# test_sms_endpoints.py
import asyncio
import sys
import os
import requests
import json

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.vendors.dialog import DialogSMSClient


async def test_different_endpoints():
    """Test different possible SMS endpoints"""
    print("🧪 Testing Different SMS Endpoints...")
    print("=" * 60)

    # Get token first
    client = DialogSMSClient()
    token = await client._get_access_token()

    # Different possible endpoints based on the documentation
    base_urls = [
        "https://esms.dialog.lk/api/v2",
        "https://e-sms.dialog.lk/api/v2",
        "https://esms.dialog.lk/api",
        "https://e-sms.dialog.lk/api"
    ]

    sms_paths = [
        "/sms",
        "/sms/send",
        "/message",
        "/send"
    ]

    # Test data
    test_data = {
        "msisdn": [{"mobile": "771818404"}],
        "message": "Test SMS from endpoint testing",
        "sourceAddress": "OTRWHEEL",
        "transaction_id": 12345
    }

    print(f"🎯 Test Data: {json.dumps(test_data, indent=2)}")
    print(f"🔑 Token: {token[:30]}...")
    print("-" * 60)

    for base_url in base_urls:
        for sms_path in sms_paths:
            full_url = f"{base_url}{sms_path}"
            print(f"\n🌐 Testing: {full_url}")

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }

            try:
                response = requests.post(
                    full_url,
                    headers=headers,
                    data=json.dumps(test_data),
                    timeout=10
                )

                print(f"📊 Status: {response.status_code}")

                if response.status_code == 200:
                    print(f"✅ SUCCESS! Working endpoint: {full_url}")
                    print(f"📋 Response: {response.text}")
                    return full_url
                elif response.status_code == 401:
                    print(f"❌ 401 Unauthorized")
                elif response.status_code == 404:
                    print(f"❌ 404 Not Found")
                elif response.status_code == 500:
                    print(f"❌ 500 Server Error")
                    print(f"Response: {response.text}")
                else:
                    print(f"❌ {response.status_code}: {response.text}")

            except requests.exceptions.Timeout:
                print(f"⏰ Timeout")
            except requests.exceptions.ConnectionError:
                print(f"🔌 Connection Error")
            except Exception as e:
                print(f"❌ Error: {str(e)}")

    print(f"\n❌ No working endpoint found!")
    return None


async def test_account_info():
    """Test if we can get account information"""
    print("\n🧪 Testing Account Information...")
    print("=" * 60)

    client = DialogSMSClient()
    token = await client._get_access_token()

    # Try to get account info or user data
    info_endpoints = [
        "https://esms.dialog.lk/api/v2/user/profile",
        "https://esms.dialog.lk/api/v2/account/balance",
        "https://esms.dialog.lk/api/v2/user/info",
        "https://e-sms.dialog.lk/api/v2/user/profile"
    ]

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    for endpoint in info_endpoints:
        print(f"\n🌐 Testing: {endpoint}")
        try:
            response = requests.get(endpoint, headers=headers, timeout=10)
            print(f"📊 Status: {response.status_code}")

            if response.status_code == 200:
                print(f"✅ SUCCESS!")
                print(f"📋 Response: {response.text}")
            else:
                print(f"❌ {response.status_code}: {response.text}")

        except Exception as e:
            print(f"❌ Error: {str(e)}")


async def test_get_request_sms():
    """Test SMS via GET request (as mentioned in documentation)"""
    print("\n🧪 Testing SMS via GET Request...")
    print("=" * 60)

    # From the documentation, there's also a GET method for SMS
    # But we need an 'esmsqk' key which is different from the Bearer token

    print("ℹ️ GET request method requires 'esmsqk' key")
    print("This is generated from the Dialog portal, not the API token")
    print("You would need to log into https://e-sms.dialog.lk and generate a URL Message Key")


if __name__ == "__main__":
    async def main():
        print("🚀 Dialog SMS Endpoint Discovery")
        print("=" * 60)

        # Test 1: Try different endpoints
        working_endpoint = await test_different_endpoints()

        # Test 2: Try account info
        await test_account_info()

        # Test 3: Info about GET method
        await test_get_request_sms()

        print("\n" + "=" * 60)
        print("📊 Summary:")
        if working_endpoint:
            print(f"✅ Found working endpoint: {working_endpoint}")
        else:
            print("❌ No working SMS endpoint found via Bearer token")
            print("💡 Possible solutions:")
            print("   1. Your account might not have API SMS access enabled")
            print("   2. You might need to use the GET method with 'esmsqk' key")
            print("   3. The SMS API might be on a different endpoint")
            print("   4. Contact Dialog support to enable SMS API access")


    asyncio.run(main())