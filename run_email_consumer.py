from app.consumers.email_notification_consumer import EmailNotificationConsumer
import signal
import sys


def handle_shutdown(sig, frame):
    print("Shutting down email consumer...")
    if consumer:
        consumer.close()
    sys.exit(0)


if __name__ == "__main__":
    consumer = EmailNotificationConsumer()

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    try:
        consumer.start_consuming()
    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        consumer.close()