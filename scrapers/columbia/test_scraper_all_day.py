import json
import types
from datetime import datetime, timedelta, timezone

import scraper


def make_iso(dt):
    return dt.replace(tzinfo=timezone.utc).isoformat()


def test_all_day_splits_into_three_meals():
    # Build a menu_data with a single All Day date_range for today
    now_utc = datetime.utcnow().replace(hour=12, minute=0, second=0, microsecond=0)
    start = now_utc - timedelta(hours=1)
    end = now_utc + timedelta(hours=8)

    menu_data = [
        {
            "date_range_fields": [
                {
                    "date_from": make_iso(start),
                    "date_to": make_iso(end),
                    "menu_type": ["61"],  # All Day
                    "stations": [
                        {
                            "station": ["24"],
                            "meals_paragraph": [
                                {"title": "All Day Sandwich", "meal_text": "Tasty", "allergens": [], "prefs": []}
                            ]
                        }
                    ]
                }
            ]
        }
    ]

    # Create a fake response HTML that extract_menu_data can decode
    fake_html = f"var menu_data = `{json.dumps(menu_data)}`;"

    # Monkeypatch requests.get to return this HTML
    class FakeResp:
        def __init__(self, text):
            self.text = text
        def raise_for_status(self):
            return

    def fake_get(url, headers=None, timeout=None):
        return FakeResp(fake_html)

    # Inject fake_get into requests used by scraper
    scraper.requests.get = fake_get

    hall = {"name": "Fake Hall", "url": "https://dining.columbia.edu/fake"}
    result = scraper.scrape_columbia_hall(hall)

    # Ensure All Day items are split into Breakfast, Lunch, and Dinner using standard windows
    meals = {m["meal_type"]: m for m in result.get("meals", [])}

    assert "Breakfast" in meals and "Lunch" in meals and "Dinner" in meals

    # Verify meal times match expected standard windows
    assert meals["Breakfast"]["time"] == "7:00 AM - 10:30 AM"
    assert meals["Lunch"]["time"] == "11:00 AM - 2:00 PM"
    assert meals["Dinner"]["time"] == "5:00 PM - 8:00 PM"

    # Ensure the item is present in each meal's stations
    for meal_name in ["Breakfast", "Lunch", "Dinner"]:
        meal = meals[meal_name]
        stations = meal.get("stations", [])
        assert any(any(item["name"] == "All Day Sandwich" for item in st["items"]) for st in stations)



if __name__ == "__main__":
    test_all_day_splits_into_three_meals()
    print("OK")
