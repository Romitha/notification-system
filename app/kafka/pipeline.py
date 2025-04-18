from app.models.notification import Notification, Priority
from app.config import settings
import json
from kafka import KafkaProducer
from kafka.errors import KafkaError
from fastapi.encoders import jsonable_encoder

class KafkaPipeline:
    """Handles sending notifications to Kafka topics based on priority"""
    
    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        self.topics = {
            Priority.HIGH: "notifications-high",
            Priority.MEDIUM: "notifications-medium",
            Priority.LOW: "notifications-low"
        }

    async def send_notification(self, notification) -> bool:
        """Send notification to appropriate Kafka topic based on priority"""
        # Handle both Notification objects and dictionaries
        if isinstance(notification, dict):
            priority = notification.get("priority")
            notification_data = notification  # Already a dict
        else:
            priority = notification.priority
            # Use jsonable_encoder instead of .dict() to handle datetime serialization
            notification_data = jsonable_encoder(notification)

        topic = self.topics.get(priority)

        try:
            # Send to Kafka
            future = self.producer.send(topic, notification_data)
            result = future.get(timeout=60)
            return True
        except KafkaError as e:
            print(f"Error sending to Kafka: {e}")
            return False
    
    def close(self):
        """Close Kafka producer connection"""
        if self.producer:
            self.producer.close()