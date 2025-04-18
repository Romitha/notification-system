from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class DeliveryStatus(BaseModel):
    """Status of notification delivery"""
    notification_id: str
    recipient: str
    channel: str
    status: str  # delivered, failed, pending
    vendor: str
    vendor_message_id: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "notification_id": "123e4567-e89b-12d3-a456-426614174000",
                "recipient": "user@example.com",
                "channel": "email",
                "status": "delivered",
                "vendor": "firebase",
                "vendor_message_id": "firebase-message-id-123",
                "timestamp": "2023-04-17T12:34:56.789Z"
            }
        }