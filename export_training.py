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
start_date = end_date - timedelta(days=35)


def get_json(url):
    response = requests.get(
        url,
        auth=auth,
        timeout=30
    )
    response.raise_for_status()
    return response.json()


# ============================================================
# ACTIVITIES
# ============================================================

activities_url = (
    f"{BASE_URL}/athlete/{ATHLETE_ID}/activities"
    f"?oldest={start_date.isoformat()}"
    f"&newest={end_date.isoformat()}"
)

activities = get_json(activities_url)

print(f"Found {len(activities)} activities")


# ============================================================
# ACTIVITY DETAILS
# ============================================================

activity_details = []

for activity in activities:

    activity_id = activity.get("id")

    if not activity_id:
        continue

    # Strava-only placeholder activities cannot always be
    # retrieved through the Intervals API.
    if not str(activity_id).startswith("i"):
        continue

    try:

        detail_url = f"{BASE_URL}/activity/{activity_id}"

        detail = get_json(detail_url)

        activity_details.append(detail)

    except Exception as e:

        print(
            f"Could not retrieve details for "
            f"{activity_id}: {e}"
        )


print(
    f"Retrieved details for "
    f"{len(activity_details)} activities"
)


# ============================================================
# MERGE ACTIVITY DETAILS
# ============================================================

# The activity-list response is useful for chronology.
# The detail response contains richer fields such as:
# average_watts
# icu_weighted_avg_watts
# icu_joules
# decoupling
# icu_power_hr_z2
# icu_cadence_z2
# icu_rpe
# feel

detail_by_id = {
    str(a.get("id")): a
    for a in activity_details
    if a.get("id")
}

merged_activities = []

for activity in activities:

    activity_id = str(activity.get("id"))

    detail = detail_by_id.get(activity_id)

    if detail:

        merged = dict(activity)
        merged.update(detail)

        merged_activities.append(merged)

    else:

        merged_activities.append(activity)


# ============================================================
# WELLNESS
# ============================================================

wellness = []

try:

    wellness_url = (
        f"{BASE_URL}/athlete/{ATHLETE_ID}/wellness"
        f"?oldest={start_date.isoformat()}"
        f"&newest={end_date.isoformat()}"
    )

    wellness = get_json(wellness_url)

except Exception as e:

    print(f"Could not retrieve wellness: {e}")


print(f"Found {len(wellness)} wellness records")


# ============================================================
# INTERVALS
# ============================================================

# Temporarily left empty.
#
# Our previous assumption that activity detail contained
# detail["intervals"] was incorrect.
#
# The next upgrade will explicitly retrieve and parse the
# Intervals.icu activity/FIT data rather than silently creating
# incorrect interval rows.

intervals = []


# ============================================================
# BUILD OUTPUT
# ============================================================

output = {

    "athlete_id": ATHLETE_ID,

    "generated_date": end_date.isoformat(),

    "period": {
        "from": start_date.isoformat(),
        "to": end_date.isoformat()
    },

    "activities": merged_activities,

    "activity_details": activity_details,

    "intervals": intervals,

    "wellness": wellness
}


# ============================================================
# SAVE GITHUB BACKUP
# ============================================================

with open(
    "training.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        output,
        f,
        indent=2,
        ensure_ascii=False
    )


print("Saved training.json")


# ============================================================
# SEND TO GOOGLE SHEETS
# ============================================================

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

print(
    "Google Sheets response:",
    response.text[:500]
)
