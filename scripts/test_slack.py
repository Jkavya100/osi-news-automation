#!/usr/bin/env python3
"""
Test Slack webhook integration
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
import requests

load_dotenv()

webhook_url = os.getenv('SLACK_WEBHOOK_URL')

if not webhook_url:
    print("❌ No SLACK_WEBHOOK_URL found in .env")
    sys.exit(1)

print(f"✅ Webhook URL found: {webhook_url[:50]}...")

# Send test message
payload = {
    "text": "🎉 *OSI News Automation - Slack Integration Test*\n\nThis is a test message from your monitoring system.\n\n✅ Slack webhook is working correctly!",
    "username": "OSI Monitor",
    "icon_emoji": ":robot_face:"
}

try:
    response = requests.post(webhook_url, json=payload, timeout=10)
    response.raise_for_status()
    print("✅ Test message sent to Slack successfully!")
    print("\nCheck your Slack channel for the message.")
except Exception as e:
    print(f"❌ Failed to send message: {e}")
    sys.exit(1)
