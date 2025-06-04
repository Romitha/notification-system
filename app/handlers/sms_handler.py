# app/handlers/sms_handler.py
# CORRECTED VERSION - Ensures correct channel is always used

from typing import List, Dict, Any
from app.models.notification import Notification
from app.models.delivery_status import DeliveryStatus
from app.vendors.dialog import DialogSMSClient
from app.config import settings
from app.db.simple_db import save_delivery_status
import uuid
from datetime import datetime


class SMSHandler:
    """Handler for SMS notifications - FIXED to always use 'sms' channel"""

    def __init__(self, db=None):
        self.dialog_client = DialogSMSClient()
        self.db = db

    async def send(self, notification: Notification) -> List[DeliveryStatus]:
        """Send SMS notifications to recipients"""
        statuses = []

        # Use a fallback ID if notification.id is None
        notification_id = notification.id or f"temp-{uuid.uuid4()}"

        # Get SMS content
        sms_content = notification.content

        # Get mask (sender ID) from metadata or use default
        mask = notification.metadata.get("mask") if notification.metadata else None
        mask = mask or settings.DIALOG_DEFAULT_MASK

        # Get campaign name from metadata or use default
        campaign_name = notification.metadata.get("campaign_name") if notification.metadata else None
        campaign_name = campaign_name or "notification_system"

        # Get client reference from metadata or generate one
        client_ref = notification.metadata.get("client_ref") if notification.metadata else None
        client_ref = client_ref or f"notif-{notification_id[:8]}"

        print(f"📱 SMS Handler: Processing {len(notification.recipients)} recipients")
        print(f"🏷️ Using mask: {mask}")
        print(f"📋 Campaign: {campaign_name}")

        try:
            # Call Dialog API to send SMS
            response = await self.dialog_client.send_sms(
                to_numbers=notification.recipients,
                message=sms_content,
                mask=mask,
                campaign_name=campaign_name,
                client_ref=client_ref,
                scheduled_time=notification.scheduled_time
            )

            print(f"📊 Dialog API Response: {response}")

            # Process response for each recipient
            if response.get("resultCode") == 0 or response.get("resultCode") == 100:
                print("✅ Dialog API returned success code")

                # Handle successful API response
                messages = response.get("messages", [])
                if messages:
                    # Process each message in response
                    for i, message in enumerate(messages):
                        server_ref = message.get("serverRef")
                        result_code = message.get("resultCode")
                        success = result_code == 0

                        # Get corresponding recipient (if available)
                        recipient = notification.recipients[i] if i < len(notification.recipients) else \
                        notification.recipients[0]

                        # Create delivery status
                        status = DeliveryStatus(
                            notification_id=notification_id,
                            recipient=recipient,
                            channel="sms",
                            status="delivered" if success else "failed",
                            vendor="dialog",
                            vendor_message_id=server_ref,
                            error_message=None if success else message.get("resultDesc"),
                            timestamp=datetime.now().isoformat()
                        )

                        print(f"📤 SMS Status for {recipient}: {status.status}")
                        statuses.append(status)
                else:
                    # No specific message responses, create status for all recipients
                    server_ref = response.get("campaignId") or response.get("transaction_id")

                    for recipient in notification.recipients:
                        status = DeliveryStatus(
                            notification_id=notification_id,
                            recipient=recipient,
                            channel="sms",
                            status="delivered",  # API success means delivered
                            vendor="dialog",
                            vendor_message_id=str(server_ref) if server_ref else None,
                            error_message=None,
                            timestamp=datetime.now().isoformat()
                        )

                        print(f"📤 SMS Status for {recipient}: delivered")
                        statuses.append(status)

            else:
                # Handle API-level failure
                error_desc = response.get("resultDesc", "Unknown API error")
                print(f"❌ Dialog API error: {error_desc}")

                for recipient in notification.recipients:
                    status = DeliveryStatus(
                        notification_id=notification_id,
                        recipient=recipient,
                        channel="sms",
                        status="failed",
                        vendor="dialog",
                        vendor_message_id=None,
                        error_message=error_desc,
                        timestamp=datetime.now().isoformat()
                    )

                    print(f"📤 SMS Status for {recipient}: failed - {error_desc}")
                    statuses.append(status)

        except Exception as e:
            # Handle exceptions during API call
            error_message = str(e)
            print(f"❌ SMS sending exception: {error_message}")

            for recipient in notification.recipients:
                status = DeliveryStatus(
                    notification_id=notification_id,
                    recipient=recipient,
                    channel="sms",
                    status="failed",
                    vendor="dialog",
                    vendor_message_id=None,
                    error_message=error_message,
                    timestamp=datetime.now().isoformat()
                )

                print(f"📤 SMS Status for {recipient}: failed - {error_message}")
                statuses.append(status)

        # 💾 Save all delivery statuses to database
        print(f"💾 Saving {len(statuses)} SMS delivery statuses to database...")
        for status in statuses:
            try:
                save_delivery_status(status)
                print(f"✅ Saved SMS delivery status for {status.recipient}: {status.status}")
            except Exception as save_err:
                print(f"❌ Error saving SMS delivery status for {status.recipient}: {save_err}")

        # 📊 Summary
        success_count = sum(1 for s in statuses if s.status == "delivered")
        failed_count = len(statuses) - success_count
        print(f"📊 SMS Handler Summary: {success_count} delivered, {failed_count} failed")

        return statuses