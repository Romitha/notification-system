# test_sms_send.py
import asyncio
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.vendors.dialog import DialogSMSClient
from app.config import settings


async def test_sms_send():
    """Test sending SMS via Dialog API"""
    print("📱 Testing Dialog SMS Sending...")
    print("=" * 50)

    # Your mobile number
    test_number = "0771818404"
    test_message = "Hello! This is a test SMS from OTR Wheel notification system. 🚗"

    print(f"📞 Sending to: {test_number}")
    print(f"💬 Message: {test_message}")
    print(f"🏷️ Mask: OTRWHEEL")
    print("-" * 30)

    try:
        # Create Dialog client
        client = DialogSMSClient()

        # Send SMS
        print("📡 Sending SMS via Dialog API...")
        response = await client.send_sms(
            to_numbers=[test_number],
            message=test_message,
            mask="OTRWHEEL",
            campaign_name="test_sms",
            client_ref="test_001"
        )

        print(f"📋 SMS Response: {response}")

        # Check response
        if response.get("resultCode") == 0:
            print("✅ SMS sent successfully!")

            # Extract campaign info
            campaign_id = response.get("campaignId")
            transaction_id = response.get("transaction_id")

            print(f"🆔 Campaign ID: {campaign_id}")
            print(f"🔢 Transaction ID: {transaction_id}")

            # Test campaign status check if we have transaction_id
            if transaction_id:
                print(f"\n🔍 Checking campaign status...")
                status_response = await client.check_campaign_status(str(transaction_id))
                print(f"📊 Status Response: {status_response}")

            return True
        else:
            print(f"❌ SMS sending failed!")
            print(f"Error: {response.get('resultDesc', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"❌ SMS test failed: {str(e)}")
        return False


async def test_multiple_numbers():
    """Test sending SMS to multiple numbers"""
    print("\n📱 Testing Multiple SMS Sending...")
    print("=" * 50)

    # Test with multiple numbers (add more if you want)
    test_numbers = ["0771818404"]  # Add more numbers here if needed
    test_message = "Bulk SMS test from OTR Wheel! 📢"

    print(f"📞 Sending to {len(test_numbers)} numbers: {test_numbers}")
    print(f"💬 Message: {test_message}")
    print("-" * 30)

    try:
        client = DialogSMSClient()

        response = await client.send_sms(
            to_numbers=test_numbers,
            message=test_message,
            mask="OTRWHEEL",
            campaign_name="bulk_test"
        )

        print(f"📋 Bulk SMS Response: {response}")

        if response.get("resultCode") == 0:
            print("✅ Bulk SMS sent successfully!")
            return True
        else:
            print(f"❌ Bulk SMS failed: {response.get('resultDesc')}")
            return False

    except Exception as e:
        print(f"❌ Bulk SMS test failed: {str(e)}")
        return False


async def test_phone_number_formats():
    """Test different phone number formats"""
    print("\n📱 Testing Phone Number Formats...")
    print("=" * 50)

    # Different formats of your number
    formats = [
        "0771818404",  # Local format
        "771818404",  # Without leading zero
        "94771818404",  # International format
        "+94771818404"  # With plus sign
    ]

    client = DialogSMSClient()

    for i, number in enumerate(formats):
        print(f"\n🧪 Test {i + 1}: {number}")
        try:
            response = await client.send_sms(
                to_numbers=[number],
                message=f"Format test {i + 1}: {number}",
                mask="OTRWHEEL",
                campaign_name=f"format_test_{i + 1}"
            )

            if response.get("resultCode") == 0:
                print(f"✅ Format {number} works!")
            else:
                print(f"❌ Format {number} failed: {response.get('resultDesc')}")

        except Exception as e:
            print(f"❌ Format {number} error: {str(e)}")


if __name__ == "__main__":
    async def main():
        print("🚀 Dialog SMS Testing Suite")
        print("=" * 50)

        # Test 1: Single SMS
        success1 = await test_sms_send()

        # Test 2: Multiple SMS (if first test passed)
        success2 = False
        if success1:
            success2 = await test_multiple_numbers()

        # Test 3: Phone number formats
        await test_phone_number_formats()

        print("\n" + "=" * 50)
        print("📊 SMS Test Summary:")
        print(f"Single SMS: {'✅ PASS' if success1 else '❌ FAIL'}")
        print(f"Multiple SMS: {'✅ PASS' if success2 else '❌ FAIL'}")

        if success1:
            print(f"\n🎉 SMS functionality is working!")
            print(f"📱 Check your phone ({test_number}) for test messages!")
        else:
            print(f"\n⚠️ SMS sending failed. Check the error messages above.")


    # Update test_number in the global scope
    test_number = "0771818404"
    asyncio.run(main())