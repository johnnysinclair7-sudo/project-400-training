import os
import json
from datetime import date, timedelta
import requests

API_KEY = os.environ["INTERVALS_API_KEY"]
ATHLETE_ID = os.environ["INTERVALS_ATHLETE_ID"]

GOOGLE_SHEETS_WEBHOOK_URL = os.environ["GOOGLE_SHEETS_WEBHOOK_URL"]
GOOGLE_SHEETS_WEBHOOK_TOKEN = os.environ["GOOGLE_SHEETS_WEBHOOK_TOKEN"]

BASE_URL = "https://intervals.icu/api/v1"
auth = ("API_KEY", API_KEY)

end_date = date.today()

# Keep enough history for coaching context.
start_date = end_date - timedelta(days=35)

def get_json(url):
    response = requests.get(url, auth=auth, timeout=30)
    response.raise_for_status()
    return response.json()

# ------------------------------------------------
# ACTIVITIES
# ------------------------------------------------

activities_url = (
    f"{BASE_URL}/athlete/{ATHLETE_ID}/activities"
    f"?oldest={start_date.isoformat()}&newest={end_date.isoformat()}"
)

activities = get_json(activities_url)

print(f"Found {len(activities)} activities")

# ------------------------------------------------
# ACTIVITY DETAILS / INTERVALS
# ------------------------------------------------

activity_details = []
intervals = []

for activity in activities:

    activity_id = activity.get("id")

    if not activity_id:
        continue

    try:
        detail_url = f"{BASE_URL}/activity/{activity_id}"
        detail = get_json(detail_url)

        activity_details.append(detail)

        activity_intervals = detail.get("intervals") or []

        for i, interval in enumerate(activity_intervals, start=1):

            interval["activity_id"] = activity_id
            interval["activity_date"] = activity.get("start_date_local")
            interval["activity_name"] = activity.get("name")
            interval["interval_number"] = i

            intervals.append(interval)

    except Exception as e:
        print(f"Could not retrieve details for {activity_id}: {e}")

print(f"Found {len(intervals)} intervals")

# ------------------------------------------------
# WELLNESS
# ------------------------------------------------

wellness = []

try:
    wellness_url = (
        f"{BASE_URL}/athlete/{ATHLETE_ID}/wellness"
        f"?oldest={start_date.isoformat()}&newest={end_date.isoformat()}"
    )

    wellness = get_json(wellness_url)

except Exception as e:
    print(f"Could not retrieve wellness: {e}")

print(f"Found {len(wellness)} wellness records")

# ------------------------------------------------
# BUILD COACHING PAYLOAD
# ------------------------------------------------

output = {
    "athlete_id": ATHLETE_ID,
    "generated_date": end_date.isoformat(),
    "period": {
        "from": start_date.isoformat(),
        "to": end_date.isoformat()
    },
    "activities": activities,
    "activity_details": activity_details,
    "intervals": intervals,
    "wellness": wellness
}

# Keep GitHub JSON backup
with open("training.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print("Saved training.json")

# ------------------------------------------------
# SEND TO GOOGLE SHEETS
# ------------------------------------------------

payload = {
    "token": GOOGLE_SHEETS_WEBHOOK_TOKEN,
    "data": output
}

response = requests.post(
    GOOGLE_SHEETS_WEBHOOK_URL,
    json=payload,
    timeout=60
)

response.raise_for_status()

print("Google Sheets response:", response.text[:500])
