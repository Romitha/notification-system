from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.models.notification import NotificationType, Priority, DeliveryChannel, NotificationStatus

Base = declarative_base()


class DBNotification(Base):
    """Database model for notifications"""
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(String(10), nullable=False)
    priority = Column(String(10), nullable=False, default="medium")
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    template_id = Column(String(36), nullable=True)
    scheduled_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    status = Column(String(20), nullable=False, default="pending")
    meta_data = Column(JSON, nullable=True)

    # Relationships
    recipients = relationship("DBRecipient", back_populates="notification", cascade="all, delete-orphan")
    channels = relationship("DBChannel", back_populates="notification", cascade="all, delete-orphan")
    delivery_statuses = relationship("DBDeliveryStatus", back_populates="notification", cascade="all, delete-orphan")


class DBRecipient(Base):
    """Database model for notification recipients"""
    __tablename__ = "recipients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    notification_id = Column(String(36), ForeignKey("notifications.id"), nullable=False)
    recipient = Column(String(255), nullable=False)

    # Relationships
    notification = relationship("DBNotification", back_populates="recipients")


class DBChannel(Base):
    """Database model for notification channels"""
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    notification_id = Column(String(36), ForeignKey("notifications.id"), nullable=False)
    channel = Column(String(20), nullable=False)

    # Relationships
    notification = relationship("DBNotification", back_populates="channels")


class DBDeliveryStatus(Base):
    """Database model for delivery status tracking"""
    __tablename__ = "delivery_statuses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    notification_id = Column(String(36), ForeignKey("notifications.id"), nullable=False)
    recipient = Column(String(255), nullable=False)
    channel = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False)
    vendor = Column(String(50), nullable=True)
    vendor_message_id = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.now)

    # Relationships
    notification = relationship("DBNotification", back_populates="delivery_statuses")


class DBTemplate(Base):
    """Database model for notification templates"""
    __tablename__ = "templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    subject = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_active = Column(Boolean, default=True)
    meta_data = Column(JSON, nullable=True)