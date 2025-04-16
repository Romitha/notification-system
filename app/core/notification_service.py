from typing import List, Optional
from datetime import datetime
from app.models.notification import Notification, NotificationType
from app.core.composite_service import CompositeService

class NotificationService:
    """Service to manage notifications"""
    
    def __init__(self):
        self.composite_service = CompositeService()
    
    async def create_notification(self, notification: Notification) -> Notification:
        """Create a new notification"""
        # Save notification to database
        # Logic for creating notification record
        
        # Pass to composite service for processing
        if notification.scheduled_time and notification.scheduled_time > datetime.now():
            await self.composite_service.schedule_notification(notification)
        else:
            await self.composite_service.process_notification(notification)
            
        return notification
    
    async def create_bulk_notification(self, notification: Notification, recipient_groups: List[List[str]]) -> List[Notification]:
        """Create notifications for multiple recipient groups"""
        notifications = []
        
        for recipients in recipient_groups:
            bulk_notification = Notification(
                **notification.dict(exclude={"id", "recipients"}),
                recipients=recipients,
                type=NotificationType.BULK
            )
            created_notification = await self.create_notification(bulk_notification)
            notifications.append(created_notification)
            
        return notifications
    
    async def get_notification(self, notification_id: str) -> Optional[Notification]:
        """Get notification by ID"""
        # Logic to retrieve notification from database
        pass
    
    async def get_notifications(self, skip: int = 0, limit: int = 100, status: Optional[str] = None) -> List[Notification]:
        """Get list of notifications with optional filtering"""
        # Logic to retrieve notifications from database
        pass
    
    async def update_notification_status(self, notification_id: str, status: str) -> Notification:
        """Update notification status"""
        # Logic to update notification status
        pass