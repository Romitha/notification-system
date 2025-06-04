from app.db.simple_db import get_failure_statistics, get_recent_failures, cleanup_old_records
from datetime import datetime, timedelta
import json


def generate_failure_report(days: int = 7):
    """Generate comprehensive failure report"""
    print(f"📊 Generating failure report for the last {days} days...")

    # Get overall statistics
    email_stats = get_failure_statistics(channel="email", days=days)
    sms_stats = get_failure_statistics(channel="sms", days=days)

    # Get recent failures
    recent_email_failures = get_recent_failures(limit=20, channel="email")
    recent_sms_failures = get_recent_failures(limit=20, channel="sms")

    report = {
        "report_generated": datetime.now().isoformat(),
        "period_days": days,
        "statistics": {
            "email": email_stats,
            "sms": sms_stats
        },
        "recent_failures": {
            "email": recent_email_failures,
            "sms": recent_sms_failures
        }
    }

    # Save report to file
    filename = f"failure_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"📁 Failure report saved to: {filename}")
    return report


def perform_maintenance():
    """Perform database maintenance"""
    print("🔧 Performing database maintenance...")

    # Clean up old records
    cleanup_result = cleanup_old_records(days_to_keep=30)

    # Generate maintenance report
    maintenance_report = {
        "maintenance_date": datetime.now().isoformat(),
        "cleanup_result": cleanup_result
    }

    print("✅ Database maintenance completed")
    return maintenance_report