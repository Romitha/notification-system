from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from enum import Enum


class DeliveryStatusType(str, Enum):
    """Enhanced delivery status types"""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    PERMANENTLY_FAILED = "permanently_failed"
    PROCESSING_FAILED = "processing_failed"
    RETRYING = "retrying"


class DeliveryStatus(BaseModel):
    """Enhanced status of notification delivery"""
    notification_id: str
    recipient: str
    channel: str
    status: str  # Use DeliveryStatusType values
    vendor: str
    vendor_message_id: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: Optional[str] = None
    retry_count: Optional[int] = 0
    next_retry_time: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "notification_id": "123e4567-e89b-12d3-a456-426614174000",
                "recipient": "user@example.com",
                "channel": "email",
                "status": "delivered",
                "vendor": "firebase",
                "vendor_message_id": "firebase-message-id-123",
                "timestamp": "2023-04-17T12:34:56.789Z",
                "retry_count": 0,
                "next_retry_time": None
            }
        }
