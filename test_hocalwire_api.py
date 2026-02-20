"""
Direct test of the Hocalwire API - sends one article and prints the full response.
"""
import os, sys, json, requests
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

api_url = os.getenv('HOCALWIRE_API_URL')
api_key = os.getenv('HOCALWIRE_API_KEY')
session_id = os.getenv('HOCALWIRE_USER_SESSION_ID')

print(f"API URL : {api_url}")
print(f"API Key : {api_key[:20] if api_key else 'MISSING'}...")
print(f"Session : {session_id[:15] if session_id else 'MISSING'}...")
print()

headers = {
    "Content-Type": "application/json",
    "s-id": api_key
}

payload = {
    "heading": "OSI Test Article - AI powered news automation working correctly",
    "mediaIds": "https://www.hocalwire.com/images/logo.png",
    "story": "<p>This is a <strong>test article</strong> uploaded by the OSI News Automation System to verify the Hocalwire API integration is working correctly. The system automatically scrapes, generates, and publishes news articles.</p>",
    "categoryId": 770,
    "location": "India",
    "state": "SUBMITTED",
    "point_long": 78.9629,
    "point_lat": 20.5937,
    "language": "en",
    "sessionId": session_id,
    "news_type": "CITIZEN_FEED",
    "publishedDate": "2026-02-20T10:00:00.000Z"
}

print("Sending test upload to Hocalwire...")
print(f"Payload: {json.dumps({k: str(v)[:50] for k, v in payload.items()}, indent=2)}")
print()

try:
    response = requests.post(api_url, json=payload, headers=headers, timeout=30)
    print(f"HTTP Status: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print()
    try:
        result = response.json()
        print(f"Response JSON: {json.dumps(result, indent=2)}")
    except Exception:
        print(f"Raw Response: {response.text[:500]}")

except Exception as e:
    print(f"ERROR: {e}")
