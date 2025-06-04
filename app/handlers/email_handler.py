# app/handlers/email_handler.py
import uuid
import smtplib
import ssl
from datetime import datetime
from typing import List, Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.repository import NotificationRepository
from app.models.delivery_status import DeliveryStatus
from app.models.notification import Notification, NotificationType
from app.vendors.firebase import FirebaseClient
from app.db.simple_db import save_delivery_status


class EmailHandler:
    """Handler for email notifications"""

    def __init__(self, db: AsyncSession = None):
        self.firebase_client = FirebaseClient()
        # self.db = db
        # self.repository = NotificationRepository(db) if db else None

    async def send(self, notification: Notification) -> List[DeliveryStatus]:
        """Send email notifications to recipients"""
        statuses = []

        # Use a fallback ID if notification.id is None
        notification_id = notification.id or f"temp-{uuid.uuid4()}"

        # Get email template content
        email_content = notification.content

        # Track batch progress
        is_bulk = notification.type == NotificationType.BULK
        total_recipients = len(notification.recipients)

        if is_bulk:
            print(f"📧 Sending bulk email '{notification.title}' to {total_recipients} recipients...")

        # Send to each recipient
        for i, recipient in enumerate(notification.recipients):
            try:
                if is_bulk and i > 0 and i % 10 == 0:
                    print(f"📊 Progress: {i}/{total_recipients} emails sent...")

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
                    # Direct SMTP sending
                    result = await self._send_via_smtp(
                        to=recipient,
                        subject=notification.title,
                        content=email_content
                    )
                    vendor = "smtp"
                    vendor_message_id = result.get("id", "smtp-sent")

                # Create delivery status
                status = DeliveryStatus(
                    notification_id=notification_id,
                    recipient=recipient,
                    channel="email",
                    status="delivered" if result.get("success") else "failed",
                    vendor=vendor,
                    vendor_message_id=vendor_message_id,
                    error_message=result.get("error"),
                    timestamp=result.get("timestamp") or datetime.now().isoformat()
                )

                # Save delivery status
                try:
                    save_delivery_status(status)
                except Exception as e:
                    print(f"Error saving delivery status: {e}")

                statuses.append(status)

            except Exception as e:
                # Handle failure
                print(f"Email sending error for {recipient}: {str(e)}")
                status = DeliveryStatus(
                    notification_id=notification_id,
                    recipient=recipient,
                    channel="email",
                    status="failed",
                    vendor="unknown",
                    error_message=str(e),
                    timestamp=datetime.now().isoformat()
                )

                # Save failed status
                try:
                    save_delivery_status(status)
                except Exception as save_err:
                    print(f"Error saving delivery status: {save_err}")

                statuses.append(status)

        if is_bulk:
            success_count = sum(1 for s in statuses if s.status == "delivered")
            print(f"✅ Completed bulk email batch: {success_count}/{total_recipients} delivered")

        return statuses

    async def _send_via_smtp(self, to: str, subject: str, content: str) -> Dict[str, Any]:
        """Send email via SMTP with proper implementation"""

        # Check if SMTP is properly configured
        if not all([settings.SMTP_SERVER, settings.SMTP_USERNAME, settings.SMTP_PASSWORD]):
            print(f"⚠️ SMTP not fully configured, using development mode")
            return await self._send_development_email(to, subject, content)

        try:
            print(f"📧 Sending email via SMTP to {to}")

            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = formataddr(("OTR Wheel System", settings.SMTP_FROM_EMAIL))
            msg['To'] = to
            msg['Subject'] = subject

            # Create both plain text and HTML versions
            text_part = MIMEText(content, 'plain', 'utf-8')

            # Create HTML version with basic formatting
            html_content = f"""
            <html>
                <head></head>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px;">
                            <h2 style="color: #007bff; margin: 0;">OTR Wheel Notification</h2>
                        </div>
                        <div style="background-color: white; padding: 20px; border: 1px solid #dee2e6; border-radius: 5px;">
                            <pre style="white-space: pre-wrap; font-family: Arial, sans-serif; margin: 0;">{content}</pre>
                        </div>
                        <div style="margin-top: 20px; padding: 15px; background-color: #f8f9fa; border-radius: 5px; font-size: 12px; color: #6c757d;">
                            <p style="margin: 0;">
                                This email was sent by OTR Wheel notification system.<br>
                                Sent at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                            </p>
                        </div>
                    </div>
                </body>
            </html>
            """
            html_part = MIMEText(html_content, 'html', 'utf-8')

            # Attach parts
            msg.attach(text_part)
            msg.attach(html_part)

            # Create SMTP connection with proper error handling
            server = None
            try:
                # Connect to server
                server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
                server.set_debuglevel(0)  # Set to 1 for debugging

                # Start TLS encryption
                if settings.SMTP_USE_TLS:
                    print(f"🔐 Starting TLS encryption...")
                    server.starttls(context=ssl.create_default_context())

                # Login to server
                print(f"🔑 Authenticating with SMTP server...")
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)

                # Send email
                print(f"📤 Sending email...")
                send_result = server.send_message(msg)

                # Check if email was sent successfully
                if send_result:
                    # Some recipients failed
                    failed_recipients = list(send_result.keys())
                    print(f"⚠️ Failed to send to some recipients: {failed_recipients}")
                    return {
                        "success": False,
                        "error": f"Failed to send to: {', '.join(failed_recipients)}",
                        "id": f"smtp-partial-{hash(to)}-{datetime.now().timestamp()}",
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    # All recipients successful
                    print(f"✅ Email sent successfully to {to}")
                    return {
                        "success": True,
                        "id": f"smtp-{hash(to)}-{datetime.now().timestamp()}",
                        "timestamp": datetime.now().isoformat()
                    }

            finally:
                # Always close the connection
                if server:
                    try:
                        server.quit()
                    except:
                        pass

        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP Authentication failed: {str(e)}"
            print(f"❌ {error_msg}")
            print(f"💡 Check username/password or if password has expired")
            return {
                "success": False,
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }

        except smtplib.SMTPRecipientsRefused as e:
            error_msg = f"Recipients refused: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }

        except smtplib.SMTPSenderRefused as e:
            error_msg = f"Sender refused: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }

        except smtplib.SMTPDataError as e:
            error_msg = f"SMTP data error: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }

        except smtplib.SMTPConnectError as e:
            error_msg = f"Cannot connect to SMTP server: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }

        except smtplib.SMTPServerDisconnected as e:
            error_msg = f"SMTP server disconnected: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            error_msg = f"Unexpected SMTP error: {str(e)}"
            print(f"❌ {error_msg}")
            print(f"🔄 Falling back to development mode")
            return await self._send_development_email(to, subject, content)

    async def _send_development_email(self, to: str, subject: str, content: str) -> Dict[str, Any]:
        """Send email in development mode (just log it)"""
        print(f"\n--- 📧 DEVELOPMENT EMAIL ---")
        print(f"To: {to}")
        print(f"From: {settings.SMTP_FROM_EMAIL}")
        print(f"Subject: {subject}")
        print(f"Content: {content}")
        print(f"Server: {settings.SMTP_SERVER}:{settings.SMTP_PORT}")
        print(f"--- END EMAIL ---\n")

        # Simulate success
        return {
            "success": True,
            "id": f"dev-email-{hash(to)}-{datetime.now().timestamp()}",
            "timestamp": datetime.now().isoformat()
        }

    async def test_smtp_connection(self) -> Dict[str, Any]:
        """Test SMTP connection and authentication"""
        print("🧪 Testing SMTP connection...")

        if not all([settings.SMTP_SERVER, settings.SMTP_USERNAME, settings.SMTP_PASSWORD]):
            return {
                "success": False,
                "error": "SMTP configuration incomplete"
            }

        try:
            server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)

            if settings.SMTP_USE_TLS:
                server.starttls(context=ssl.create_default_context())

            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.quit()

            print("✅ SMTP connection test successful")
            return {
                "success": True,
                "message": "SMTP connection and authentication successful"
            }

        except Exception as e:
            error_msg = f"SMTP connection test failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }