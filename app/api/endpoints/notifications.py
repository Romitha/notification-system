from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from app.models.notification import Notification, NotificationStatus, DeliveryChannel, NotificationType, Priority
from app.core.notification_service import NotificationService
from pydantic import BaseModel, EmailStr
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import uuid
router = APIRouter()
notification_service = NotificationService()


class EmailNotificationRequest(BaseModel):
    recipient_email: EmailStr
    subject: str
    content: str
    template_id: Optional[str] = None
    metadata: Optional[dict] = {}

class BulkEmailNotificationRequest(BaseModel):
    recipient_emails: List[EmailStr]
    subject: str
    content: str
    template_id: Optional[str] = None
    metadata: Optional[dict] = {}
    batch_size: int = 100

@router.post("/email", response_model=Notification)
async def send_email_notification(email_req: EmailNotificationRequest):
    """Send a single email notification"""
    try:
        # Create notification object
        notification = Notification(
            type="single",
            priority="medium",
            title=email_req.subject,
            content=email_req.content,
            template_id=email_req.template_id,
            channels=[DeliveryChannel.EMAIL],
            recipients=[email_req.recipient_email],
            metadata=email_req.metadata
        )

        # Send the notification
        created_notification = await notification_service.create_notification(notification)
        # 🔍 Debug output before serialization
        print("✅ CREATED NOTIFICATION (raw):", created_notification)
        return created_notification
    except Exception as e:
        print("❌ EXCEPTION:", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/email/bulk", response_model=List[Notification])
async def send_bulk_email_notification(email_req: BulkEmailNotificationRequest):
    """Send a bulk email notification with batching"""
    try:
        # Create base notification object
        notification = Notification(
            type=NotificationType.BULK,  # Explicitly set type to BULK
            priority=Priority.MEDIUM,
            title=email_req.subject,
            content=email_req.content,
            template_id=email_req.template_id,
            channels=[DeliveryChannel.EMAIL],
            recipients=[],  # Will be set per batch
            metadata=email_req.metadata or {}
        )

        # Split recipients into batches
        all_recipients = email_req.recipient_emails
        batch_size = min(email_req.batch_size, 100)  # Limit maximum batch size to 100
        recipient_groups = [
            all_recipients[i:i + batch_size]
            for i in range(0, len(all_recipients), batch_size)
        ]

        # Create bulk notifications - make sure we don't pass 'type' twice
        notifications = []
        batch_id = f"batch-{uuid.uuid4()}"

        for i, recipients in enumerate(recipient_groups):
            # Create a copy of the metadata to avoid modifying the original
            batch_metadata = dict(notification.metadata or {})

            # Add batch information
            batch_metadata["batch_id"] = batch_id
            batch_metadata["batch_size"] = len(recipient_groups)
            batch_metadata["batch_index"] = i + 1

            # Create a new notification for this batch
            bulk_notification = Notification(
                # Don't include 'type' here since we're copying from the original notification
                title=notification.title,
                content=notification.content,
                template_id=notification.template_id,
                channels=notification.channels,
                priority=notification.priority,
                type=NotificationType.BULK,  # Explicitly set type
                recipients=recipients,
                metadata=batch_metadata
            )

            created_notification = await notification_service.create_notification(bulk_notification)
            notifications.append(created_notification)

        print(f"✅ Created {len(notifications)} bulk notification batches")
        return notifications

    except Exception as e:
        print("❌ BULK EMAIL EXCEPTION:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=Notification)
async def create_notification(notification: Notification):
    """Create a new notification"""
    try:
        created_notification = await notification_service.create_notification(notification)
        return created_notification
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk", response_model=List[Notification])
async def create_bulk_notification(notification: Notification, recipient_groups: List[List[str]]):
    """Create notifications for multiple recipient groups"""
    try:
        created_notifications = await notification_service.create_bulk_notification(
            notification, recipient_groups
        )
        return created_notifications
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{notification_id}", response_model=Notification)
async def get_notification(notification_id: str):
    """Get notification by ID"""
    notification = await notification_service.get_notification(notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification

@router.get("/", response_model=List[Notification])
async def get_notifications(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None
):
    """Get list of notifications with optional filtering"""
    notifications = await notification_service.get_notifications(skip, limit, status)
    return notifications

@router.put("/{notification_id}/status", response_model=Notification)
async def update_notification_status(notification_id: str, status: NotificationStatus):
    """Update notification status"""
    try:
        updated_notification = await notification_service.update_notification_status(
            notification_id, status
        )
        return updated_notification
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))