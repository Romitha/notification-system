# Updated Database Functions for Retry Mechanism
# Add these functions to your app/db/simple_db.py file

import sqlite3
import json
from app.models.notification import Notification
from app.models.delivery_status import DeliveryStatus
import threading
from datetime import datetime, timedelta
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
    """Initialize the database with required tables including new failure tracking"""
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

    # Enhanced delivery_statuses table with retry tracking
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
        retry_count INTEGER DEFAULT 0,
        next_retry_time TEXT,
        final_attempt BOOLEAN DEFAULT 0,
        FOREIGN KEY (notification_id) REFERENCES notifications(id)
    )
    ''')

    # Create permanent_failures table for detailed failure tracking
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS permanent_failures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        notification_id TEXT NOT NULL,
        recipient TEXT NOT NULL,
        channel TEXT NOT NULL,
        total_attempts INTEGER NOT NULL,
        first_attempt_time TEXT NOT NULL,
        final_attempt_time TEXT NOT NULL,
        failure_reason TEXT NOT NULL,
        all_error_messages TEXT,
        notification_data TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (notification_id) REFERENCES notifications(id)
    )
    ''')

    # Create retry_history table for tracking retry attempts
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS retry_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        notification_id TEXT NOT NULL,
        recipient TEXT NOT NULL,
        channel TEXT NOT NULL,
        retry_attempt INTEGER NOT NULL,
        retry_time TEXT NOT NULL,
        error_message TEXT,
        next_retry_scheduled TEXT,
        status TEXT NOT NULL,
        FOREIGN KEY (notification_id) REFERENCES notifications(id)
    )
    ''')

    conn.commit()
    print("✅ Database tables created/updated successfully")


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
    """Enhanced save delivery status with retry tracking"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Determine if this is a final attempt
    final_attempt = status.status in ["permanently_failed", "processing_failed"]

    cursor.execute('''
    INSERT INTO delivery_statuses (notification_id, recipient, channel, status, 
                                 vendor, vendor_message_id, error_message, timestamp,
                                 retry_count, next_retry_time, final_attempt)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        status.notification_id,
        status.recipient,
        status.channel,
        status.status,
        status.vendor,
        status.vendor_message_id,
        status.error_message,
        status.timestamp or datetime.now().isoformat(),
        getattr(status, 'retry_count', 0),
        getattr(status, 'next_retry_time', None),
        1 if final_attempt else 0
    ))

    conn.commit()
    print(f"✅ Saved delivery status: {status.status} for {status.recipient}")
    return status


def save_permanent_failure(notification_id: str, recipient: str, channel: str,
                           total_attempts: int, first_attempt_time: str,
                           failure_reason: str, all_errors: list,
                           notification_data: dict = None):
    """Save permanent failure details for comprehensive tracking"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Combine all error messages
    all_error_messages = " | ".join(all_errors) if all_errors else "No specific errors recorded"

    cursor.execute('''
    INSERT INTO permanent_failures (notification_id, recipient, channel, total_attempts,
                                  first_attempt_time, final_attempt_time, failure_reason,
                                  all_error_messages, notification_data, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        notification_id,
        recipient,
        channel,
        total_attempts,
        first_attempt_time,
        datetime.now().isoformat(),
        failure_reason,
        all_error_messages,
        json.dumps(notification_data) if notification_data else None,
        datetime.now().isoformat()
    ))

    conn.commit()
    print(f"✅ Saved permanent failure record for {recipient} on {channel}")


def save_retry_attempt(notification_id: str, recipient: str, channel: str,
                       retry_attempt: int, error_message: str = None,
                       next_retry_scheduled: str = None):
    """Save retry attempt for tracking"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
    INSERT INTO retry_history (notification_id, recipient, channel, retry_attempt,
                             retry_time, error_message, next_retry_scheduled, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        notification_id,
        recipient,
        channel,
        retry_attempt,
        datetime.now().isoformat(),
        error_message,
        next_retry_scheduled,
        "retrying"
    ))

    conn.commit()
    print(f"✅ Saved retry attempt #{retry_attempt} for {recipient}")


def get_failure_statistics(channel: str = None, days: int = 7):
    """Get failure statistics for monitoring"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Base query for failure statistics
    base_query = '''
    SELECT 
        channel,
        COUNT(*) as total_failures,
        AVG(total_attempts) as avg_attempts,
        MIN(total_attempts) as min_attempts,
        MAX(total_attempts) as max_attempts
    FROM permanent_failures 
    WHERE created_at >= ?
    '''

    params = [start_date.isoformat()]

    if channel:
        base_query += " AND channel = ?"
        params.append(channel)

    base_query += " GROUP BY channel ORDER BY total_failures DESC"

    cursor.execute(base_query, params)
    results = cursor.fetchall()

    # Convert to list of dictionaries
    statistics = []
    for row in results:
        statistics.append({
            "channel": row["channel"],
            "total_failures": row["total_failures"],
            "avg_attempts": round(row["avg_attempts"], 2),
            "min_attempts": row["min_attempts"],
            "max_attempts": row["max_attempts"]
        })

    return statistics


def get_recent_failures(limit: int = 50, channel: str = None):
    """Get recent permanent failures for monitoring"""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = '''
    SELECT notification_id, recipient, channel, total_attempts, 
           failure_reason, final_attempt_time, all_error_messages
    FROM permanent_failures 
    '''

    params = []
    if channel:
        query += " WHERE channel = ?"
        params.append(channel)

    query += " ORDER BY final_attempt_time DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    results = cursor.fetchall()

    # Convert to list of dictionaries
    failures = []
    for row in results:
        failures.append({
            "notification_id": row["notification_id"],
            "recipient": row["recipient"],
            "channel": row["channel"],
            "total_attempts": row["total_attempts"],
            "failure_reason": row["failure_reason"],
            "final_attempt_time": row["final_attempt_time"],
            "error_messages": row["all_error_messages"]
        })

    return failures


def cleanup_old_records(days_to_keep: int = 30):
    """Clean up old records to prevent database bloat"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()

    # Clean up old delivery statuses (keep only final attempts and recent records)
    cursor.execute('''
    DELETE FROM delivery_statuses 
    WHERE timestamp < ? 
    AND final_attempt = 0
    AND status NOT IN ('permanently_failed', 'processing_failed')
    ''', (cutoff_date,))

    deleted_statuses = cursor.rowcount

    # Clean up old retry history
    cursor.execute('''
    DELETE FROM retry_history 
    WHERE retry_time < ?
    ''', (cutoff_date,))

    deleted_retries = cursor.rowcount

    conn.commit()

    print(f"🧹 Cleaned up {deleted_statuses} old delivery statuses and {deleted_retries} retry records")

    return {
        "deleted_statuses": deleted_statuses,
        "deleted_retries": deleted_retries,
        "cutoff_date": cutoff_date
    }


def get_notification_status(notification_id: str):
    """Get complete status of a notification including retry history"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get notification details
    cursor.execute('''
    SELECT * FROM notifications WHERE id = ?
    ''', (notification_id,))

    notification = cursor.fetchone()
    if not notification:
        return None

    # Get delivery statuses
    cursor.execute('''
    SELECT * FROM delivery_statuses WHERE notification_id = ?
    ORDER BY timestamp DESC
    ''', (notification_id,))

    delivery_statuses = cursor.fetchall()

    # Get retry history
    cursor.execute('''
    SELECT * FROM retry_history WHERE notification_id = ?
    ORDER BY retry_time DESC
    ''', (notification_id,))

    retry_history = cursor.fetchall()

    # Get permanent failures
    cursor.execute('''
    SELECT * FROM permanent_failures WHERE notification_id = ?
    ''', (notification_id,))

    permanent_failures = cursor.fetchall()

    return {
        "notification": dict(notification) if notification else None,
        "delivery_statuses": [dict(row) for row in delivery_statuses],
        "retry_history": [dict(row) for row in retry_history],
        "permanent_failures": [dict(row) for row in permanent_failures]
    }


def get_retry_statistics():
    """Get overall retry statistics"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get retry statistics
    cursor.execute('''
    SELECT 
        channel,
        COUNT(*) as total_retries,
        AVG(retry_attempt) as avg_retry_attempt,
        MAX(retry_attempt) as max_retry_attempt
    FROM retry_history 
    GROUP BY channel
    ''')

    retry_stats = cursor.fetchall()

    # Get success rate after retries
    cursor.execute('''
    SELECT 
        channel,
        COUNT(CASE WHEN status = 'delivered' THEN 1 END) as successful_deliveries,
        COUNT(CASE WHEN status = 'permanently_failed' THEN 1 END) as permanent_failures,
        COUNT(*) as total_attempts
    FROM delivery_statuses 
    GROUP BY channel
    ''')

    success_stats = cursor.fetchall()

    return {
        "retry_statistics": [dict(row) for row in retry_stats],
        "success_statistics": [dict(row) for row in success_stats]
    }


def is_notification_permanently_failed(notification_id: str) -> bool:
    """Check if notification is permanently failed in database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if this notification is in permanent_failures table
        cursor.execute('''
            SELECT COUNT(*) FROM permanent_failures 
            WHERE notification_id = ?
        ''', (notification_id,))

        result = cursor.fetchone()
        count = result[0] if result else 0

        if count > 0:
            print(f"🔍 Found {count} permanent failure record(s) for {notification_id}")
            return True

        return False

    except Exception as e:
        print(f"⚠️ Error checking permanent failures: {e}")
        # If we can't check the database, assume it's not permanently failed
        # This prevents notifications from being stuck if there's a DB issue
        return False


def check_table_exists(table_name: str) -> bool:
    """Check if a table exists in the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """, (table_name,))

        return cursor.fetchone() is not None

    except Exception as e:
        print(f"⚠️ Error checking if table {table_name} exists: {e}")
        return False


def check_column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [column[1] for column in cursor.fetchall()]
        return column_name in columns

    except Exception as e:
        print(f"⚠️ Error checking if column {column_name} exists in {table_name}: {e}")
        return False