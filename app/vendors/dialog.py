# app/vendors/dialog.py
import json
import requests
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.config import settings


class DialogSMSClient:
    """Client for Dialog RichCommunication SMS API"""

    def __init__(self):
        self.api_base_url = settings.DIALOG_API_BASE_URL
        self.api_username = settings.DIALOG_API_USERNAME
        self.api_password = settings.DIALOG_API_PASSWORD
        self.default_mask = settings.DIALOG_DEFAULT_MASK

    async def send_sms(self, to_numbers: List[str], message: str,
                       mask: Optional[str] = None,
                       campaign_name: Optional[str] = None,
                       client_ref: Optional[str] = None,
                       scheduled_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Send SMS to one or more recipients using Dialog API

        Args:
            to_numbers: List of recipient phone numbers in format '947xxxxxxxx'
            message: SMS content
            mask: SMS source ID (sender ID)
            campaign_name: Campaign name for reporting
            client_ref: Client reference ID
            scheduled_time: Optional scheduled time for the SMS

        Returns:
            API response as dictionary
        """
        mask = mask or self.default_mask
        campaign_name = campaign_name or "notification_system"
        client_ref = client_ref or f"msg-{datetime.now().timestamp()}"

        # Create request body
        numbers = ",".join(to_numbers)

        request_data = {
            "messages": [
                {
                    "clientRef": client_ref,
                    "number": numbers,
                    "mask": mask,
                    "text": message,
                    "campaignName": campaign_name
                }
            ]
        }

        # Add scheduled time if provided
        if scheduled_time:
            request_data["messages"][0]["scheduledTime"] = scheduled_time.strftime("%Y-%m-%dT%H:%M:%S")

        # Generate security headers
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        digest = hashlib.md5(self.api_password.encode()).hexdigest() #need to request from Malith
        digest = "10a8d9b88435c6d3ad6207913af53422"

        headers = {
            "Content-Type": "application/json",
            "USER": self.api_username,
            "DIGEST": digest,
            "CREATED": now
        }

        # Make API request
        response = requests.post(
            f"{self.api_base_url}/sms/send",
            headers=headers,
            data=json.dumps(request_data)
        )

        # Parse and return response
        response_data = response.json()
        return response_data

    async def send_sms_to_list(self, list_names: List[str], message: str,
                               mask: Optional[str] = None,
                               campaign_name: Optional[str] = None,
                               client_ref: Optional[str] = None,
                               scheduled_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Send SMS to predefined list(s) using Dialog API

        Args:
            list_names: List of predefined recipient list names
            message: SMS content
            mask: SMS source ID (sender ID)
            campaign_name: Campaign name for reporting
            client_ref: Client reference ID
            scheduled_time: Optional scheduled time for the SMS

        Returns:
            API response as dictionary
        """
        mask = mask or self.default_mask
        campaign_name = campaign_name or "notification_system"
        client_ref = client_ref or f"list-{datetime.now().timestamp()}"

        # Create request body
        lists = ",".join(list_names)

        request_data = {
            "messages": [
                {
                    "clientRef": client_ref,
                    "list": lists,
                    "mask": mask,
                    "text": message,
                    "campaignName": campaign_name
                }
            ]
        }

        # Add scheduled time if provided
        if scheduled_time:
            request_data["messages"][0]["scheduledTime"] = scheduled_time.strftime("%Y-%m-%dT%H:%M:%S")

        # Generate security headers
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        digest = hashlib.md5(self.api_password.encode()).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "USER": self.api_username,
            "DIGEST": digest,
            "CREATED": now
        }

        # Make API request
        response = requests.post(
            f"{self.api_base_url}/sms/send",
            headers=headers,
            data=json.dumps(request_data)
        )

        # Parse and return response
        response_data = response.json()
        return response_data