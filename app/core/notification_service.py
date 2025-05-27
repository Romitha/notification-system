from typing import List, Optional
from datetime import datetime
from app.models.notification import Notification, NotificationType, NotificationStatus
from app.core.composite_service import CompositeService
from app.core.template_service import TemplateService
from app.db.repository import NotificationRepository
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from app.db.simple_db import save_notification


class NotificationService:
    """Service to manage notifications"""

    def __init__(self, db: AsyncSession = None):
        self.composite_service = CompositeService()
        self.template_service = TemplateService()
        self.db = db
        self.repository = NotificationRepository(db) if db else None

    async def create_notification(self, notification: Notification) -> Notification:
        """Create a new notification"""
        # Process template if needed
        if any(str(channel).lower() == 'email' for channel in notification.channels):
            notification = await self._process_email_template(notification)

        # Ensure notification has an ID
        if not notification.id:
            notification.id = str(uuid.uuid4())

        # Standardize datetime objects to be timezone-naive
        if notification.scheduled_time and notification.scheduled_time.tzinfo is not None:
            notification.scheduled_time = notification.scheduled_time.replace(tzinfo=None)

        # Save notification to database
        try:
            save_notification(notification)
        except Exception as e:
            print(f"Error saving notification to database: {e}")

        # Pass to composite service for processing
        if notification.scheduled_time and notification.scheduled_time > datetime.now():
            await self.composite_service.schedule_notification(notification)
        else:
            await self.composite_service.process_notification(notification)

        return notification

    async def create_bulk_notification(self, notification: Notification, recipient_groups: List[List[str]]) -> List[
        Notification]:
        """Create notifications for multiple recipient groups"""
        notifications = []

        # Generate a batch ID to link these notifications
        batch_id = f"batch-{uuid.uuid4()}"

        # Process each recipient group
        for i, recipients in enumerate(recipient_groups):
            # Create new notification object
            batch_metadata = dict(notification.metadata or {})
            batch_metadata["batch_id"] = batch_id
            batch_metadata["batch_size"] = len(recipient_groups)
            batch_metadata["batch_index"] = i + 1

            bulk_notification = Notification(
                type=NotificationType.BULK,
                priority=notification.priority,
                title=notification.title,
                content=notification.content,
                template_id=notification.template_id,
                channels=notification.channels,
                recipients=recipients,
                metadata=batch_metadata
            )

            # Create through normal flow
            created_notification = await self.create_notification(bulk_notification)
            notifications.append(created_notification)

        return notifications

    async def get_notification(self, notification_id: str) -> Optional[Notification]:
        """Get notification by ID"""
        if not self.repository:
            return None

        return await self.repository.get_notification(notification_id)

    async def get_notifications(self, skip: int = 0, limit: int = 100, status: Optional[str] = None) -> List[
        Notification]:
        """Get list of notifications with optional filtering"""
        if not self.repository:
            return []

        return await self.repository.get_notifications(skip, limit, status)

    async def update_notification_status(self, notification_id: str, status: NotificationStatus) -> Optional[
        Notification]:
        """Update notification status"""
        status_str = status.value if hasattr(status, 'value') else str(status)

        if not self.repository:
            return None

        return await self.repository.update_notification_status(notification_id, status_str)

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