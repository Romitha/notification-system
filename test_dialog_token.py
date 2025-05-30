# test_dialog_token.py
import asyncio
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.vendors.dialog import DialogSMSClient
from app.config import settings


async def test_dialog_token():
    """Test Dialog SMS API token generation"""
    print("🧪 Testing Dialog SMS API Token Generation...")
    print(f"API Base URL: {settings.DIALOG_API_BASE_URL}")
    print(f"Username: {settings.DIALOG_API_USERNAME}")
    print(f"Password: {'*' * len(settings.DIALOG_API_PASSWORD) if settings.DIALOG_API_PASSWORD else 'Not Set'}")
    print("-" * 50)

    try:
        # Create Dialog client
        client = DialogSMSClient()

        # Test token generation
        print("📡 Attempting to get access token...")
        token = await client._get_access_token()

        if token:
            print("✅ Token generation successful!")
            print(f"Token preview: {token[:20]}...{token[-10:] if len(token) > 30 else token}")
            print(f"Token length: {len(token)} characters")

            # Test token refresh (should use cached token)
            print("\n🔄 Testing token caching...")
            token2 = await client._get_access_token()

            if token == token2:
                print("✅ Token caching working correctly")
            else:
                print("⚠️ Token caching might not be working")

            return True
        else:
            print("❌ Token generation failed - No token returned")
            return False

    except Exception as e:
        print(f"❌ Token generation failed: {str(e)}")
        return False


async def test_dialog_login_direct():
    """Test Dialog login API directly"""
    import requests
    import json

    print("\n🧪 Testing Direct Dialog Login API...")

    login_url = f"{settings.DIALOG_API_BASE_URL or 'https://esms.dialog.lk/api/v2'}/user/login"
    login_data = {
        "username": settings.DIALOG_API_USERNAME or "Otrwheel",
        "password": settings.DIALOG_API_PASSWORD or "OtRR||-->>2025"
    }

    print(f"Login URL: {login_url}")
    print(f"Request Data: {json.dumps(login_data, indent=2)}")
    print("-" * 30)

    try:
        response = requests.post(
            login_url,
            headers={'Content-Type': 'application/json'},
            data=json.dumps(login_data),
            timeout=30
        )

        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")

        if response.status_code == 200:
            result = response.json()
            print(f"Response Body: {json.dumps(result, indent=2)}")

            if result.get("status") == "success":
                print("✅ Direct API login successful!")
                return True
            else:
                print(f"❌ API returned error: {result.get('comment', 'Unknown error')}")
                print(f"Error Code: {result.get('errCode', 'N/A')}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print("❌ Request timeout - API might be slow or unreachable")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - Check internet connection or API URL")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False


if __name__ == "__main__":
    async def main():
        print("🚀 Dialog SMS API Token Test")
        print("=" * 50)

        # Test 1: Direct API call
        success1 = await test_dialog_login_direct()

        # Test 2: Via DialogSMSClient
        success2 = await test_dialog_token()

        print("\n" + "=" * 50)
        print("📊 Test Summary:")
        print(f"Direct API Login: {'✅ PASS' if success1 else '❌ FAIL'}")
        print(f"DialogSMSClient: {'✅ PASS' if success2 else '❌ FAIL'}")

        if success1 and success2:
            print("\n🎉 All tests passed! Dialog API integration is working.")
        else:
            print("\n⚠️ Some tests failed. Check the error messages above.")


    asyncio.run(main())