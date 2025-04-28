from fastapi import FastAPI
from fastapi.routing import APIRouter
from contextlib import asynccontextmanager
import threading
from app.api.routes import api_router
from app.config import settings
from app.consumers.email_notification_consumer import EmailNotificationConsumer
from app.consumers.retry_notification_consumer import RetryConsumer, FailedNotificationConsumer

# Global references for threads
email_consumer_thread = None
retry_5m_thread = None
retry_30m_thread = None
failed_notifications_thread = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan hook to start/stop background consumer"""
    global email_consumer_thread, retry_5m_thread, retry_30m_thread, failed_notifications_thread

    # Initialize consumers
    email_consumer = EmailNotificationConsumer()
    retry_5m = RetryConsumer("notifications-retry-5m", 5, "notifications-retry-30m")
    retry_30m = RetryConsumer("notifications-retry-30m", 30, "notifications-failed")
    failed_consumer = FailedNotificationConsumer()

    # Start the Kafka consumers in separate threads
    email_consumer_thread = threading.Thread(target=email_consumer.start_consuming, daemon=True)
    retry_5m_thread = threading.Thread(target=retry_5m.start_consuming, daemon=True)
    retry_30m_thread = threading.Thread(target=retry_30m.start_consuming, daemon=True)
    failed_notifications_thread = threading.Thread(target=failed_consumer.start_consuming, daemon=True)

    email_consumer_thread.start()
    retry_5m_thread.start()
    retry_30m_thread.start()
    failed_notifications_thread.start()

    print("✅ Email consumer started")
    print("✅ Retry consumers started")

    yield  # ⏳ App runs here...

    # Shutdown cleanup
    for consumer in [email_consumer, retry_5m, retry_30m, failed_consumer]:
        if consumer:
            consumer.close()

    print("🛑 Consumers stopped")


# Create FastAPI app with lifespan hook
app = FastAPI(
    title="Notification System API",
    lifespan=lifespan
)

# Include all API routes
app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)