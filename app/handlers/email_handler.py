from typing import List, Dict, Any
from app.models.notification import Notification
from app.models.delivery_status import DeliveryStatus
from app.vendors.firebase import FirebaseClient

class EmailHandler:
    """Handler for email notifications"""
    
    def __init__(self):
        self.firebase_client = FirebaseClient()
    
    async def send(self, notification: Notification) -> List[DeliveryStatus]:
        """Send email notifications to recipients"""
        statuses = []
        
        # Get email template content
        email_content = await self._prepare_email_content(notification)
        
        # Send to each recipient
        for recipient in notification.recipients:
            try:
                # Use Firebase or another vendor for email delivery
                result = await self.firebase_client.send_email(
                    to=recipient,
                    subject=notification.title,
                    content=email_content,
                    metadata=notification.metadata
                )
                
                # Record delivery status
                status = DeliveryStatus(
                    notification_id=notification.id,
                    recipient=recipient,
                    channel="email",
                    status="delivered" if result.get("success") else "failed",
                    vendor="firebase",
                    vendor_message_id=result.get("id"),
                    timestamp=result.get("timestamp")
                )
                statuses.append(status)
                
            except Exception as e:
                # Handle failure
                status = DeliveryStatus(
                    notification_id=notification.id,
                    recipient=recipient,
                    channel="email",
                    status="failed",
                    vendor="firebase",
                    error_message=str(e)
                )
                statuses.append(status)
        
        return statuses
    
    async def _prepare_email_content(self, notification: Notification) -> str:
        """Prepare email content with template if specified"""
        # Logic to fetch and apply template
        # For now, just return the content
        return notification.content