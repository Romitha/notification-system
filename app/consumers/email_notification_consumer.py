from kafka import KafkaConsumer
import json
from typing import Dict, Any
from app.models.notification import Notification, DeliveryChannel
from app.handlers.email_handler import EmailHandler
from app.config import settings
import asyncio
from datetime import datetime
import uuid

class EmailNotificationConsumer:
    """Consumes email notifications from Kafka and processes them"""

    def __init__(self):
        self.consumer = KafkaConsumer(
            "notifications-high",
            "notifications-medium",
            "notifications-low",
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_deserializer=self.safe_json_deserializer,  # Use self to reference the method
            group_id="email-notification-group",
            auto_offset_reset="earliest"
        )
        self.email_handler = EmailHandler()

    def safe_json_deserializer(self, m):  # Add 'self' parameter
        if not m:
            return None
        try:
            return json.loads(m.decode('utf-8'))
        except json.JSONDecodeError:
            print(f"Failed to decode message: {m}")
            return None
    # def start_consuming(self):
    #     """Start consuming notifications from Kafka"""
    #     try:
    #         print("Starting to consume email notifications...")
    #         for message in self.consumer:
    #             # Process message
    #             notification_data = message.value
    #             print(f"Received notification: {notification_data}")
    #
    #             # Check if email is in channels
    #             channels = notification_data.get("channels", [])
    #             if "email" in channels or DeliveryChannel.EMAIL.value in channels:
    #                 # Convert dict back to Notification object
    #                 notification = self._dict_to_notification(notification_data)
    #
    #                 # Process email notification asynchronously
    #                 asyncio.run(self._process_email_notification(notification))
    #     except Exception as e:
    #         print(f"Error in consumer: {str(e)}")
    #     finally:
    #         self.consumer.close()

    def start_consuming(self):
        """Start consuming notifications from Kafka"""
        try:
            print("Starting to consume email notifications...")
            for message in self.consumer:
                try:
                    notification_data = message.value
                    if not notification_data:
                        print("⚠️ Empty or invalid message received, skipping.")
                        continue

                    print(f"📩 Received notification:", notification_data)

                    # Check if email is in channels
                    channels = notification_data.get("channels", [])
                    if "email" in channels or DeliveryChannel.EMAIL.value in channels:
                        # Convert dict back to Notification object
                        notification = self._dict_to_notification(notification_data)

                        # Process email notification asynchronously
                        asyncio.run(self._process_email_notification(notification))

                except Exception as msg_err:
                    print(f"❌ Error processing message: {msg_err}")
        except Exception as e:
            print(f"🔥 Error in consumer loop: {str(e)}")
        finally:
            self.consumer.close()

    async def _process_email_notification(self, notification: Notification):
        """Process an email notification"""
        try:
            # Send email
            statuses = await self.email_handler.send(notification)

            # Log results
            for status in statuses:
                print(f"Email delivery status for {status.recipient}: {status.status}")

            # Here you might want to update the notification status in your database

        except Exception as e:
            print(f"Error processing email notification: {str(e)}")

    def _dict_to_notification(self, data: Dict[str, Any]) -> Notification:
        """Convert dictionary to Notification object"""
        # Handle datetime conversion
        if "scheduled_time" in data and data["scheduled_time"]:
            data["scheduled_time"] = datetime.fromisoformat(data["scheduled_time"])
        if "created_at" in data and data["created_at"]:
            data["created_at"] = datetime.fromisoformat(data["created_at"])

        # Add a fallback ID if none exists
        if data.get("id") is None:
            data["id"] = f"gen-{uuid.uuid4()}"
            print(f"Generated ID for notification: {data['id']}")

        return Notification(**data)

    def close(self):
        """Close the consumer"""
        if self.consumer:
            self.consumer.close()