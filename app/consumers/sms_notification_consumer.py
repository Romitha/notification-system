# app/consumers/sms_notification_consumer.py
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


class SMSNotificationConsumer:
    """Consumes SMS notifications from Kafka and processes them"""

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
            print("SMS notification consumer initialized successfully")
        except Exception as e:
            print(f"⚠️ Error initializing SMS consumer: {e}")
            # Create fallback components to prevent the app from crashing
            self.consumer = None
            self.producer = None
            self.sms_handler = SMSHandler()

    def start_consuming(self):
        """Start consuming notifications from Kafka"""
        # Skip if Kafka is not available
        if not self.consumer:
            print("⚠️ Kafka consumer not available, skipping SMS consumer startup")
            return

        try:
            print("Starting to consume SMS notifications...")
            for message in self.consumer:
                try:
                    notification_data = message.value
                    if not notification_data:
                        print("⚠️ Empty or invalid message received, skipping.")
                        continue

                    print(f"📩 Received notification:", notification_data)

                    # Check if SMS is in channels
                    channels = notification_data.get("channels", [])
                    if "sms" in channels or DeliveryChannel.SMS.value in channels:
                        # Convert dict back to Notification object
                        notification = self._dict_to_notification(notification_data)

                        # Process SMS notification asynchronously
                        statuses = asyncio.run(self._process_sms_notification(notification))

                        # Check if any recipients failed
                        has_failures = any(status.status == "failed" for status in statuses)

                        if has_failures:
                            # Send to retry topic with metadata about the attempt
                            retry_data = notification_data.copy()
                            retry_data["retry_count"] = retry_data.get("retry_count", 0) + 1
                            failed_status = next((s for s in statuses if s.status == "failed"), None)
                            retry_data["last_error"] = getattr(failed_status, "error_message", "Unknown error")
                            retry_data["last_attempt"] = datetime.now().isoformat()

                            # Choose topic based on retry count
                            if retry_data["retry_count"] <= 3:
                                retry_topic = "notifications-retry-5m"
                                print(
                                    f"⚠️ Sending to retry topic with 5 minute delay, attempt #{retry_data['retry_count']}")
                            elif retry_data["retry_count"] <= 5:
                                retry_topic = "notifications-retry-30m"
                                print(
                                    f"⚠️ Sending to retry topic with 30 minute delay, attempt #{retry_data['retry_count']}")
                            else:
                                retry_topic = "notifications-failed"
                                print(f"❌ Max retries exceeded, sending to failed topic")

                            if self.producer:
                                self.producer.send(retry_topic, retry_data)

                except Exception as msg_err:
                    print(f"❌ Error processing message: {msg_err}")
                    # Send to retry topic if it's a dictionary
                    if self.producer and message.value and isinstance(message.value, dict):
                        retry_data = message.value.copy()
                        retry_data["retry_count"] = retry_data.get("retry_count", 0) + 1
                        retry_data["last_error"] = str(msg_err)
                        retry_data["last_attempt"] = datetime.now().isoformat()
                        self.producer.send("notifications-retry-5m", retry_data)
                        print(f"⚠️ Sending to retry topic with 5 minute delay, attempt #{retry_data['retry_count']}")
        except Exception as e:
            print(f"🔥 Error in consumer loop: {str(e)}")
        finally:
            self.close()

    async def _process_sms_notification(self, notification: Notification):
        """Process an SMS notification"""
        try:
            # Log notification type
            if notification.type == NotificationType.BULK:
                batch_info = f"(Batch {notification.metadata.get('batch_index', '?')}/{notification.metadata.get('batch_size', '?')})"
                print(f"📨 Processing BULK SMS notification {batch_info} with {len(notification.recipients)} recipients")
            else:
                print(f"📧 Processing SINGLE SMS notification to {len(notification.recipients)} recipients")

            # Send SMS
            statuses = await self.sms_handler.send(notification)

            # Log results
            success_count = sum(1 for status in statuses if status.status == "delivered")
            failed_count = len(statuses) - success_count

            print(f"📊 SMS delivery results: {success_count} succeeded, {failed_count} failed")

            if failed_count > 0:
                failed_recipients = [status.recipient for status in statuses if status.status == "failed"]
                print(f"❌ Failed recipients: {failed_recipients}")

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
            print(f"Generated ID for notification: {data_copy['id']}")

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
                print(f"Error closing producer: {e}")

        if hasattr(self, 'consumer') and self.consumer:
            try:
                self.consumer.close()
            except Exception as e:
                print(f"Error closing consumer: {e}")