from kafka import KafkaConsumer, KafkaProducer
import json
import time
from app.config import settings
from datetime import datetime, timedelta


def safe_json_deserializer(m):
    if not m:
        return None
    try:
        return json.loads(m.decode('utf-8'))
    except json.JSONDecodeError:
        print(f"Failed to decode message: {m}")
        return None


class RetryConsumer:
    """Consumes notifications from retry topics and re-publishes them after delay"""

    def __init__(self, retry_topic, delay_minutes, next_retry_topic=None):
        """
        Initialize retry consumer

        Args:
            retry_topic: Topic to consume from (e.g. "notifications-retry-5m")
            delay_minutes: Minutes to delay before republishing
            next_retry_topic: Next retry topic if publishing fails again (or None)
        """
        self.retry_topic = retry_topic
        self.delay_minutes = delay_minutes
        self.next_retry_topic = next_retry_topic

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

    def start_consuming(self):
        """Start consuming from retry topic"""
        try:
            print(f"Starting {self.retry_topic} consumer with {self.delay_minutes} minute delay...")
            for message in self.consumer:
                try:
                    notification_data = message.value
                    if not notification_data:
                        print("⚠️ Empty retry message received, skipping.")
                        continue

                    # Check if we need to respect the delay
                    last_attempt = notification_data.get("last_attempt")
                    if last_attempt:
                        last_attempt_time = datetime.fromisoformat(last_attempt)
                        earliest_retry = last_attempt_time + timedelta(minutes=self.delay_minutes)
                        now = datetime.now()

                        if now < earliest_retry:
                            time_to_wait = (earliest_retry - now).total_seconds()
                            print(f"⏳ Waiting {time_to_wait:.1f} seconds before retrying...")
                            time.sleep(time_to_wait)

                    # Determine where to send the message
                    priority = notification_data.get("priority", "medium")
                    original_topic = f"notifications-{priority}"

                    # Send back to original topic
                    self.producer.send(original_topic, notification_data)
                    print(
                        f"🔄 Retrying notification on {original_topic}, attempt #{notification_data.get('retry_count', 1)}")

                except Exception as e:
                    print(f"❌ Error processing retry message: {str(e)}")

                    # If we have a next retry topic, send it there
                    if self.next_retry_topic and message.value:
                        retry_data = message.value.copy() if isinstance(message.value, dict) else {}
                        retry_data["retry_count"] = retry_data.get("retry_count", 0) + 1
                        retry_data["last_error"] = str(e)
                        retry_data["last_attempt"] = datetime.now().isoformat()

                        self.producer.send(self.next_retry_topic, retry_data)
                        print(f"↪️ Forwarded to next retry topic: {self.next_retry_topic}")

        except Exception as e:
            print(f"🔥 Error in retry consumer loop: {str(e)}")
        finally:
            self.close()

    def close(self):
        """Close consumer and producer"""
        if self.producer:
            self.producer.close()
        if self.consumer:
            self.consumer.close()


class FailedNotificationConsumer:
    """Consumes notifications from the failed topic and logs them"""

    def __init__(self):
        self.consumer = KafkaConsumer(
            "notifications-failed",
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_deserializer=safe_json_deserializer,
            group_id="failed-notification-group",
            auto_offset_reset="earliest"
        )

    def start_consuming(self):
        """Start consuming from failed notifications topic"""
        try:
            print("Starting failed notifications consumer...")
            for message in self.consumer:
                try:
                    notification_data = message.value
                    if not notification_data:
                        continue

                    # Log the failed notification
                    print(f"⛔ PERMANENTLY FAILED NOTIFICATION:")
                    print(f"  ID: {notification_data.get('id')}")
                    print(f"  Recipients: {notification_data.get('recipients')}")
                    print(f"  Last Error: {notification_data.get('last_error')}")
                    print(f"  Retry Count: {notification_data.get('retry_count')}")

                    # Here you might want to store this in a database or send an alert

                except Exception as e:
                    print(f"Error processing failed notification: {str(e)}")

        except Exception as e:
            print(f"Error in failed notification consumer: {str(e)}")
        finally:
            if self.consumer:
                self.consumer.close()

    def close(self):
        """Close consumer"""
        if self.consumer:
            self.consumer.close()