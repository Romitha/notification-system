import json
from typing import Dict, Any
import firebase_admin
from firebase_admin import credentials, messaging
from datetime import datetime
from app.config import settings

class FirebaseClient:
    """Client for Firebase services (used for emails and push notifications)"""
    
    def __init__(self):
        # Initialize Firebase Admin SDK
        # In a real app, you would load credentials from a secure location
        if not firebase_admin._apps:
            try:
                cred = credentials.Certificate(
                    json.loads(settings.FIREBASE_API_KEY)
                    if settings.FIREBASE_API_KEY.startswith('{') 
                    else settings.FIREBASE_API_KEY
                )
                firebase_admin.initialize_app(cred)
            except Exception as e:
                print(f"Firebase initialization error: {str(e)}")
                # Initialize in development mode if credentials not available
                firebase_admin.initialize_app()
    
    async def send_push_notification(self, token: str, title: str, body: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send push notification via Firebase Cloud Messaging"""
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=data or {},
                token=token
            )
            
            response = messaging.send(message)
            
            return {
                "success": True,
                "id": response,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Error sending push notification: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def send_email(self, to: str, subject: str, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Send email via Firebase Extensions or similar service
        
        Note: Firebase doesn't have a built-in email service, so this is a placeholder.
        In a real app, you might use Firebase Extensions or a different service.
        """
        try:
            # This is a placeholder - you would integrate with an actual email service
            # For example, you might use Firebase Extensions with Mailchimp or SendGrid
            
            # Simulate success
            return {
                "success": True,
                "id": f"email-{hash(to)}-{hash(subject)}",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }