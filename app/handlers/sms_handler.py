# app/handlers/sms_handler.py
from typing import List, Dict, Any
from app.models.notification import Notification
from app.models.delivery_status import DeliveryStatus
from app.vendors.dialog import DialogSMSClient
from app.config import settings
from app.db.simple_db import save_delivery_status
import uuid
from datetime import datetime


class SMSHandler:
    """Handler for SMS notifications"""

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

            # Process response for each recipient
            if response.get("resultCode") == 0 or response.get("resultCode") == 100:
                for message in response.get("messages", []):
                    server_ref = message.get("serverRef")
                    result_code = message.get("resultCode")
                    success = result_code == 0

                    for recipient in notification.recipients:
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

                        # Save delivery status to database if available
                        try:
                            if self.db:
                                save_delivery_status(status)
                        except Exception as e:
                            print(f"Error saving delivery status: {e}")

                        statuses.append(status)
            else:
                # Handle API-level failure
                for recipient in notification.recipients:
                    status = DeliveryStatus(
                        notification_id=notification_id,
                        recipient=recipient,
                        channel="sms",
                        status="failed",
                        vendor="dialog",
                        vendor_message_id=None,
                        error_message=response.get("resultDesc", "Unknown API error"),
                        timestamp=datetime.now().isoformat()
                    )

                    # Save delivery status
                    try:
                        if self.db:
                            save_delivery_status(status)
                    except Exception as e:
                        print(f"Error saving delivery status: {e}")

                    statuses.append(status)

        except Exception as e:
            # Handle exceptions during API call
            print(f"SMS sending error: {str(e)}")

            for recipient in notification.recipients:
                status = DeliveryStatus(
                    notification_id=notification_id,
                    recipient=recipient,
                    channel="sms",
                    status="failed",
                    vendor="dialog",
                    vendor_message_id=None,
                    error_message=str(e),
                    timestamp=datetime.now().isoformat()
                )

                # Save delivery status
                try:
                    if self.db:
                        save_delivery_status(status)
                except Exception as save_err:
                    print(f"Error saving delivery status: {save_err}")

                statuses.append(status)

        return statuses