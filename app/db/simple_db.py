import sqlite3
import json
from app.models.notification import Notification
from app.models.delivery_status import DeliveryStatus
import threading
from datetime import datetime
import uuid

# Thread-local storage for our connection
_local = threading.local()


def get_db_connection():
    """Get a database connection from thread-local storage or create a new one"""
    if not hasattr(_local, 'connection'):
        _local.connection = sqlite3.connect('notification_system.db')
        _local.connection.row_factory = sqlite3.Row
    return _local.connection


def init_db():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create notifications table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
        id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        priority TEXT NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        template_id TEXT,
        scheduled_time TEXT,
        created_at TEXT NOT NULL,
        status TEXT NOT NULL,
        meta_data TEXT
    )
    ''')

    # Create recipients table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS recipients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        notification_id TEXT NOT NULL,
        recipient TEXT NOT NULL,
        FOREIGN KEY (notification_id) REFERENCES notifications(id)
    )
    ''')

    # Create channels table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        notification_id TEXT NOT NULL,
        channel TEXT NOT NULL,
        FOREIGN KEY (notification_id) REFERENCES notifications(id)
    )
    ''')

    # Create delivery_statuses table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS delivery_statuses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        notification_id TEXT NOT NULL,
        recipient TEXT NOT NULL,
        channel TEXT NOT NULL,
        status TEXT NOT NULL,
        vendor TEXT,
        vendor_message_id TEXT,
        error_message TEXT,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (notification_id) REFERENCES notifications(id)
    )
    ''')

    conn.commit()


def save_notification(notification: Notification):
    """Save a notification to the database"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Generate ID if not provided
    if not notification.id:
        notification.id = str(uuid.uuid4())

    # Insert notification
    cursor.execute('''
    INSERT INTO notifications (id, type, priority, title, content, template_id, 
                              scheduled_time, created_at, status, meta_data)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        notification.id,
        notification.type.value if hasattr(notification.type, 'value') else str(notification.type),
        notification.priority.value if hasattr(notification.priority, 'value') else str(notification.priority),
        notification.title,
        notification.content,
        notification.template_id,
        notification.scheduled_time.isoformat() if notification.scheduled_time else None,
        notification.created_at.isoformat(),
        notification.status.value if hasattr(notification.status, 'value') else str(notification.status),
        json.dumps(notification.metadata) if notification.metadata else None
    ))

    # Insert recipients
    for recipient in notification.recipients:
        cursor.execute('''
        INSERT INTO recipients (notification_id, recipient)
        VALUES (?, ?)
        ''', (notification.id, recipient))

    # Insert channels
    for channel in notification.channels:
        cursor.execute('''
        INSERT INTO channels (notification_id, channel)
        VALUES (?, ?)
        ''', (notification.id,
              channel.value if hasattr(channel, 'value') else str(channel)))

    conn.commit()
    return notification


def save_delivery_status(status: DeliveryStatus):
    """Save a delivery status to the database"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
    INSERT INTO delivery_statuses (notification_id, recipient, channel, status, 
                                 vendor, vendor_message_id, error_message, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        status.notification_id,
        status.recipient,
        status.channel,
        status.status,
        status.vendor,
        status.vendor_message_id,
        status.error_message,
        status.timestamp or datetime.now().isoformat()
    ))

    conn.commit()
    return status