import os
import json
from datetime import date, timedelta
import requests

API_KEY = os.environ["INTERVALS_API_KEY"]
ATHLETE_ID = os.environ["INTERVALS_ATHLETE_ID"]

GOOGLE_SHEETS_WEBHOOK_URL = os.getenv("GOOGLE_SHEETS_WEBHOOK_URL")
GOOGLE_SHEETS_WEBHOOK_TOKEN = os.getenv("GOOGLE_SHEETS_WEBHOOK_TOKEN")

BASE_URL = "https://intervals.icu/api/v1"

end_date = date.today()
start_date = end_date - timedelta(days=35)

auth = ("API_KEY", API_KEY)

activities_url = (
    f"{BASE_URL}/athlete/{ATHLETE_ID}/activities"
    f"?oldest={start_date.isoformat()}&newest={end_date.isoformat()}"
)

response = requests.get(activities_url, auth=auth, timeout=30)
response.raise_for_status()

activities = response.json()

output = {
    "athlete_id": ATHLETE_ID,
    "generated_date": end_date.isoformat(),
    "period": {
        "from": start_date.isoformat(),
        "to": end_date.isoformat()
    },
    "activities": activities
}

with open("training.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"Exported {len(activities)} activities to training.json")

if GOOGLE_SHEETS_WEBHOOK_URL and GOOGLE_SHEETS_WEBHOOK_TOKEN:
    sheets_payload = {
        "token": GOOGLE_SHEETS_WEBHOOK_TOKEN,
        "activities": activities
    }

    sheets_response = requests.post(
        GOOGLE_SHEETS_WEBHOOK_URL,
        json=sheets_payload,
        timeout=30
    )

    sheets_response.raise_for_status()

    print(
        "Google Sheets update response:",
        sheets_response.text[:200]
    )
else:
    print("Google Sheets webhook secrets not configured")
