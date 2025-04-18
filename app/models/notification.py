from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class NotificationType(str, Enum):
    """Types of notifications"""
    SINGLE = "single"
    BULK = "bulk"

class Priority(str, Enum):
    """Priority levels for notifications"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class DeliveryChannel(str, Enum):
    """Available delivery channels"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    NEWSLETTER = "newsletter"

class NotificationStatus(str, Enum):
    """Status of a notification"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    FAILED = "failed"
    
class Notification(BaseModel):
    """Notification data model"""
    id: Optional[str] = None
    type: NotificationType
    priority: Priority = Priority.MEDIUM
    title: str
    content: str
    template_id: Optional[str] = None
    channels: List[DeliveryChannel]
    recipients: List[str]
    scheduled_time: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    status: NotificationStatus = NotificationStatus.PENDING
    metadata: Optional[dict] = {}
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
        schema_extra = {
            "example": {
                "type": "single",
                "priority": "medium",
                "title": "Account Update",
                "content": "Your account has been updated successfully.",
                "template_id": "account_update",
                "channels": ["email", "push"],
                "recipients": ["user@example.com"],
                "scheduled_time": None,
                "metadata": {"category": "account", "action": "update"}
            }
        }