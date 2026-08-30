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
# ACTIVITY DETAILS + INTERVALS
# ============================================================

activity_details = []
intervals = []

for activity in activities:

    activity_id = activity.get("id")

    if not activity_id:
        continue

    # Skip Strava placeholder rows that are not accessible
    # through the Intervals.icu activity API.
    if not str(activity_id).startswith("i"):
        continue

    try:

        detail_url = (
            f"{BASE_URL}/activity/{activity_id}"
            f"?intervals=true"
        )

        detail = get_json(detail_url)

        activity_details.append(detail)

        activity_intervals = (
            detail.get("icu_intervals") or []
        )

        print(
            f"{activity_id}: "
            f"{len(activity_intervals)} intervals"
        )

        for number, interval in enumerate(
            activity_intervals,
            start=1
        ):

            row = dict(interval)

            row["activity_id"] = activity_id

            row["activity_date"] = activity.get(
                "start_date_local"
            )

            row["activity_name"] = activity.get(
                "name"
            )

            row["interval_number"] = number

            intervals.append(row)

    except Exception as e:

        print(
            f"Could not retrieve activity "
            f"{activity_id}: {e}"
        )


print(
    f"Retrieved details for "
    f"{len(activity_details)} activities"
)

print(
    f"Found {len(intervals)} total intervals"
)


# ============================================================
# MERGE ACTIVITY DETAILS
# ============================================================

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

        # Avoid copying large interval arrays
        # into every activity record.
        merged.pop("icu_intervals", None)

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

    print(
        f"Could not retrieve wellness: {e}"
    )


print(
    f"Found {len(wellness)} wellness records"
)


# ============================================================
# POWER CURVES
# ============================================================

power_curves = {}

curve_periods = [
    "42d",
    "84d",
    "all"
]

activity_types = [
    "Ride",
    "VirtualRide"
]


for period in curve_periods:

    power_curves[period] = {}

    for activity_type in activity_types:

        try:

            curve_url = (
                f"{BASE_URL}/athlete/"
                f"{ATHLETE_ID}/power-curves.json"
                f"?curves={period}"
                f"&type={activity_type}"
            )

            curve = get_json(curve_url)

            power_curves[period][
                activity_type
            ] = curve

            print(
                f"Retrieved {period} "
                f"{activity_type} power curve"
            )

           if isinstance(curve, dict):

    print(
        f"{period} {activity_type} "
        f"keys: {list(curve.keys())}"
    )

    curve_list = curve.get("list") or []

    print(
        f"{period} {activity_type} "
        f"list type: {type(curve_list).__name__}"
    )

    print(
        f"{period} {activity_type} "
        f"list length: {len(curve_list)}"
    )

    print(
        f"{period} {activity_type} "
        f"list sample: "
        f"{json.dumps(curve_list[:3], default=str)[:2000]}"
    )

            elif isinstance(curve, list):

                print(
                    f"{period} {activity_type} "
                    f"returned {len(curve)} items"
                )

                if len(curve) > 0:

                    first_item = curve[0]

                    if isinstance(
                        first_item,
                        dict
                    ):

                        print(
                            f"First item keys: "
                            f"{list(first_item.keys())}"
                        )

        except Exception as e:

            print(
                f"Could not retrieve "
                f"{period} {activity_type} "
                f"power curve: {e}"
            )


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

    "wellness": wellness,

    "power_curves": power_curves
}


# ============================================================
# SAVE TRAINING.JSON
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
