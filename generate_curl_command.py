# generate_curl_command.py
import asyncio
import sys
import os
import json

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.vendors.dialog import DialogSMSClient


async def generate_curl_command():
    """Generate curl command for testing Dialog SMS API"""
    print("🔧 Generating cURL Command for Dialog SMS API")
    print("=" * 60)

    try:
        # Get fresh token
        client = DialogSMSClient()
        token = await client._get_access_token()

        print(f"✅ Token obtained: {token[:30]}...")

        # Generate the curl command
        curl_command = f'''curl --location --request POST 'https://e-sms.dialog.lk/api/v2/sms' \\
--header 'Authorization: Bearer {token}' \\
--header 'Content-Type: application/json' \\
--data-raw '{{
    "sourceAddress": "OTRWHEEL",
    "message": "Test message from OTR Wheel SMS API! 🚗",
    "transaction_id": {int(asyncio.get_event_loop().time() * 1000)},
    "payment_method": 0,
    "msisdn": [
        {{
            "mobile": "771818404"
        }}
    ]
}}'
'''

        print("\n📋 Complete cURL Command:")
        print("-" * 40)
        print(curl_command)
        print("-" * 40)

        # Also generate alternative endpoints to test
        alternative_commands = []

        # Alternative 1: Different endpoint
        alt1 = f'''curl --location --request POST 'https://esms.dialog.lk/api/v2/sms' \\
--header 'Authorization: Bearer {token}' \\
--header 'Content-Type: application/json' \\
--data-raw '{{
    "sourceAddress": "OTRWHEEL",
    "message": "Test via esms endpoint",
    "transaction_id": {int(asyncio.get_event_loop().time() * 1000) + 1},
    "msisdn": [
        {{
            "mobile": "771818404"
        }}
    ]
}}'
'''

        # Alternative 2: Without payment_method
        alt2 = f'''curl --location --request POST 'https://e-sms.dialog.lk/api/v2/sms' \\
--header 'Authorization: Bearer {token}' \\
--header 'Content-Type: application/json' \\
--data-raw '{{
    "sourceAddress": "OTRWHEEL",
    "message": "Test without payment method",
    "transaction_id": {int(asyncio.get_event_loop().time() * 1000) + 2},
    "msisdn": [
        {{
            "mobile": "771818404"
        }}
    ]
}}'
'''

        print("\n🔄 Alternative Commands to Try:")
        print("\n1️⃣ Try esms.dialog.lk endpoint:")
        print("-" * 40)
        print(alt1)
        print("-" * 40)

        print("\n2️⃣ Try without payment_method:")
        print("-" * 40)
        print(alt2)
        print("-" * 40)

        # Save commands to file
        with open("sms_curl_commands.txt", "w") as f:
            f.write("Dialog SMS API cURL Commands\\n")
            f.write("=" * 50 + "\\n\\n")
            f.write("Main Command:\\n")
            f.write(curl_command + "\\n\\n")
            f.write("Alternative 1 (esms endpoint):\\n")
            f.write(alt1 + "\\n\\n")
            f.write("Alternative 2 (no payment_method):\\n")
            f.write(alt2 + "\\n\\n")

        print(f"\\n💾 Commands saved to: sms_curl_commands.txt")

        # Generate simple test versions
        print("\\n🧪 Quick Test Commands:")
        print("\\nCopy and paste these one by one:\\n")

        simple_commands = [
            f"curl -X POST 'https://e-sms.dialog.lk/api/v2/sms' -H 'Authorization: Bearer {token}' -H 'Content-Type: application/json' -d '{{\"sourceAddress\":\"OTRWHEEL\",\"message\":\"Quick test 1\",\"transaction_id\":{int(asyncio.get_event_loop().time() * 1000)},\"msisdn\":[{{\"mobile\":\"771818404\"}}]}}'",

            f"curl -X POST 'https://esms.dialog.lk/api/v2/sms' -H 'Authorization: Bearer {token}' -H 'Content-Type: application/json' -d '{{\"sourceAddress\":\"OTRWHEEL\",\"message\":\"Quick test 2\",\"transaction_id\":{int(asyncio.get_event_loop().time() * 1000) + 1},\"msisdn\":[{{\"mobile\":\"771818404\"}}]}}'",
        ]

        for i, cmd in enumerate(simple_commands, 1):
            print(f"{i}. {cmd}\\n")

        return token

    except Exception as e:
        print(f"❌ Error generating curl command: {str(e)}")
        return None


async def test_token_validity():
    """Test if the token works for other endpoints"""
    print("\\n🧪 Testing Token Validity on Other Endpoints")
    print("=" * 60)

    try:
        client = DialogSMSClient()
        token = await client._get_access_token()

        # Test endpoints that might work
        test_endpoints = [
            "https://esms.dialog.lk/api/v2/user/profile",
            "https://e-sms.dialog.lk/api/v2/user/profile",
            "https://esms.dialog.lk/api/v2/account/balance",
        ]

        for endpoint in test_endpoints:
            curl_cmd = f"curl -X GET '{endpoint}' -H 'Authorization: Bearer {token}'"
            print(f"\\nTest: {curl_cmd}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    async def main():
        token = await generate_curl_command()
        if token:
            await test_token_validity()

            print("\\n" + "=" * 60)
            print("📝 Instructions:")
            print("1. Copy one of the curl commands above")
            print("2. Paste it in your terminal/command prompt")
            print("3. Press Enter to execute")
            print("4. Check the response")
            print("5. Try different endpoints if first one fails")
            print("\\n💡 If all fail with 401, your account might need SMS API access enabled")


    asyncio.run(main())