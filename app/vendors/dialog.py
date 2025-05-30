# app/vendors/dialog.py
import json
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.config import settings


class DialogSMSClient:
    """Client for Dialog E-SMS API v2"""

    def __init__(self):
        self.api_base_url = settings.DIALOG_API_BASE_URL or "https://esms.dialog.lk/api/v2"
        self.api_username = settings.DIALOG_API_USERNAME or "Otrwheel"
        self.api_password = settings.DIALOG_API_PASSWORD or "OtRR||-->>2025"
        self.default_mask = settings.DIALOG_DEFAULT_MASK or "OTRWHEEL"
        self._access_token = None
        self._token_expiry = None

    async def _get_access_token(self) -> str:
        """Get or refresh access token"""
        print(f"🔑 Checking Dialog API token...")

        # Check if we have a valid token
        if self._access_token and self._token_expiry:
            current_time = datetime.now().timestamp()
            # If token expires in less than 5 minutes, refresh it
            if current_time < (self._token_expiry - 300):
                print(f"✅ Using cached token (expires in {int((self._token_expiry - current_time) / 60)} minutes)")
                return self._access_token
            else:
                print(f"⏰ Token expiring soon, refreshing...")

        # Get new token
        login_url = f"{self.api_base_url}/user/login"
        login_data = {
            "username": self.api_username,
            "password": self.api_password
        }

        print(f"📡 Requesting token from: {login_url}")
        print(f"🔐 Username: {self.api_username}")
        print(f"🔐 Password: {'*' * len(self.api_password) if self.api_password else 'NOT SET'}")

        try:
            response = requests.post(
                login_url,
                headers={'Content-Type': 'application/json'},
                data=json.dumps(login_data),
                timeout=30
            )

            print(f"📊 Response Status: {response.status_code}")

            if response.status_code != 200:
                print(f"❌ HTTP Error {response.status_code}: {response.text}")
                response.raise_for_status()

            result = response.json()
            print(f"📋 API Response: {json.dumps(result, indent=2)}")

            if result.get("status") == "success":
                self._access_token = result.get("token")
                # Token expires in seconds, convert to timestamp
                expiration_seconds = result.get("expiration", 43200)  # Default 12 hours
                self._token_expiry = datetime.now().timestamp() + expiration_seconds

                print(f"✅ Dialog API token obtained successfully")
                print(f"🕒 Token expires in {expiration_seconds} seconds ({expiration_seconds / 3600:.1f} hours)")
                print(f"🎫 Token preview: {self._access_token[:30]}...")
                return self._access_token
            else:
                error_msg = result.get("comment", "Unknown error")
                error_code = result.get("errCode", "N/A")
                remaining_count = result.get("remainingCount", "N/A")

                print(f"❌ Dialog API login failed:")
                print(f"   Error: {error_msg}")
                print(f"   Error Code: {error_code}")
                print(f"   Remaining Login Attempts: {remaining_count}")

                raise Exception(f"Dialog API login failed: {error_msg} (Code: {error_code})")

        except requests.exceptions.Timeout:
            error_msg = f"Request timeout after 30 seconds"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
        except requests.exceptions.ConnectionError:
            error_msg = f"Connection error - cannot reach {login_url}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Dialog API request error: {str(e)}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
        except json.JSONDecodeError:
            error_msg = f"Invalid JSON response from Dialog API"
            print(f"❌ {error_msg}")
            print(f"Raw response: {response.text}")
            raise Exception(error_msg)

    async def send_sms(self, to_numbers: List[str], message: str,
                       mask: Optional[str] = None,
                       campaign_name: Optional[str] = None,
                       client_ref: Optional[str] = None,
                       scheduled_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Send SMS to one or more recipients using Dialog E-SMS API v2

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
        # Get access token
        token = await self._get_access_token()

        # Use provided values or defaults
        mask = mask or self.default_mask
        campaign_name = campaign_name or "notification_system"

        # Generate unique transaction ID and client reference
        timestamp = int(datetime.now().timestamp() * 1000)  # milliseconds
        transaction_id = timestamp
        client_ref = client_ref or f"notif-{timestamp}"

        # Format phone numbers for Dialog API (remove country code if present)
        formatted_numbers = []
        for number in to_numbers:
            # Remove any non-digits
            clean_number = ''.join(filter(str.isdigit, number))

            # Handle different formats
            if clean_number.startswith('94'):
                # Remove country code 94
                clean_number = clean_number[2:]
            elif clean_number.startswith('0'):
                # Remove leading zero
                clean_number = clean_number[1:]

            # Ensure it's 9 digits (Sri Lankan mobile format)
            if len(clean_number) == 9 and clean_number.startswith('7'):
                formatted_numbers.append({"mobile": clean_number})
            else:
                print(f"⚠️ Invalid phone number format: {number}")

        if not formatted_numbers:
            return {
                "resultCode": 1,
                "resultDesc": "No valid phone numbers provided",
                "messages": []
            }

        # Create request body according to Dialog API v2 format
        request_data = {
            "msisdn": formatted_numbers,
            "message": message,
            "sourceAddress": mask,
            "transaction_id": transaction_id
        }

        # Add scheduled time if provided
        if scheduled_time:
            # Note: Check if Dialog API supports scheduled SMS in v2
            pass

        # Make API request
        # sms_url = f"{self.api_base_url}/sms" # https://e-sms.dialog.lk /api/v2/sms
        sms_url = "https://e-sms.dialog.lk/api/v2/sms"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }

        try:
            print(f"📤 Sending SMS to {len(formatted_numbers)} recipients via Dialog API")
            print(f"🌐 SMS URL: {sms_url}")
            print(f"📋 Request Headers: {headers}")
            print(f"📦 Request Data: {json.dumps(request_data, indent=2)}")

            response = requests.post(
                sms_url,
                headers=headers,
                data=json.dumps(request_data),
                timeout=30
            )

            print(f"📊 SMS Response Status: {response.status_code}")
            print(f"📋 SMS Response Headers: {dict(response.headers)}")
            print(f"📄 SMS Response Body: {response.text}")

            if response.status_code == 401:
                print("❌ 401 Unauthorized - Possible issues:")
                print("   1. Token might be invalid for SMS endpoint")
                print("   2. Account might not have SMS API access")
                print("   3. SMS endpoint URL might be wrong")
                print("   4. Bearer token format might be incorrect")

            response.raise_for_status()
            result = response.json()

            # Convert Dialog API response to our expected format
            if result.get("status") == "success":
                # Extract campaign info
                data = result.get("data", {})
                campaign_id = data.get("campaignId")

                return {
                    "resultCode": 0,
                    "resultDesc": "SMS sent successfully",
                    "messages": [{
                        "serverRef": str(campaign_id) if campaign_id else client_ref,
                        "resultCode": 0,
                        "resultDesc": "Success"
                    }],
                    "campaignId": campaign_id,
                    "transaction_id": transaction_id
                }
            else:
                error_msg = result.get("comment", "Unknown error")
                error_code = result.get("errCode", "999")
                return {
                    "resultCode": 1,
                    "resultDesc": f"Dialog API error ({error_code}): {error_msg}",
                    "messages": [{
                        "serverRef": None,
                        "resultCode": 1,
                        "resultDesc": error_msg
                    }]
                }

        except requests.exceptions.RequestException as e:
            print(f"❌ Dialog SMS API request failed: {str(e)}")
            return {
                "resultCode": 1,
                "resultDesc": f"API request failed: {str(e)}",
                "messages": [{
                    "serverRef": None,
                    "resultCode": 1,
                    "resultDesc": str(e)
                }]
            }
        except Exception as e:
            print(f"❌ Unexpected error in Dialog SMS: {str(e)}")
            return {
                "resultCode": 1,
                "resultDesc": f"Unexpected error: {str(e)}",
                "messages": [{
                    "serverRef": None,
                    "resultCode": 1,
                    "resultDesc": str(e)
                }]
            }

    async def send_sms_to_list(self, list_names: List[str], message: str,
                               mask: Optional[str] = None,
                               campaign_name: Optional[str] = None,
                               client_ref: Optional[str] = None,
                               scheduled_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Send SMS to predefined list(s) using Dialog API

        Note: This method would need to be implemented based on Dialog's
        list functionality if available in their API v2
        """
        # This is a placeholder - Dialog E-SMS API v2 documentation
        # doesn't show list-based sending in the provided docs
        return {
            "resultCode": 1,
            "resultDesc": "List-based SMS sending not implemented for Dialog API v2",
            "messages": []
        }

    async def check_campaign_status(self, transaction_id: str) -> Dict[str, Any]:
        """Check the status of a campaign using transaction ID"""
        try:
            token = await self._get_access_token()

            check_url = f"{self.api_base_url}/sms/check-transaction"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }

            request_data = {
                "transaction_id": int(transaction_id)
            }

            response = requests.post(
                check_url,
                headers=headers,
                data=json.dumps(request_data)
            )

            response.raise_for_status()
            result = response.json()

            return result

        except Exception as e:
            print(f"❌ Error checking campaign status: {str(e)}")
            return {
                "status": "failed",
                "comment": str(e),
                "data": {}
            }