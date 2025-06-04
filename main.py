# main.py - Updated with Configurable Retry System

import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from app.api.routes import api_router
from app.consumers.email_notification_consumer import EmailNotificationConsumer
from app.consumers.sms_notification_consumer import SMSNotificationConsumer
from app.consumers.retry_notification_consumer import RetryConsumer, FailedNotificationConsumer
from app.db.simple_db import init_db
from app.config import settings
from fastapi.responses import JSONResponse

# Threads
email_consumer_thread = None
retry_short_thread = None
retry_long_thread = None
failed_notifications_thread = None
sms_consumer_thread = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan hook to start/stop background consumers with configurable retry"""
    global email_consumer_thread, retry_short_thread, retry_long_thread, failed_notifications_thread, sms_consumer_thread

    # Print retry configuration on startup
    print("🚀 Starting Notification System with Configurable Retry Mechanism")
    print("=" * 70)
    print(settings.retry_config_summary)
    print("=" * 70)

    # Initialize SQLite database
    try:
        init_db()
        print("✅ Database initialized")
    except Exception as e:
        print(f"⚠️ Database initialization error: {e}")

    # Initialize consumers
    email_consumer = EmailNotificationConsumer()
    sms_consumer = SMSNotificationConsumer()

    # 🎯 CONFIGURABLE RETRY CONSUMERS
    # Use settings to determine delay times
    delays = settings.retry_delays

    print(f"🔧 Creating retry consumers with configured delays:")
    print(f"   Short delay: {delays['first_delay_seconds']}s")
    print(f"   Long delay: {delays['final_delay_seconds']}s")

    # Create retry consumers with configurable delays
    retry_short = RetryConsumer(
        retry_topic=settings.RETRY_TOPIC_SHORT,
        delay_minutes=delays['first_delay'],  # Uses config (e.g., 0.5 min for testing, 5 min for prod)
        next_retry_topic=settings.RETRY_TOPIC_LONG
    )

    retry_long = RetryConsumer(
        retry_topic=settings.RETRY_TOPIC_LONG,
        delay_minutes=delays['final_delay'],  # Uses config (e.g., 1 min for testing, 30 min for prod)
        next_retry_topic=settings.FAILED_TOPIC
    )

    failed_consumer = FailedNotificationConsumer()

    # Start the Kafka consumers in separate threads
    email_consumer_thread = threading.Thread(target=email_consumer.start_consuming, daemon=True)
    sms_consumer_thread = threading.Thread(target=sms_consumer.start_consuming, daemon=True)
    retry_short_thread = threading.Thread(target=retry_short.start_consuming, daemon=True)
    retry_long_thread = threading.Thread(target=retry_long.start_consuming, daemon=True)
    failed_notifications_thread = threading.Thread(target=failed_consumer.start_consuming, daemon=True)

    email_consumer_thread.start()
    sms_consumer_thread.start()
    retry_short_thread.start()
    retry_long_thread.start()
    failed_notifications_thread.start()

    mode = "TESTING" if settings.TESTING_MODE else "PRODUCTION"
    print(f"✅ All consumers started in {mode} mode")
    print(f"📧 Email consumer: Ready")
    print(f"📱 SMS consumer: Ready")
    print(f"🔄 Short retry consumer: {delays['first_delay_seconds']}s delay")
    print(f"🔄 Long retry consumer: {delays['final_delay_seconds']}s delay")
    print(f"❌ Failed consumer: Ready for monitoring")

    yield  # ⏳ App runs here...

    # Shutdown cleanup
    print("🛑 Shutting down consumers...")
    for consumer in [email_consumer, sms_consumer, retry_short, retry_long, failed_consumer]:
        if consumer:
            consumer.close()

    print("🛑 All consumers stopped")


# Create FastAPI app with lifespan hook
app = FastAPI(
    title="Notification System API",
    description="Enhanced notification system with configurable retry mechanism",
    version="2.1.0",
    lifespan=lifespan
)

# Include API routes
app.include_router(api_router, prefix="/api")


# Add configuration endpoint
@app.get("/api/config/retry")
async def get_retry_config():
    """Get current retry configuration"""
    delays = settings.retry_delays

    return {
        "retry_configuration": {
            "mode": "testing" if settings.TESTING_MODE else "production",
            "max_attempts": settings.MAX_RETRY_ATTEMPTS,
            "delays": {
                "first_retry_seconds": delays['first_delay_seconds'],
                "second_retry_seconds": delays['second_delay_seconds'],
                "final_retry_seconds": delays['final_delay_seconds']
            },
            "topics": {
                "short_retry": settings.RETRY_TOPIC_SHORT,
                "long_retry": settings.RETRY_TOPIC_LONG,
                "failed": settings.FAILED_TOPIC
            }
        },
        "timeline_example": {
            "attempt_1": "0 seconds (initial)",
            "attempt_2": f"{delays['first_delay_seconds']} seconds later",
            "attempt_3": f"{delays['first_delay_seconds'] + delays['second_delay_seconds']} seconds later",
            "attempt_4": f"{delays['first_delay_seconds'] + delays['second_delay_seconds'] + delays['final_delay_seconds']} seconds later",
            "permanent_failure": f"After {delays['first_delay_seconds'] + delays['second_delay_seconds'] + delays['final_delay_seconds']} seconds if all attempts fail"
        }
    }


# Add endpoint to change retry mode
@app.post("/api/config/retry/mode/{mode}")
async def set_retry_mode(mode: str):
    """Change retry mode (testing/production) - requires restart"""
    if mode not in ["testing", "production"]:
        return {"error": "Mode must be 'testing' or 'production'"}

    import os

    # Update environment variable
    if mode == "testing":
        os.environ["TESTING_MODE"] = "True"
        message = "Retry mode set to TESTING (fast retries). Restart application to apply."
    else:
        os.environ["TESTING_MODE"] = "False"
        message = "Retry mode set to PRODUCTION (normal retries). Restart application to apply."

    return {
        "message": message,
        "current_mode": "testing" if settings.TESTING_MODE else "production",
        "restart_required": True
    }


# Enhanced retry statistics endpoint
@app.get("/api/retry-stats")
async def get_retry_stats():
    """Get retry statistics with configuration info"""
    try:
        from app.db.simple_db import get_retry_statistics, get_failure_statistics

        retry_stats = get_retry_statistics()
        failure_stats_email = get_failure_statistics(channel="email", days=7)
        failure_stats_sms = get_failure_statistics(channel="sms", days=7)

        delays = settings.retry_delays

        return {
            "configuration": {
                "mode": "testing" if settings.TESTING_MODE else "production",
                "max_attempts": settings.MAX_RETRY_ATTEMPTS,
                "retry_delays_seconds": {
                    "first": delays['first_delay_seconds'],
                    "second": delays['second_delay_seconds'],
                    "final": delays['final_delay_seconds']
                }
            },
            "retry_statistics": retry_stats,
            "failure_statistics": {
                "email": failure_stats_email,
                "sms": failure_stats_sms
            }
        }
    except Exception as e:
        return {"error": str(e)}


# Add endpoint to test retry mechanism
@app.post("/api/test/retry")
async def test_retry_mechanism():
    """Send a test notification that will fail for testing retry mechanism"""
    test_notification = {
        "recipient_email": "invalid@nonexistent-domain-for-testing.xyz",
        "subject": "Retry Test",
        "content": "This email should fail and trigger retry mechanism"
    }

    delays = settings.retry_delays
    mode = "TESTING" if settings.TESTING_MODE else "PRODUCTION"

    return {
        "message": f"Test notification sent - will fail and trigger retry mechanism in {mode} mode",
        "expected_timeline": {
            "initial_attempt": "Immediate",
            "retry_1": f"After {delays['first_delay_seconds']} seconds",
            "retry_2": f"After {delays['second_delay_seconds']} more seconds",
            "retry_3": f"After {delays['final_delay_seconds']} more seconds",
            "permanent_failure": "If all retries fail"
        },
        "monitor_logs": "Watch console output to see retry attempts"
    }


if __name__ == "__main__":
    import uvicorn

    # Print startup configuration
    print("🚀 Starting Notification System")
    print(settings.retry_config_summary)

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)