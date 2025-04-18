from typing import List, Dict, Any
from app.models.notification import Notification
from app.models.delivery_status import DeliveryStatus
from app.vendors.firebase import FirebaseClient
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings
import uuid

class EmailHandler:
    """Handler for email notifications"""

    def __init__(self):
        self.firebase_client = FirebaseClient()

    async def send(self, notification: Notification) -> List[DeliveryStatus]:
        """Send email notifications to recipients"""
        statuses = []

        # Use a fallback ID if notification.id is None
        notification_id = notification.id or f"temp-{uuid.uuid4()}"

        # Get email template content
        email_content = notification.content

        # Send to each recipient
        for recipient in notification.recipients:
            try:
                # Use Firebase or direct SMTP based on configuration
                if settings.USE_FIREBASE_EMAIL:
                    result = await self.firebase_client.send_email(
                        to=recipient,
                        subject=notification.title,
                        content=email_content,
                        metadata=notification.metadata
                    )
                    vendor = "firebase"
                    vendor_message_id = result.get("id")
                else:
                    # Direct SMTP sending (for development/testing)
                    result = await self._send_via_smtp(
                        to=recipient,
                        subject=notification.title,
                        content=email_content
                    )
                    vendor = "smtp"
                    vendor_message_id = "local-smtp-id"

                # Record delivery status - use notification_id instead of notification.id
                status = DeliveryStatus(
                    notification_id=notification_id,  # Use our fallback ID if needed
                    recipient=recipient,
                    channel="email",
                    status="delivered" if result.get("success") else "failed",
                    vendor=vendor,
                    vendor_message_id=vendor_message_id,
                    timestamp=result.get("timestamp")
                )
                statuses.append(status)

            except Exception as e:
                # Handle failure
                print(f"Email sending error: {str(e)}")
                status = DeliveryStatus(
                    notification_id=notification_id,  # Use our fallback ID here too
                    recipient=recipient,
                    channel="email",
                    status="failed",
                    vendor="unknown",
                    error_message=str(e)
                )
                statuses.append(status)

        return statuses

    async def _send_via_smtp(self, to: str, subject: str, content: str) -> Dict[str, Any]:
        """Send email via SMTP (for development/testing)"""
        from datetime import datetime

        # For development, just log the email instead of sending
        print(f"\n--- DEVELOPMENT EMAIL ---")
        print(f"To: {to}")
        print(f"Subject: {subject}")
        print(f"Content: {content}")
        print(f"--- END EMAIL ---\n")

        # In a real implementation, you would use something like:
        """
        msg = MIMEMultipart()
        msg['From'] = settings.SMTP_FROM_EMAIL
        msg['To'] = to
        msg['Subject'] = subject
        msg.attach(MIMEText(content, 'plain'))

        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
        """

        # Simulate success
        return {
            "success": True,
            "id": f"dev-email-{hash(to)}-{datetime.now().timestamp()}",
            "timestamp": datetime.now().isoformat()
        }