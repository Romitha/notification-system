# test_email_smtp.py
import smtplib
import sys
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_office365_smtp():
    """Test Office 365 SMTP configuration"""
    print("📧 Testing Office 365 SMTP Configuration")
    print("=" * 50)

    # SMTP Configuration
    smtp_server = "smtp.office365.com"
    smtp_port = 587
    smtp_username = "systeminfo@otrwheel.com"
    smtp_password = "Waterfall25!"
    from_email = "systeminfo@otrwheel.com"

    # Test email details
    to_email = "janith@example.com"  # Change this to your email for testing
    subject = "OTR Wheel SMTP Test"
    body = f"""
Hello!

This is a test email from OTR Wheel notification system.

SMTP Configuration Test Results:
✅ Server: {smtp_server}
✅ Port: {smtp_port}
✅ Username: {smtp_username}
✅ From: {from_email}
✅ TLS: Enabled

Sent at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Best regards,
OTR Wheel System
"""

    print(f"📋 SMTP Server: {smtp_server}")
    print(f"📋 Port: {smtp_port}")
    print(f"📋 Username: {smtp_username}")
    print(f"📋 From Email: {from_email}")
    print(f"📋 Password: {'*' * len(smtp_password)}")
    print("-" * 30)

    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        print("📧 Creating SMTP connection...")

        # Create SMTP connection
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.set_debuglevel(1)  # Enable debug output

        print("🔐 Starting TLS...")
        server.starttls()  # Enable TLS

        print("🔑 Logging in...")
        server.login(smtp_username, smtp_password)

        print("📤 Sending email...")
        server.send_message(msg)

        print("✅ Email sent successfully!")
        print(f"📧 Sent to: {to_email}")

        server.quit()
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Authentication failed: {str(e)}")
        print("💡 Possible issues:")
        print("   1. Username/password incorrect")
        print("   2. Account might need multi-factor authentication")
        print("   3. Account might be locked")
        return False

    except smtplib.SMTPConnectError as e:
        print(f"❌ Connection failed: {str(e)}")
        print("💡 Check network connection and server details")
        return False

    except smtplib.SMTPException as e:
        print(f"❌ SMTP error: {str(e)}")
        return False

    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False


def test_via_notification_system():
    """Test email via your notification system"""
    print("\n📧 Testing via Notification System")
    print("=" * 50)

    try:
        from app.handlers.email_handler import EmailHandler
        from app.models.notification import Notification, NotificationType, Priority, DeliveryChannel
        import asyncio

        async def send_test_email():
            # Create email handler
            email_handler = EmailHandler()

            # Create test notification
            notification = Notification(
                type=NotificationType.SINGLE,
                priority=Priority.MEDIUM,
                title="OTR Wheel SMTP Test via Notification System",
                content="This is a test email sent through the OTR Wheel notification system using Office 365 SMTP!",
                channels=[DeliveryChannel.EMAIL],
                recipients=["janith2011@gmail.com"],  # Change to your email
                metadata={"test": True}
            )

            print("📤 Sending test email via notification system...")
            statuses = await email_handler.send(notification)

            for status in statuses:
                if status.status == "delivered":
                    print(f"✅ Email delivered to {status.recipient}")
                else:
                    print(f"❌ Email failed to {status.recipient}: {status.error_message}")

            return len([s for s in statuses if s.status == "delivered"]) > 0

        return asyncio.run(send_test_email())

    except ImportError:
        print("⚠️ Notification system not available for testing")
        return False
    except Exception as e:
        print(f"❌ Error testing notification system: {str(e)}")
        return False


def show_configuration_summary():
    """Show the complete configuration summary"""
    print("\n📋 Complete Email Configuration")
    print("=" * 50)

    config = {
        "SMTP_SERVER": "smtp.office365.com",
        "SMTP_PORT": "587",
        "SMTP_USERNAME": "systeminfo@otrwheel.com",
        "SMTP_PASSWORD": "Waterfall25!",
        "SMTP_FROM_EMAIL": "systeminfo@otrwheel.com",
        "SMTP_USE_TLS": "True",
        "USE_FIREBASE_EMAIL": "False"
    }

    print("Add these to your .env file:")
    print("-" * 30)
    for key, value in config.items():
        if "PASSWORD" in key:
            print(f"{key}={value}")  # Show password for copy-paste
        else:
            print(f"{key}={value}")

    print("\n💡 Notes:")
    print("1. Username = Email address for Office 365")
    print("2. Make sure to change password after first login")
    print("3. If 2FA is enabled, you might need an app password")
    print("4. Test with your own email address first")


if __name__ == "__main__":
    print("🚀 OTR Wheel Email Configuration Test")
    print("=" * 50)

    # Show configuration
    show_configuration_summary()

    # Test SMTP directly
    print(f"\n{'=' * 50}")
    smtp_success = test_office365_smtp()

    # Test via notification system
    notification_success = test_via_notification_system()

    print(f"\n{'=' * 50}")
    print("📊 Test Results:")
    print(f"Direct SMTP: {'✅ PASS' if smtp_success else '❌ FAIL'}")
    print(f"Notification System: {'✅ PASS' if notification_success else '❌ FAIL'}")

    if smtp_success:
        print("\n🎉 Email configuration is working!")
        print("📧 You can now send emails via OTR Wheel notification system")
    else:
        print("\n⚠️ Email configuration needs attention")
        print("💡 Check the error messages above for troubleshooting")