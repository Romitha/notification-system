from fastapi import FastAPI
from fastapi.routing import APIRouter
from contextlib import asynccontextmanager
import threading
from app.api.routes import api_router
from app.config import settings
from app.consumers.email_notification_consumer import EmailNotificationConsumer

# Global reference for thread
email_consumer_thread = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan hook to start/stop background consumer"""
    global email_consumer_thread
    consumer = EmailNotificationConsumer()

    # Start the Kafka consumer in a separate thread
    email_consumer_thread = threading.Thread(target=consumer.start_consuming, daemon=True)
    email_consumer_thread.start()
    print("✅ Email consumer started")

    yield  # ⏳ App runs here...

    # Shutdown cleanup
    if consumer:
        consumer.close()
        print("🛑 Email consumer stopped")

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
