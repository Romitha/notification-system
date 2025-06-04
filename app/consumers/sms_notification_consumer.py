# app/consumers/sms_notification_consumer.py
# Aligned with email consumer features: configuration, pipeline cleanup, database checks

from kafka import KafkaConsumer, KafkaProducer
import json
from typing import Dict, Any, List
from app.models.notification import Notification, DeliveryChannel, NotificationType
from app.handlers.sms_handler import SMSHandler
from app.config import settings
import asyncio
from datetime import datetime
import uuid
import time
from app.models.delivery_status import DeliveryStatus
from app.db.simple_db import save_delivery_status


class SMSNotificationConsumer:
    """Consumes SMS notifications from Kafka with configurable retry and proper pipeline cleanup"""

    def safe_json_deserializer(self, m):
        if not m:
            return None
        try:
            return json.loads(m.decode('utf-8'))
        except json.JSONDecodeError:
            print(f"Failed to decode message: {m}")
            return None

    def __init__(self):
        try:
            self.consumer = KafkaConsumer(
                "notifications-high",
                "notifications-medium",
                "notifications-low",
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=self.safe_json_deserializer,
                group_id="sms-notification-group",
                auto_offset_reset="earliest"
            )
            self.producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            self.sms_handler = SMSHandler()

            # Print retry configuration on initialization
            print("📱 SMS notification consumer initialized successfully")
            print(f"⚙️ Retry configuration: {settings.retry_config_summary}")

        except Exception as e:
            print(f"⚠️ Error initializing SMS consumer: {e}")
            # Create fallback components to prevent the app from crashing
            self.consumer = None
            self.producer = None
            self.sms_handler = SMSHandler()

    def start_consuming(self):
        """Start consuming notifications with enhanced pipeline cleanup"""
        # Skip if Kafka is not available
        if not self.consumer:
            print("⚠️ Kafka consumer not available, skipping SMS consumer startup")
            return

        try:
            print("📱 Starting to consume SMS notifications with pipeline cleanup...")
            for message in self.consumer:
                try:
                    notification_data = message.value
                    if not notification_data:
                        print("⚠️ Empty or invalid message received, skipping.")
                        continue

                    notification_id = notification_data.get("id", "unknown")
                    retry_count = notification_data.get("retry_count", 0)

                    print(f"📨 Received SMS notification {notification_id} with retry_count={retry_count}")

                    # 🛡️ PIPELINE CLEANUP CHECK #1: Database lookup
                    if self._is_permanently_failed_in_database(notification_data):
                        print(f"🛑 PIPELINE CLEARED: {notification_id} already in permanent_failures table")
                        self._consume_without_processing(notification_data, "Already permanently failed")
                        continue

                    # 🛡️ PIPELINE CLEANUP CHECK #2: Retry count limit (configurable)
                    if retry_count >= settings.MAX_RETRY_ATTEMPTS:
                        print(f"🛑 PIPELINE CLEARED: {notification_id} exceeded max retries (count={retry_count}, max={settings.MAX_RETRY_ATTEMPTS})")
                        self._handle_permanent_failure_final(notification_data)
                        continue

                    # 🛡️ PIPELINE CLEANUP CHECK #3: Explicit status check
                    status = notification_data.get("status", "")
                    if status in ["permanently_failed", "processing_failed"]:
                        print(f"🛑 PIPELINE CLEARED: {notification_id} has status={status}")
                        self._consume_without_processing(notification_data, f"Status is {status}")
                        continue

                    # Check if SMS is in channels
                    channels = notification_data.get("channels", [])
                    if "sms" in channels or DeliveryChannel.SMS.value in channels:
                        # ✅ Safe to process
                        print(f"✅ Processing SMS notification {notification_id} (retry_count={retry_count})")

                        # Convert dict back to Notification object
                        notification = self._dict_to_notification(notification_data)

                        # Process SMS notification asynchronously
                        statuses = asyncio.run(self._process_sms_notification(notification))

                        # Handle retry logic based on delivery status (now with configuration)
                        self._handle_retry_logic_sync(notification_data, statuses)

                except Exception as msg_err:
                    print(f"❌ Error processing SMS message: {msg_err}")
                    # Send to retry topic if it's a dictionary
                    if self.producer and message.value and isinstance(message.value, dict):
                        self._handle_processing_error_sync(message.value, str(msg_err))
        except Exception as e:
            print(f"🔥 Error in SMS consumer loop: {str(e)}")
        finally:
            self.close()

    def _is_permanently_failed_in_database(self, notification_data: dict) -> bool:
        """Check if notification is permanently failed in database"""
        try:
            from app.db.simple_db import get_db_connection

            notification_id = notification_data.get("id")
            if not notification_id:
                return False

            conn = get_db_connection()
            cursor = conn.cursor()

            # Check if this notification is in permanent_failures table
            cursor.execute('''
                SELECT COUNT(*) FROM permanent_failures 
                WHERE notification_id = ?
            ''', (notification_id,))

            count = cursor.fetchone()[0]

            if count > 0:
                print(f"🔍 Found {count} permanent failure record(s) for SMS {notification_id}")
                return True

            return False

        except Exception as e:
            print(f"⚠️ Error checking SMS permanent failures: {e}")
            return False

    def _consume_without_processing(self, notification_data: dict, reason: str):
        """Consume message without processing = Pipeline cleanup"""
        notification_id = notification_data.get("id", "unknown")
        print(f"🧹 CONSUMING SMS WITHOUT PROCESSING: {notification_id}")
        print(f"📋 Reason: {reason}")
        print(f"🚮 SMS message consumed and discarded = Pipeline cleared")

        # Optional: Log the skipped processing
        try:
            for recipient in notification_data.get("recipients", []):
                skip_status = DeliveryStatus(
                    notification_id=notification_id,
                    recipient=recipient,
                    channel="sms",
                    status="skipped_permanently_failed",
                    vendor="system",
                    error_message=f"Skipped SMS processing: {reason}",
                    timestamp=datetime.now().isoformat()
                )
                save_delivery_status(skip_status)

        except Exception as e:
            print(f"⚠️ Warning: Could not log SMS skip status: {e}")

    def _handle_permanent_failure_final(self, notification_data: dict):
        """Handle permanent failure and ensure no more retries"""
        notification_id = notification_data.get("id", "unknown")
        retry_count = notification_data.get("retry_count", 0)

        print(f"💀 FINAL SMS PERMANENT FAILURE: {notification_id}")
        print(f"📊 Total attempts: {retry_count + 1}")
        print(f"🚫 No more SMS retries will be attempted")

        # Save to permanent failures table
        try:
            from app.db.simple_db import save_permanent_failure

            for recipient in notification_data.get("recipients", []):
                save_permanent_failure(
                    notification_id=notification_id,
                    recipient=recipient,
                    channel="sms",
                    total_attempts=retry_count + 1,
                    first_attempt_time=notification_data.get("created_at", datetime.now().isoformat()),
                    failure_reason=f"Exceeded max SMS retries ({retry_count + 1} attempts)",
                    all_errors=[notification_data.get("last_error", "Unknown error")],
                    notification_data=notification_data
                )

            print(f"✅ SMS permanent failure saved to database")

        except Exception as e:
            print(f"❌ Error saving SMS permanent failure: {e}")

        # 🎯 CRITICAL: Do NOT send to any retry topics
        print(f"🛑 SMS PIPELINE CLEANUP: No retry topics will be used")
        print(f"🧹 SMS message consumed and pipeline cleared")

    def _is_permanently_failed(self, notification_data: dict) -> bool:
        """Check if this notification should be permanently failed (legacy method)"""
        retry_count = notification_data.get("retry_count", 0)

        # Use configurable max retry attempts
        if retry_count >= settings.MAX_RETRY_ATTEMPTS:
            print(f"🚫 SMS notification has retry_count={retry_count} >= max({settings.MAX_RETRY_ATTEMPTS}), marking as permanently failed")
            return True

        # Also check if it's explicitly marked as permanently failed
        status = notification_data.get("status", "")
        if status in ["permanently_failed", "processing_failed"]:
            print(f"🚫 SMS notification status is {status}, skipping")
            return True

        return False

    def _handle_retry_logic_sync(self, notification_data: dict, statuses: List[DeliveryStatus]):
        """ENHANCED: Handle retry logic with configuration and proper pipeline cleanup"""
        # Check if any recipients failed
        failed_statuses = [status for status in statuses if status.status == "failed"]

        if not failed_statuses:
            print("✅ All SMS recipients delivered successfully")
            return

        # Get current retry count
        retry_count = notification_data.get("retry_count", 0)
        delays = settings.retry_delays

        print(f"❌ {len(failed_statuses)} SMS recipients failed, retry count: {retry_count}")
        print(f"⚙️ Using {delays['unit']} delays from configuration")

        # 🎯 CONFIGURABLE RETRY LOGIC:
        if retry_count == 0:
            # First retry - configurable delay
            delay_seconds = delays['first_delay_seconds']
            self._send_to_retry_topic_sync(
                notification_data,
                failed_statuses,
                settings.RETRY_TOPIC_SHORT,
                delays['first_delay'],
                f"First SMS retry attempt (1/{settings.MAX_RETRY_ATTEMPTS}) - {delay_seconds}s delay"
            )
        elif retry_count == 1:
            # Second retry - configurable delay
            delay_seconds = delays['second_delay_seconds']
            self._send_to_retry_topic_sync(
                notification_data,
                failed_statuses,
                settings.RETRY_TOPIC_SHORT,
                delays['second_delay'],
                f"Second SMS retry attempt (2/{settings.MAX_RETRY_ATTEMPTS}) - {delay_seconds}s delay"
            )
        elif retry_count == 2:
            # Final retry - configurable delay
            delay_seconds = delays['final_delay_seconds']
            self._send_to_retry_topic_sync(
                notification_data,
                failed_statuses,
                settings.RETRY_TOPIC_LONG,
                delays['final_delay'],
                f"Final SMS retry attempt (3/{settings.MAX_RETRY_ATTEMPTS}) - {delay_seconds}s delay"
            )
        else:
            # retry_count >= MAX_RETRY_ATTEMPTS: Permanent failure - STOP THE PIPELINE
            print(f"🛑 STOPPING SMS PIPELINE: retry_count={retry_count} >= {settings.MAX_RETRY_ATTEMPTS}")
            self._handle_permanent_failure_sync(notification_data, failed_statuses)

    def _send_to_retry_topic_sync(self, notification_data: dict, failed_statuses: List[DeliveryStatus],
                                  retry_topic: str, delay_minutes: int, message: str):
        """Send notification to retry topic with configuration"""
        retry_data = notification_data.copy()
        retry_data["retry_count"] = retry_data.get("retry_count", 0) + 1

        # Get the first failed status for error details
        first_failed = failed_statuses[0]
        retry_data["last_error"] = first_failed.error_message or "SMS delivery failed"
        retry_data["last_attempt"] = datetime.now().isoformat()
        retry_data["failed_recipients"] = [status.recipient for status in failed_statuses]

        mode = "TESTING" if settings.TESTING_MODE else "PRODUCTION"
        print(f"⚠️ {message} ({mode} mode)")
        print(f"📤 Sending to {retry_topic} with retry_count={retry_data['retry_count']}")

        if self.producer:
            self.producer.send(retry_topic, retry_data)
            print(f"✅ Sent to SMS retry queue")

    def _handle_permanent_failure_sync(self, notification_data: dict, failed_statuses: List[DeliveryStatus]):
        """Handle permanent failure - log to database and COMPLETELY clear pipeline"""
        print(f"❌ SMS MAX RETRIES EXCEEDED - Permanent failure")
        print(f"🛑 SMS PIPELINE CLEANUP: This notification will NOT be retried again")

        notification_id = notification_data.get("id", "unknown")
        failed_recipients = [status.recipient for status in failed_statuses]

        print(f"📝 Logging SMS permanent failure to database:")
        print(f"   Notification ID: {notification_id}")
        print(f"   Failed Recipients: {failed_recipients}")
        print(f"   Total Retry Attempts: {notification_data.get('retry_count', 0)}")

        # Save permanent failure status for each failed recipient
        for failed_status in failed_statuses:
            permanent_failure_status = DeliveryStatus(
                notification_id=notification_id,
                recipient=failed_status.recipient,
                channel="sms",
                status="permanently_failed",
                vendor=failed_status.vendor or "dialog",
                vendor_message_id=failed_status.vendor_message_id,
                error_message=f"Max SMS retries exceeded ({notification_data.get('retry_count', 0)} attempts). "
                              f"Last error: {failed_status.error_message or 'Unknown error'}",
                timestamp=datetime.now().isoformat()
            )

            try:
                save_delivery_status(permanent_failure_status)
                print(f"✅ Logged SMS permanent failure for {failed_status.recipient}")
            except Exception as e:
                print(f"❌ Error saving SMS permanent failure to DB: {e}")

        # Save to permanent failures table
        try:
            from app.db.simple_db import save_permanent_failure

            for failed_status in failed_statuses:
                save_permanent_failure(
                    notification_id=notification_id,
                    recipient=failed_status.recipient,
                    channel="sms",
                    total_attempts=notification_data.get("retry_count", 0) + 1,
                    first_attempt_time=notification_data.get("created_at", datetime.now().isoformat()),
                    failure_reason="Max SMS retries exceeded",
                    all_errors=[failed_status.error_message or "Unknown error"],
                    notification_data=notification_data
                )
        except Exception as e:
            print(f"❌ Error saving to SMS permanent failures table: {e}")

        # Send to failed topic for monitoring ONLY (not for reprocessing)
        failure_data = {
            "notification_id": notification_id,
            "channel": "sms",
            "failed_recipients": failed_recipients,
            "total_attempts": notification_data.get("retry_count", 0) + 1,
            "last_error": notification_data.get("last_error", "Unknown error"),
            "failure_time": datetime.now().isoformat(),
            "notification_data": notification_data,
            "status": "permanently_failed",
            "pipeline_cleared": True
        }

        if self.producer:
            self.producer.send(settings.FAILED_TOPIC, failure_data)
            print(f"📤 Sent SMS failure details to {settings.FAILED_TOPIC} for monitoring ONLY")

        print(f"🧹 SMS Pipeline COMPLETELY cleared for notification {notification_id}")
        print(f"🚫 This SMS notification will NEVER be processed again")

    def _handle_processing_error_sync(self, notification_data: dict, error_message: str):
        """Handle errors that occur during message processing"""
        # Check if already permanently failed
        if self._is_permanently_failed_in_database(notification_data):
            print(f"🛑 SMS processing error for permanently failed notification, skipping retry")
            return

        retry_data = notification_data.copy()
        retry_data["retry_count"] = retry_data.get("retry_count", 0) + 1
        retry_data["last_error"] = f"SMS Processing error: {error_message}"
        retry_data["last_attempt"] = datetime.now().isoformat()

        # Follow same retry logic for processing errors
        retry_count = retry_data["retry_count"] - 1

        if retry_count < settings.MAX_RETRY_ATTEMPTS:
            if retry_count < 2:
                self.producer.send(settings.RETRY_TOPIC_SHORT, retry_data)
                print(f"⚠️ SMS Processing error - sending to short retry, attempt #{retry_data['retry_count']}")
            else:
                self.producer.send(settings.RETRY_TOPIC_LONG, retry_data)
                print(f"⚠️ SMS Processing error - sending to long retry, final attempt")
        else:
            # Log processing failure to database
            self._log_processing_failure_sync(notification_data, error_message)

    def _log_processing_failure_sync(self, notification_data: dict, error_message: str):
        """Log processing failure to database"""
        notification_id = notification_data.get("id", f"sms-processing-error-{uuid.uuid4()}")
        recipients = notification_data.get("recipients", ["unknown"])

        for recipient in recipients:
            failure_status = DeliveryStatus(
                notification_id=notification_id,
                recipient=recipient,
                channel="sms",
                status="processing_failed",
                vendor="system",
                error_message=f"SMS Processing failed after max retries: {error_message}",
                timestamp=datetime.now().isoformat()
            )

            try:
                save_delivery_status(failure_status)
                print(f"✅ Logged SMS processing failure for {recipient}")
            except Exception as e:
                print(f"❌ Error saving SMS processing failure to DB: {e}")

    async def _process_sms_notification(self, notification: Notification):
        """Process an SMS notification"""
        try:
            # Log notification type
            if notification.type == NotificationType.BULK:
                batch_info = f"(Batch {notification.metadata.get('batch_index', '?')}/{notification.metadata.get('batch_size', '?')})"
                print(f"📨 Processing BULK SMS notification {batch_info} with {len(notification.recipients)} recipients")
            else:
                print(f"📱 Processing SINGLE SMS notification to {len(notification.recipients)} recipients")

            # Send SMS
            statuses = await self.sms_handler.send(notification)

            # Log results
            success_count = sum(1 for status in statuses if status.status == "delivered")
            failed_count = len(statuses) - success_count

            print(f"📊 SMS delivery results: {success_count} succeeded, {failed_count} failed")

            if failed_count > 0:
                failed_recipients = [status.recipient for status in statuses if status.status == "failed"]
                print(f"❌ Failed SMS recipients: {failed_recipients}")

            return statuses

        except Exception as e:
            print(f"Error processing SMS notification: {str(e)}")
            raise

    def _dict_to_notification(self, data: Dict[str, Any]) -> Notification:
        """Convert dictionary to Notification object"""
        # Make a copy to avoid modifying the original
        data_copy = data.copy()

        # Handle datetime conversion
        if "scheduled_time" in data_copy and data_copy["scheduled_time"]:
            try:
                data_copy["scheduled_time"] = datetime.fromisoformat(data_copy["scheduled_time"])
            except (ValueError, TypeError):
                print(f"⚠️ Invalid scheduled_time format: {data_copy['scheduled_time']}")
                data_copy["scheduled_time"] = None

        if "created_at" in data_copy and data_copy["created_at"]:
            try:
                data_copy["created_at"] = datetime.fromisoformat(data_copy["created_at"])
            except (ValueError, TypeError):
                print(f"⚠️ Invalid created_at format: {data_copy['created_at']}")
                data_copy["created_at"] = datetime.now()

        # Add a fallback ID if none exists
        if data_copy.get("id") is None:
            data_copy["id"] = f"gen-{uuid.uuid4()}"
            print(f"Generated ID for SMS notification: {data_copy['id']}")

        # Ensure we have valid channels and status
        if "channels" not in data_copy or not data_copy["channels"]:
            data_copy["channels"] = [DeliveryChannel.SMS]

        if "status" not in data_copy:
            data_copy["status"] = "pending"

        return Notification(**data_copy)

    def close(self):
        """Close the consumer"""
        if hasattr(self, 'producer') and self.producer:
            try:
                self.producer.close()
            except Exception as e:
                print(f"Error closing SMS producer: {e}")

        if hasattr(self, 'consumer') and self.consumer:
            try:
                self.consumer.close()
            except Exception as e:
                print(f"Error closing SMS consumer: {e}")