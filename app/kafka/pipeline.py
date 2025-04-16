from app.models.notification import Notification, Priority
from app.config import settings
import json
from kafka import KafkaProducer
from kafka.errors import KafkaError

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
    
    async def send_notification(self, notification: Notification) -> bool:
        """Send notification to appropriate Kafka topic based on priority"""
        topic = self.topics.get(notification.priority)
        
        try:
            # Convert to dict for serialization
            notification_data = notification.dict()
            
            # Send to Kafka
            future = self.producer.send(topic, notification_data)
            result = future.get(timeout=60)  # Wait for message to be delivered
            return True
        except KafkaError as e:
            # Log error
            print(f"Error sending to Kafka: {e}")
            return False
    
    def close(self):
        """Close Kafka producer connection"""
        if self.producer:
            self.producer.close()