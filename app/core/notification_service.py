from typing import List, Optional
from datetime import datetime
from app.models.notification import Notification, NotificationType
from app.core.composite_service import CompositeService
from app.core.template_service import TemplateService

class NotificationService:
    """Service to manage notifications"""

    def __init__(self):
        self.composite_service = CompositeService()
        self.template_service = TemplateService()

    async def create_notification(self, notification: Notification) -> Notification:
        """Create a new notification"""
        # Process template if needed
        if "email" in notification.channels:
            notification = await self._process_email_template(notification)

        # Save notification to database
        # Logic for creating notification record

        # Pass to composite service for processing
        if notification.scheduled_time and notification.scheduled_time > datetime.now():
            await self.composite_service.schedule_notification(notification)
        else:
            await self.composite_service.process_notification(notification)

        return notification

    async def _process_email_template(self, notification: Notification) -> Notification:
        """Process email template for notification content"""
        # If no template specified or template not found, use default
        if not notification.template_id:
            # No need to fetch template, content is already set
            pass
        else:
            try:
                # Get template from template service
                template = await self.template_service.get_template(notification.template_id)

                # Apply template to notification content
                notification.content = await self.template_service.apply_template(
                    template,
                    notification.content,
                    notification.metadata
                )
            except Exception as e:
                print(f"Error applying template: {str(e)}. Using raw content instead.")
                # Continue with the raw content

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