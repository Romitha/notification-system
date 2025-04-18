from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from app.models.notification import Notification, NotificationStatus, DeliveryChannel
from app.core.notification_service import NotificationService
from pydantic import BaseModel, EmailStr
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

router = APIRouter()
notification_service = NotificationService()


class EmailNotificationRequest(BaseModel):
    recipient_email: EmailStr
    subject: str
    content: str
    template_id: Optional[str] = None
    metadata: Optional[dict] = {}


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