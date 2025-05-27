from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from app.db.models import DBNotification, DBRecipient, DBChannel, DBDeliveryStatus, DBTemplate
from app.models.notification import Notification, NotificationType, Priority, DeliveryChannel, NotificationStatus
from app.models.delivery_status import DeliveryStatus
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime


class NotificationRepository:
    """Repository for notification database operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_notification(self, notification: Notification) -> Notification:
        """Create a new notification record in the database"""
        # Generate ID if not provided
        if not notification.id:
            notification.id = str(uuid.uuid4())

        # Create DB notification object
        db_notification = DBNotification(
            id=notification.id,
            type=notification.type.value if hasattr(notification.type, 'value') else str(notification.type),
            priority=notification.priority.value if hasattr(notification.priority, 'value') else str(
                notification.priority),
            title=notification.title,
            content=notification.content,
            template_id=notification.template_id,
            scheduled_time=notification.scheduled_time,
            status=notification.status.value if hasattr(notification.status, 'value') else str(notification.status),
            metadata=notification.metadata
        )

        # Add recipients
        for recipient in notification.recipients:
            db_notification.recipients.append(DBRecipient(recipient=recipient))

        # Add channels
        for channel in notification.channels:
            db_notification.channels.append(DBChannel(
                channel=channel.value if hasattr(channel, 'value') else str(channel)
            ))

        # Add to database
        self.db.add(db_notification)
        await self.db.commit()
        await self.db.refresh(db_notification)

        # Convert back to Notification model
        return await self._db_to_notification(db_notification)

    async def get_notification(self, notification_id: str) -> Optional[Notification]:
        """Get a notification by ID"""
        query = select(DBNotification).where(DBNotification.id == notification_id)
        result = await self.db.execute(query)
        db_notification = result.scalars().first()

        if not db_notification:
            return None

        return await self._db_to_notification(db_notification)

    async def update_notification_status(self, notification_id: str, status: str) -> Optional[Notification]:
        """Update a notification's status"""
        query = update(DBNotification).where(DBNotification.id == notification_id).values(status=status)
        await self.db.execute(query)
        await self.db.commit()

        return await self.get_notification(notification_id)

    async def get_notifications(self, skip: int = 0, limit: int = 100, status: Optional[str] = None) -> List[
        Notification]:
        """Get a list of notifications with optional filtering"""
        query = select(DBNotification)

        if status:
            query = query.where(DBNotification.status == status)

        query = query.order_by(DBNotification.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        db_notifications = result.scalars().all()

        notifications = []
        for db_notification in db_notifications:
            notification = await self._db_to_notification(db_notification)
            notifications.append(notification)

        return notifications

    async def get_scheduled_notifications(self, now: datetime) -> List[Notification]:
        """Get notifications that are scheduled to be sent before the given time"""
        query = select(DBNotification).where(
            (DBNotification.scheduled_time <= now) &
            (DBNotification.status == "scheduled")
        )
        result = await self.db.execute(query)
        db_notifications = result.scalars().all()

        notifications = []
        for db_notification in db_notifications:
            notification = await self._db_to_notification(db_notification)
            notifications.append(notification)

        return notifications

    async def add_delivery_status(self, delivery_status: DeliveryStatus) -> DeliveryStatus:
        """Add a delivery status record"""
        db_status = DBDeliveryStatus(
            notification_id=delivery_status.notification_id,
            recipient=delivery_status.recipient,
            channel=delivery_status.channel,
            status=delivery_status.status,
            vendor=delivery_status.vendor,
            vendor_message_id=delivery_status.vendor_message_id,
            error_message=delivery_status.error_message,
            timestamp=datetime.fromisoformat(delivery_status.timestamp) if isinstance(delivery_status.timestamp,
                                                                                      str) else delivery_status.timestamp
        )

        self.db.add(db_status)
        await self.db.commit()
        await self.db.refresh(db_status)

        return DeliveryStatus(
            notification_id=db_status.notification_id,
            recipient=db_status.recipient,
            channel=db_status.channel,
            status=db_status.status,
            vendor=db_status.vendor,
            vendor_message_id=db_status.vendor_message_id,
            error_message=db_status.error_message,
            timestamp=db_status.timestamp.isoformat() if db_status.timestamp else None
        )

    async def _db_to_notification(self, db_notification: DBNotification) -> Notification:
        """Convert DB notification to Notification model"""
        # Get recipients
        recipients = [r.recipient for r in db_notification.recipients]

        # Get channels
        channels = [self._string_to_channel(c.channel) for c in db_notification.channels]

        # Create notification
        return Notification(
            id=db_notification.id,
            type=self._string_to_type(db_notification.type),
            priority=self._string_to_priority(db_notification.priority),
            title=db_notification.title,
            content=db_notification.content,
            template_id=db_notification.template_id,
            channels=channels,
            recipients=recipients,
            scheduled_time=db_notification.scheduled_time,
            created_at=db_notification.created_at,
            status=self._string_to_status(db_notification.status),
            metadata=db_notification.metadata or {}
        )

    def _string_to_type(self, type_str: str) -> NotificationType:
        """Convert string to NotificationType enum"""
        try:
            return NotificationType(type_str)
        except ValueError:
            return NotificationType.SINGLE

    def _string_to_priority(self, priority_str: str) -> Priority:
        """Convert string to Priority enum"""
        try:
            return Priority(priority_str)
        except ValueError:
            return Priority.MEDIUM

    def _string_to_channel(self, channel_str: str) -> DeliveryChannel:
        """Convert string to DeliveryChannel enum"""
        try:
            return DeliveryChannel(channel_str)
        except ValueError:
            return DeliveryChannel.EMAIL

    def _string_to_status(self, status_str: str) -> NotificationStatus:
        """Convert string to NotificationStatus enum"""
        try:
            return NotificationStatus(status_str)
        except ValueError:
            return NotificationStatus.PENDING