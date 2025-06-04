# app/consumers/retry_notification_consumer.py
# Updated with configurable retry timing and database pipeline cleanup

from kafka import KafkaConsumer, KafkaProducer
import json
import time
from app.config import settings
from datetime import datetime, timedelta
from app.db.simple_db import save_retry_attempt


def safe_json_deserializer(m):
    if not m:
        return None
    try:
        return json.loads(m.decode('utf-8'))
    except json.JSONDecodeError:
        print(f"Failed to decode message: {m}")
        return None


class RetryConsumer:
    """Enhanced retry consumer with configurable timing and database logging"""

    def __init__(self, retry_topic, delay_minutes, next_retry_topic=None):
        """
        Initialize enhanced retry consumer with configurable timing

        Args:
            retry_topic: Topic to consume from (e.g. "notifications-retry-5m")
            delay_minutes: Minutes to delay before republishing (will be overridden by config)
            next_retry_topic: Next retry topic if publishing fails again (or None)
        """
        self.retry_topic = retry_topic
        self.next_retry_topic = next_retry_topic
        self.config = settings

        # 🎯 DETERMINE DELAY BASED ON CONFIGURATION
        if retry_topic == settings.RETRY_TOPIC_SHORT:
            if settings.TESTING_MODE:
                # Use the maximum of first and second delay for short retry topic
                self.delay_seconds = max(
                    settings.TEST_RETRY_FIRST_DELAY_SECONDS,
                    settings.TEST_RETRY_SECOND_DELAY_SECONDS
                )
                self.delay_minutes = self.delay_seconds / 60
            else:
                # Use the maximum of first and second delay for production
                self.delay_minutes = max(
                    settings.RETRY_FIRST_DELAY_MINUTES,
                    settings.RETRY_SECOND_DELAY_MINUTES
                )
                self.delay_seconds = self.delay_minutes * 60

        elif retry_topic == settings.RETRY_TOPIC_LONG:
            if settings.TESTING_MODE:
                self.delay_seconds = settings.TEST_RETRY_FINAL_DELAY_SECONDS
                self.delay_minutes = self.delay_seconds / 60
            else:
                self.delay_minutes = settings.RETRY_FINAL_DELAY_MINUTES
                self.delay_seconds = self.delay_minutes * 60
        else:
            # Fallback to provided delay_minutes if not a configured topic
            self.delay_minutes = delay_minutes
            self.delay_seconds = delay_minutes * 60

        try:
            self.consumer = KafkaConsumer(
                retry_topic,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=safe_json_deserializer,
                group_id=f"{retry_topic}-group",
                auto_offset_reset="earliest"
            )

            self.producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )

            mode = "TESTING" if settings.TESTING_MODE else "PRODUCTION"
            print(f"✅ Enhanced retry consumer initialized for {retry_topic}")
            print(f"⚙️ Mode: {mode}, Delay: {self.delay_seconds}s ({self.delay_minutes:.2f} min)")

        except Exception as e:
            print(f"⚠️ Error initializing retry consumer: {e}")
            self.consumer = None
            self.producer = None

    def start_consuming(self):
        """Start consuming from retry topic with enhanced logging and configuration"""
        if not self.consumer:
            print(f"⚠️ Retry consumer not available for {self.retry_topic}")
            return

        try:
            mode = "TESTING" if settings.TESTING_MODE else "PRODUCTION"
            print(f"🔄 Starting {self.retry_topic} consumer in {mode} mode with {self.delay_seconds}s delay...")

            for message in self.consumer:
                try:
                    notification_data = message.value
                    if not notification_data:
                        print("⚠️ Empty retry message received, skipping.")
                        continue

                    notification_id = notification_data.get("id", "unknown")

                    # 🛡️ PIPELINE CLEANUP CHECK: Database lookup first
                    if self._is_permanently_failed_in_database(notification_data):
                        print(f"🛑 RETRY PIPELINE CLEARED: {notification_id} permanently failed in database")
                        continue

                    # Log retry attempt to database
                    self._log_retry_attempt(notification_data)

                    # 🕐 CONFIGURABLE DELAY: Check if we need to respect the delay
                    last_attempt = notification_data.get("last_attempt")
                    if last_attempt:
                        last_attempt_time = datetime.fromisoformat(last_attempt)
                        earliest_retry = last_attempt_time + timedelta(seconds=self.delay_seconds)
                        now = datetime.now()

                        if now < earliest_retry:
                            time_to_wait = (earliest_retry - now).total_seconds()
                            mode_info = f"({mode} mode: {self.delay_seconds}s delay)"
                            print(f"⏳ Waiting {time_to_wait:.1f} seconds before retrying... {mode_info}")
                            time.sleep(time_to_wait)

                    # Determine where to send the message
                    priority = notification_data.get("priority", "medium")
                    original_topic = f"notifications-{priority}"

                    # Calculate next retry time for logging
                    next_retry_time = (datetime.now() + timedelta(seconds=self.delay_seconds)).isoformat()

                    # Send back to original topic
                    if self.producer:
                        self.producer.send(original_topic, notification_data)
                        retry_count = notification_data.get('retry_count', 1)
                        print(f"🔄 Retrying notification {notification_id} on {original_topic}, attempt #{retry_count}")

                        # Log successful retry dispatch
                        self._log_retry_dispatch(notification_data, original_topic, next_retry_time)

                except Exception as e:
                    print(f"❌ Error processing retry message: {str(e)}")

                    # If we have a next retry topic, send it there
                    if self.next_retry_topic and message.value:
                        retry_data = message.value.copy() if isinstance(message.value, dict) else {}
                        retry_data["retry_count"] = retry_data.get("retry_count", 0) + 1
                        retry_data["last_error"] = str(e)
                        retry_data["last_attempt"] = datetime.now().isoformat()

                        if self.producer:
                            self.producer.send(self.next_retry_topic, retry_data)
                            print(f"↪️ Forwarded to next retry topic: {self.next_retry_topic}")

        except Exception as e:
            print(f"🔥 Error in retry consumer loop: {str(e)}")
        finally:
            self.close()

    def _is_permanently_failed_in_database(self, notification_data: dict) -> bool:
        """Check if notification is permanently failed in database"""
        try:
            from app.db.simple_db import is_notification_permanently_failed

            notification_id = notification_data.get("id")
            if not notification_id:
                return False

            return is_notification_permanently_failed(notification_id)

        except Exception as e:
            print(f"⚠️ Error checking permanent failures in retry consumer: {e}")
            # If we can't check the database, allow retry to proceed
            # This prevents notifications from being stuck if there's a DB issue
            return False

    def _log_retry_attempt(self, notification_data: dict):
        """Log retry attempt to database"""
        try:
            notification_id = notification_data.get("id", "unknown")
            recipients = notification_data.get("recipients", [])
            failed_recipients = notification_data.get("failed_recipients", recipients)
            channels = notification_data.get("channels", ["unknown"])
            retry_count = notification_data.get("retry_count", 0)
            error_message = notification_data.get("last_error", "Retry scheduled")

            # Determine channel
            channel = "unknown"
            if "email" in channels or "EMAIL" in str(channels):
                channel = "email"
            elif "sms" in channels or "SMS" in str(channels):
                channel = "sms"

            # Log retry attempt for each failed recipient
            for recipient in failed_recipients:
                next_retry_time = (datetime.now() + timedelta(seconds=self.delay_seconds)).isoformat()
                save_retry_attempt(
                    notification_id=notification_id,
                    recipient=recipient,
                    channel=channel,
                    retry_attempt=retry_count,
                    error_message=error_message,
                    next_retry_scheduled=next_retry_time
                )

        except Exception as e:
            print(f"⚠️ Error logging retry attempt: {e}")

    def _log_retry_dispatch(self, notification_data: dict, target_topic: str, next_retry_time: str):
        """Log successful retry dispatch"""
        try:
            notification_id = notification_data.get("id", "unknown")
            retry_count = notification_data.get("retry_count", 0)
            mode = "TESTING" if settings.TESTING_MODE else "PRODUCTION"
            print(f"📊 Retry dispatch logged: {notification_id} attempt #{retry_count} -> {target_topic} ({mode})")
        except Exception as e:
            print(f"⚠️ Error logging retry dispatch: {e}")

    def close(self):
        """Close consumer and producer"""
        if self.producer:
            try:
                self.producer.close()
            except Exception as e:
                print(f"Error closing retry producer: {e}")
        if self.consumer:
            try:
                self.consumer.close()
            except Exception as e:
                print(f"Error closing retry consumer: {e}")


class FailedNotificationConsumer:
    """Enhanced consumer for permanently failed notifications with detailed logging"""

    def __init__(self):
        try:
            self.consumer = KafkaConsumer(
                settings.FAILED_TOPIC,  # Use configurable failed topic
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=safe_json_deserializer,
                group_id="failed-notification-group",
                auto_offset_reset="earliest"
            )
            print(f"✅ Enhanced failed notification consumer initialized for {settings.FAILED_TOPIC}")
        except Exception as e:
            print(f"⚠️ Error initializing failed notification consumer: {e}")
            self.consumer = None

    def start_consuming(self):
        """Start consuming from failed notifications topic with enhanced logging"""
        if not self.consumer:
            print("⚠️ Failed notification consumer not available")
            return

        try:
            print(f"🔍 Starting enhanced failed notifications consumer for {settings.FAILED_TOPIC}...")
            for message in self.consumer:
                try:
                    failure_data = message.value
                    if not failure_data:
                        continue

                    # Check if this is a pipeline cleared notification
                    if failure_data.get("pipeline_cleared", False):
                        print(f"🧹 Pipeline cleared notification received - monitoring only")

                    # Enhanced logging of failed notification
                    self._log_permanent_failure(failure_data)

                    # Optional: Send alerts, notifications to administrators
                    self._send_failure_alert(failure_data)

                except Exception as e:
                    print(f"❌ Error processing failed notification: {str(e)}")

        except Exception as e:
            print(f"🔥 Error in failed notification consumer: {str(e)}")
        finally:
            if self.consumer:
                self.consumer.close()

    def _log_permanent_failure(self, failure_data: dict):
        """Log permanent failure with detailed information"""
        try:
            notification_id = failure_data.get("notification_id", "unknown")
            channel = failure_data.get("channel", "unknown")
            failed_recipients = failure_data.get("failed_recipients", [])
            total_attempts = failure_data.get("total_attempts", 0)
            failure_reason = failure_data.get("last_error", "Max retries exceeded")
            pipeline_cleared = failure_data.get("pipeline_cleared", False)

            print(f"⛔ PERMANENT FAILURE LOGGED:")
            print(f"  📧 Notification ID: {notification_id}")
            print(f"  📱 Channel: {channel}")
            print(f"  👥 Failed Recipients: {len(failed_recipients)}")
            print(f"  🔄 Total Attempts: {total_attempts}")
            print(f"  ❌ Reason: {failure_reason}")
            print(f"  🕒 Failed At: {failure_data.get('failure_time', 'Unknown')}")
            print(f"  🧹 Pipeline Cleared: {pipeline_cleared}")

            # Only save to database if not already saved (avoid duplicates)
            # The email consumer already saves to permanent_failures table
            # This is just for monitoring and alerting

            if not pipeline_cleared:
                # Log to database using the save_permanent_failure function
                from app.db.simple_db import save_permanent_failure

                for recipient in failed_recipients:
                    save_permanent_failure(
                        notification_id=notification_id,
                        recipient=recipient,
                        channel=channel,
                        total_attempts=total_attempts,
                        first_attempt_time=failure_data.get("notification_data", {}).get("created_at",
                                                                                         datetime.now().isoformat()),
                        failure_reason=failure_reason,
                        all_errors=[failure_reason],  # Could be enhanced to track all errors
                        notification_data=failure_data.get("notification_data", {})
                    )

        except Exception as e:
            print(f"⚠️ Error logging permanent failure: {e}")

    def _send_failure_alert(self, failure_data: dict):
        """Send alert for permanent failure (configurable implementation)"""
        try:
            notification_id = failure_data.get("notification_id", "unknown")
            failed_count = len(failure_data.get("failed_recipients", []))
            channel = failure_data.get("channel", "unknown")
            mode = "TESTING" if settings.TESTING_MODE else "PRODUCTION"

            print(
                f"🚨 ALERT ({mode}): Permanent failure for {failed_count} recipients on {channel} (ID: {notification_id})")

            # TODO: Implement configurable alerting mechanism
            # Could be configured via settings:
            # - settings.ALERT_EMAIL_ENABLED
            # - settings.SLACK_WEBHOOK_URL
            # - settings.PAGERDUTY_API_KEY
            # - settings.ALERT_THRESHOLDS

        except Exception as e:
            print(f"⚠️ Error sending failure alert: {e}")

    def close(self):
        """Close consumer"""
        if self.consumer:
            try:
                self.consumer.close()
            except Exception as e:
                print(f"Error closing failed notification consumer: {e}")


# ==========================================
# 🎯 FACTORY FUNCTION FOR EASY SETUP
# ==========================================

def create_retry_consumers():
    """Factory function to create configured retry consumers"""
    delays = settings.retry_delays
    mode = "TESTING" if settings.TESTING_MODE else "PRODUCTION"

    print(f"🏭 Creating retry consumers in {mode} mode:")
    print(f"   Short retry delay: {delays['first_delay_seconds']}s")
    print(f"   Long retry delay: {delays['final_delay_seconds']}s")

    # Create retry consumers with configurable delays
    retry_short = RetryConsumer(
        retry_topic=settings.RETRY_TOPIC_SHORT,
        delay_minutes=delays['first_delay'],  # This will be overridden by config
        next_retry_topic=settings.RETRY_TOPIC_LONG
    )

    retry_long = RetryConsumer(
        retry_topic=settings.RETRY_TOPIC_LONG,
        delay_minutes=delays['final_delay'],  # This will be overridden by config
        next_retry_topic=settings.FAILED_TOPIC
    )

    failed_consumer = FailedNotificationConsumer()

    return retry_short, retry_long, failed_consumer


# ==========================================
# 🧪 TESTING UTILITIES
# ==========================================

# def print_retry_configuration():
#     """Print current retry configuration for debugging"""
#     print("\n" + "=" * 50)
#     print("🔄 RETRY CONSUMER CONFIGURATION")
#     print("=" * 50)
#     print(settings.retry_config_summary)
#     print(f"Topics:")
#     print(f"  Short retry: {settings.RETRY_TOPIC_SHORT}")
#     print(f"  Long retry: {settings.RETRY_TOPIC_LONG}")
#     print(f"  Failed: {settings.FAILED_TOPIC}")
#     print("=" * 50 + "\n")
#
#
# if __name__ == "__main__":
#     # For testing the configuration
#     print_retry_configuration()
#
#     # Test creating consumers
#     short, long, failed = create_retry_consumers()
#     print(f"✅ Created consumers: {short.retry_topic}, {long.retry_topic}, failed consumer")