#!/usr/bin/env python3
"""
Columbia & Barnard Dining Scraper - With Exact Meal Times
Only scrapes Breakfast, Lunch, Dinner (no "All Day")
"""

import requests
import json
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import time

# New York timezone
NY_TZ = ZoneInfo('America/New_York')

def now_ny():
    """Get current time in New York timezone"""
    return datetime.now(NY_TZ)

def parse_date_to_ny_date(date_str):
    """Parse a date string into a NY-local date (YYYY-MM-DD)."""
    if not date_str:
        return None

    try:
        # Normalize Zulu time
        normalized = date_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=NY_TZ)
    else:
        dt = dt.astimezone(NY_TZ)

    return dt.date()

def is_today_in_date_range(date_range):
    """Return True if today's NY date is within date_from/date_to (inclusive)."""
    date_from = parse_date_to_ny_date(date_range.get("date_from"))
    date_to = parse_date_to_ny_date(date_range.get("date_to"))

    # If no valid dates are present, don't filter out.
    if date_from is None and date_to is None:
        return True

    today = now_ny().date()

    if date_from and date_to:
        return date_from <= today <= date_to
    if date_from:
        return today == date_from
    return today == date_to

# ==============================================================================
# HALL-SPECIFIC MEAL TIMES - Based on actual Columbia Dining schedules
# ==============================================================================

HALL_MEAL_TIMES = {
    "John Jay Dining Hall": {
        "days": ["sunday", "monday", "tuesday", "wednesday", "thursday"],
        "meals": {
            "Breakfast": {"start": (9, 30), "end": (11, 0)},
            "Lunch": {"start": (11, 0), "end": (14, 30)},
            "Dinner": {"start": (17, 0), "end": (21, 0)}
        }
    },
    "Ferris Booth Commons": {
        "weekday": {  # Mon-Fri
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "meals": {
                "Breakfast": {"start": (7, 30), "end": (10, 30)},
                "Lunch": {"start": (11, 0), "end": (15, 0)},
                "Dinner": {"start": (17, 0), "end": (20, 0)}
            }
        },
        "saturday": {
            "days": ["saturday"],
            "meals": {
                "Breakfast": {"start": (9, 0), "end": (11, 0)},
                "Lunch": {"start": (11, 0), "end": (15, 0)},
                "Dinner": {"start": (17, 0), "end": (20, 0)}
            }
        },
        "sunday": {
            "days": ["sunday"],
            "meals": {
                "Lunch": {"start": (10, 0), "end": (14, 0)},
                "Dinner": {"start": (16, 0), "end": (20, 0)}
            }
        }
    },
    "Chef Mike's": {
        "weekday": {
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "meals": {
                "Lunch": {"start": (10, 30), "end": (15, 0)},
                "Dinner": {"start": (17, 0), "end": (22, 0)}
            }
        },
        "saturday": {
            "days": ["saturday"],
            "meals": {
                "Lunch": {"start": (11, 0), "end": (15, 0)},
                "Dinner": {"start": (15, 0), "end": (19, 0)}
            }
        }
    },
    "Grace Dodge": {
        "days": ["monday", "tuesday", "wednesday", "thursday"],
        "meals": {
            "Lunch": {"start": (11, 0), "end": (14, 30)},
            "Dinner": {"start": (14, 30), "end": (19, 30)}
        }
    },
    "Faculty House 2nd Floor": {
        "days": ["monday", "tuesday", "wednesday", "thursday"],
        "meals": {
            "Lunch": {"start": (11, 0), "end": (14, 30)}
        }
    },
    "Faculty House Skyline": {
        "days": ["monday", "tuesday", "wednesday", "thursday"],
        "meals": {
            "Lunch": {"start": (11, 0), "end": (14, 30)}
        }
    },
    "Johnny's": {
        "mon_wed": {
            "days": ["monday", "tuesday", "wednesday"],
            "meals": {
                "Lunch": {"start": (11, 0), "end": (14, 30)}
            }
        },
        "thu_fri": {
            "days": ["thursday", "friday"],
            "meals": {
                "Lunch": {"start": (11, 0), "end": (14, 30)},
                "Dinner": {"start": (19, 0), "end": (23, 0)}
            }
        },
        "saturday": {
            "days": ["saturday"],
            "meals": {
                "Dinner": {"start": (19, 0), "end": (23, 0)}
            }
        },
        "sunday": {
            "days": ["sunday"],
            "meals": {
                "Dinner": {"start": (18, 0), "end": (22, 0)}
            }
        }
    },
    "Fac Shack": {
        "weekday": {
            "days": ["monday", "tuesday", "wednesday", "thursday"],
            "meals": {
                "Lunch": {"start": (12, 0), "end": (15, 0)},
                "Dinner": {"start": (17, 0), "end": (20, 0)}
            }
        },
        "sunday": {
            "days": ["sunday"],
            "meals": {
                "Dinner": {"start": (15, 0), "end": (20, 0)}
            }
        }
    }
}

# ==============================================================================
# STATIC MENU LOCATIONS - These don't change their menus
# ==============================================================================

STATIC_MENU_LOCATIONS = {
    "JJ's Place": {
        "operating_hours": "Open daily 12:00 p.m. - 10:00 a.m.",
        "days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
        "hours": {"start": (12, 0), "end": (10, 0)},  # Crosses midnight
        "menu_items": [
            {"name": "Hamburger", "description": "Classic beef burger", "allergens": ["Gluten"], "dietary_prefs": []},
            {"name": "Cheeseburger", "description": "Beef burger with cheese", "allergens": ["Gluten", "Dairy"], "dietary_prefs": []},
            {"name": "Fried Chicken Burger", "description": "Crispy fried chicken sandwich", "allergens": ["Gluten"], "dietary_prefs": []},
            {"name": "Chicken Nuggets", "description": "Breaded chicken nuggets", "allergens": ["Gluten"], "dietary_prefs": []},
            {"name": "Chicken Tenders", "description": "Breaded chicken tenders", "allergens": ["Gluten"], "dietary_prefs": []},
            {"name": "French Fries", "description": "Crispy golden fries", "allergens": [], "dietary_prefs": ["Vegan", "Gluten Free"]},
            {"name": "Quesadilla", "description": "Cheese quesadilla", "allergens": ["Dairy", "Gluten"], "dietary_prefs": ["Vegetarian"]},
            {"name": "Pancakes", "description": "Fluffy pancakes", "allergens": ["Gluten", "Eggs", "Dairy"], "dietary_prefs": ["Vegetarian"]},
            {"name": "Chocolate Chip Pancakes", "description": "Pancakes with chocolate chips", "allergens": ["Gluten", "Eggs", "Dairy"], "dietary_prefs": ["Vegetarian"]},
            {"name": "French Toast", "description": "Classic french toast", "allergens": ["Gluten", "Eggs", "Dairy"], "dietary_prefs": ["Vegetarian"]}
        ]
    },
    "Blue Java Butler": {
        "operating_hours": "Monday - Thursday, 8 a.m. - 12 a.m. | Friday - Sunday, 9 a.m. - 9 p.m.",
        "weekday": {
            "days": ["monday", "tuesday", "wednesday", "thursday"],
            "hours": {"start": (8, 0), "end": (0, 0)}
        },
        "weekend": {
            "days": ["friday", "saturday", "sunday"],
            "hours": {"start": (9, 0), "end": (21, 0)}
        },
        "menu_items": [
            {"name": "Hot Espresso Beverages", "description": "Lattes, cappuccinos, americanos", "allergens": ["Dairy"], "dietary_prefs": []},
            {"name": "Iced Espresso Beverages", "description": "Iced lattes, iced cappuccinos", "allergens": ["Dairy"], "dietary_prefs": []},
            {"name": "Iced Coffee", "description": "Cold brewed iced coffee", "allergens": [], "dietary_prefs": ["Vegan"]},
            {"name": "Hot Brewed Coffee", "description": "Fresh hot coffee", "allergens": [], "dietary_prefs": ["Vegan"]},
            {"name": "Cold Brew Coffee", "description": "Slow-steeped cold brew", "allergens": [], "dietary_prefs": ["Vegan"]},
            {"name": "Paninis", "description": "Assorted grilled paninis", "allergens": ["Gluten", "Dairy"], "dietary_prefs": []},
            {"name": "Republic of Tea", "description": "Premium tea selection", "allergens": [], "dietary_prefs": ["Vegan"]},
            {"name": "Specialty Teas", "description": "Assorted specialty teas", "allergens": [], "dietary_prefs": ["Vegan"]},
            {"name": "Assorted Muffins", "description": "Various muffin flavors", "allergens": ["Gluten", "Eggs", "Dairy"], "dietary_prefs": ["Vegetarian"]},
            {"name": "Assorted Pastries", "description": "Fresh baked pastries", "allergens": ["Gluten", "Eggs", "Dairy"], "dietary_prefs": ["Vegetarian"]},
            {"name": "Chilled Drinks", "description": "Bottled beverages and juices", "allergens": [], "dietary_prefs": ["Vegan"]},
            {"name": "Assorted Fruit", "description": "Fresh fruit cups", "allergens": [], "dietary_prefs": ["Vegan", "Gluten Free"]},
            {"name": "Assorted Snacks", "description": "Grab and go snacks", "allergens": [], "dietary_prefs": []}
        ]
    },
    "Blue Java Uris": {
        "operating_hours": "Monday - Friday: 8:00 a.m. - 5:30 p.m.",
        "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
        "hours": {"start": (8, 0), "end": (17, 30)},
        "menu_items": [
            {"name": "Hot Espresso Beverages", "description": "Lattes, cappuccinos, americanos", "allergens": ["Dairy"], "dietary_prefs": []},
            {"name": "Iced Espresso Beverages", "description": "Iced lattes, iced cappuccinos", "allergens": ["Dairy"], "dietary_prefs": []},
            {"name": "Iced Coffee", "description": "Cold brewed iced coffee", "allergens": [], "dietary_prefs": ["Vegan"]},
            {"name": "Hot Brewed Coffee", "description": "Fresh hot coffee", "allergens": [], "dietary_prefs": ["Vegan"]},
            {"name": "Cold Brew Coffee", "description": "Slow-steeped cold brew", "allergens": [], "dietary_prefs": ["Vegan"]},
            {"name": "Paninis", "description": "Assorted grilled paninis", "allergens": ["Gluten", "Dairy"], "dietary_prefs": []},
            {"name": "Republic of Tea", "description": "Premium tea selection", "allergens": [], "dietary_prefs": ["Vegan"]},
            {"name": "Assorted Muffins", "description": "Various muffin flavors", "allergens": ["Gluten", "Eggs", "Dairy"], "dietary_prefs": ["Vegetarian"]},
            {"name": "Assorted Pastries", "description": "Fresh baked pastries", "allergens": ["Gluten", "Eggs", "Dairy"], "dietary_prefs": ["Vegetarian"]},
            {"name": "Chilled Drinks", "description": "Bottled beverages and juices", "allergens": [], "dietary_prefs": ["Vegan"]},
            {"name": "Assorted Fruit", "description": "Fresh fruit cups", "allergens": [], "dietary_prefs": ["Vegan", "Gluten Free"]},
            {"name": "Assorted Snacks", "description": "Grab and go snacks", "allergens": [], "dietary_prefs": []}
        ]
    },
    "Blue Java Mudd": {
        "operating_hours": "Monday - Friday: 8 a.m. - 6 p.m.",
        "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
        "hours": {"start": (8, 0), "end": (18, 0)},
        "menu_items": [
            {"name": "Hot Espresso Beverages", "description": "Lattes, cappuccinos, americanos", "allergens": ["Dairy"], "dietary_prefs": []},
            {"name": "Iced Espresso Beverages", "description": "Iced lattes, iced cappuccinos", "allergens": ["Dairy"], "dietary_prefs": []},
            {"name": "Iced Coffee", "description": "Cold brewed iced coffee", "allergens": [], "dietary_prefs": ["Vegan"]},
            {"name": "Hot Brewed Coffee", "description": "Fresh hot coffee", "allergens": [], "dietary_prefs": ["Vegan"]},
            {"name": "Cold Brew Coffee", "description": "Slow-steeped cold brew", "allergens": [], "dietary_prefs": ["Vegan"]},
            {"name": "Paninis", "description": "Assorted grilled paninis", "allergens": ["Gluten", "Dairy"], "dietary_prefs": []},
            {"name": "Republic of Tea", "description": "Premium tea selection", "allergens": [], "dietary_prefs": ["Vegan"]},
            {"name": "Assorted Muffins", "description": "Various muffin flavors", "allergens": ["Gluten", "Eggs", "Dairy"], "dietary_prefs": ["Vegetarian"]},
            {"name": "Assorted Pastries", "description": "Fresh baked pastries", "allergens": ["Gluten", "Eggs", "Dairy"], "dietary_prefs": ["Vegetarian"]},
            {"name": "Chilled Drinks", "description": "Bottled beverages and juices", "allergens": [], "dietary_prefs": ["Vegan"]},
            {"name": "Assorted Fruit", "description": "Fresh fruit cups", "allergens": [], "dietary_prefs": ["Vegan", "Gluten Free"]},
            {"name": "Assorted Snacks", "description": "Grab and go snacks", "allergens": [], "dietary_prefs": []}
        ]
    },
    "Blue Java Everett": {
        "operating_hours": "Monday - Thursday, 8:00 a.m. - 7:30 p.m. | Friday, 8:00 a.m. - 2:30 p.m.",
        "weekday": {
            "days": ["monday", "tuesday", "wednesday", "thursday"],
            "hours": {"start": (8, 0), "end": (19, 30)}
        },
        "friday": {
            "days": ["friday"],
            "hours": {"start": (8, 0), "end": (14, 30)}
        },
        "menu_items": [
            {"name": "Hot Espresso Beverages", "description": "Lattes, cappuccinos, americanos", "allergens": ["Dairy"], "dietary_prefs": []},
            {"name": "Iced Espresso Beverages", "description": "Iced lattes, iced cappuccinos", "allergens": ["Dairy"], "dietary_prefs": []},
            {"name": "Iced Coffee", "description": "Cold brewed iced coffee", "allergens": [], "dietary_prefs": ["Vegan"]},
            {"name": "Hot Brewed Coffee", "description": "Fresh hot coffee", "allergens": [], "dietary_prefs": ["Vegan"]},
            {"name": "Cold Brew Coffee", "description": "Slow-steeped cold brew", "allergens": [], "dietary_prefs": ["Vegan"]},
            {"name": "Paninis", "description": "Assorted grilled paninis", "allergens": ["Gluten", "Dairy"], "dietary_prefs": []},
            {"name": "Republic of Tea", "description": "Premium tea selection", "allergens": [], "dietary_prefs": ["Vegan"]},
            {"name": "Assorted Muffins", "description": "Various muffin flavors", "allergens": ["Gluten", "Eggs", "Dairy"], "dietary_prefs": ["Vegetarian"]},
            {"name": "Assorted Pastries", "description": "Fresh baked pastries", "allergens": ["Gluten", "Eggs", "Dairy"], "dietary_prefs": ["Vegetarian"]},
            {"name": "Chilled Drinks", "description": "Bottled beverages and juices", "allergens": [], "dietary_prefs": ["Vegan"]},
            {"name": "Assorted Fruit", "description": "Fresh fruit cups", "allergens": [], "dietary_prefs": ["Vegan", "Gluten Free"]},
            {"name": "Assorted Snacks", "description": "Grab and go snacks", "allergens": [], "dietary_prefs": []}
        ]
    },
    "Lenfest Cafe": {
        "operating_hours": "Monday - Thursday: 8:00 a.m. - 6:30 p.m. | Friday: 8:00 a.m. - 3:00 p.m.",
        "weekday": {
            "days": ["monday", "tuesday", "wednesday", "thursday"],
            "hours": {"start": (8, 0), "end": (18, 30)}
        },
        "friday": {
            "days": ["friday"],
            "hours": {"start": (8, 0), "end": (15, 0)}
        },
        "menu_items": [
            {"name": "Hot Espresso Beverages", "description": "Lattes, cappuccinos, americanos", "allergens": ["Dairy"], "dietary_prefs": []},
            {"name": "Iced Coffee", "description": "Cold brewed iced coffee", "allergens": [], "dietary_prefs": ["Vegan"]},
            {"name": "Hot Brewed Coffee", "description": "Fresh hot coffee", "allergens": [], "dietary_prefs": ["Vegan"]},
            {"name": "Sandwiches", "description": "Fresh made sandwiches", "allergens": ["Gluten"], "dietary_prefs": []},
            {"name": "Salads", "description": "Fresh salads", "allergens": [], "dietary_prefs": ["Vegetarian"]},
            {"name": "Assorted Pastries", "description": "Fresh baked pastries", "allergens": ["Gluten", "Eggs", "Dairy"], "dietary_prefs": ["Vegetarian"]},
            {"name": "Chilled Drinks", "description": "Bottled beverages and juices", "allergens": [], "dietary_prefs": ["Vegan"]},
            {"name": "Assorted Snacks", "description": "Grab and go snacks", "allergens": [], "dietary_prefs": []}
        ]
    },
    "Robert F. Smith": {
        "operating_hours": "Monday - Thursday, 8 a.m. - 4:30 p.m. | Friday, 8 a.m. - 4 p.m.",
        "weekday": {
            "days": ["monday", "tuesday", "wednesday", "thursday"],
            "hours": {"start": (8, 0), "end": (16, 30)}
        },
        "friday": {
            "days": ["friday"],
            "hours": {"start": (8, 0), "end": (16, 0)}
        },
        "menu_items": [
            {"name": "Hot Espresso Beverages", "description": "Lattes, cappuccinos, americanos", "allergens": ["Dairy"], "dietary_prefs": []},
            {"name": "Iced Coffee", "description": "Cold brewed iced coffee", "allergens": [], "dietary_prefs": ["Vegan"]},
            {"name": "Hot Brewed Coffee", "description": "Fresh hot coffee", "allergens": [], "dietary_prefs": ["Vegan"]},
            {"name": "Sandwiches", "description": "Fresh made sandwiches", "allergens": ["Gluten"], "dietary_prefs": []},
            {"name": "Salads", "description": "Fresh salads", "allergens": [], "dietary_prefs": ["Vegetarian"]},
            {"name": "Assorted Pastries", "description": "Fresh baked pastries", "allergens": ["Gluten", "Eggs", "Dairy"], "dietary_prefs": ["Vegetarian"]},
            {"name": "Chilled Drinks", "description": "Bottled beverages and juices", "allergens": [], "dietary_prefs": ["Vegan"]},
            {"name": "Assorted Snacks", "description": "Grab and go snacks", "allergens": [], "dietary_prefs": []}
        ]
    }
}

# ==============================================================================
# COLUMBIA DINING HALL URLS - For scraping dynamic menus
# ==============================================================================

COLUMBIA_DYNAMIC_HALLS = [
    {"name": "John Jay Dining Hall", "url": "https://dining.columbia.edu/content/john-jay-dining-hall"},
    {"name": "Ferris Booth Commons", "url": "https://dining.columbia.edu/content/ferris-booth-commons-0"},
    {"name": "Grace Dodge", "url": "https://dining.columbia.edu/content/grace-dodge-dining-hall-0"},
    {"name": "Faculty House 2nd Floor", "url": "https://dining.columbia.edu/content/faculty-house-2nd-floor-0"},
    {"name": "Faculty House Skyline", "url": "https://dining.columbia.edu/content/faculty-house-4th-floor-skyline-room"},
    {"name": "Fac Shack", "url": "https://dining.columbia.edu/content/fac-shack-0"},
    {"name": "Chef Mike's", "url": "https://dining.columbia.edu/chef-mikes"},
    {"name": "Johnny's", "url": "https://dining.columbia.edu/johnnys"}
]

COLUMBIA_STATIC_HALLS = [
    {"name": "JJ's Place", "url": "https://dining.columbia.edu/content/jjs-place-0"},
    {"name": "Blue Java Butler", "url": "https://dining.columbia.edu/content/blue-java-cafe-butler-library-0"},
    {"name": "Blue Java Uris", "url": "https://dining.columbia.edu/content/blue-java-cafe-uris-hall"},
    {"name": "Blue Java Mudd", "url": "https://dining.columbia.edu/content/blue-java-cafe-mudd-hall-0"},
    {"name": "Blue Java Everett", "url": "https://dining.columbia.edu/content/blue-java-everett-library-cafe"},
    {"name": "Lenfest Cafe", "url": "https://dining.columbia.edu/content/lenfest-cafe-0"},
    {"name": "Robert F. Smith", "url": "https://dining.columbia.edu/content/robert-f-smith-dining-hall-0"}
]

# Barnard Dining Halls (DineOnCampus API)
BARNARD_LOCATIONS = [
    {
        "name": "Hewitt Dining Hall",
        "location_id": "5d27a0461ca48e0aca2a104c",
        "periods": {
            "Breakfast": "697fa33a771598a5a6eb2f01",
            "Lunch": "697fb150771598a5a6ebea1b",
            "Dinner": "697fa349771598a5a6eb2f3e"
        }
    },
    {
        "name": "Diana Center",
        "location_id": "5d27a073e5be796ca46a93f9",
        "periods": {
            "Breakfast": "697fa33a771598a5a6eb2f01",
            "Lunch": "697fb150771598a5a6ebea1b",
            "Dinner": "697fa349771598a5a6eb2f3e"
        }
    },
    {
        "name": "Liz's Place",
        "location_id": "5d27a0c31ca48e0aca2a104d",
        "periods": {
            "Breakfast": "697fa33a771598a5a6eb2f01",
            "Lunch": "697fb150771598a5a6ebea1b",
            "Dinner": "697fa349771598a5a6eb2f3e"
        }
    }
]

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def format_time_tuple(hour, minute):
    """Format (hour, minute) tuple to readable string like '9:30 AM'"""
    if hour == 0:
        return "12:00 AM"
    elif hour < 12:
        return f"{hour}:{minute:02d} AM"
    elif hour == 12:
        return f"12:{minute:02d} PM"
    else:
        return f"{hour-12}:{minute:02d} PM"

def get_meal_times_for_hall(hall_name):
    """Get the meal times configuration for a specific hall"""
    if hall_name not in HALL_MEAL_TIMES:
        return None

    config = HALL_MEAL_TIMES[hall_name]
    now = now_ny()
    day_name = now.strftime('%A').lower()

    # Check if hall has day-specific configurations
    if "days" in config:
        # Simple configuration - same times all days
        if day_name in config["days"]:
            return config["meals"]
        return None
    else:
        # Complex configuration with different schedules per day
        for schedule_name, schedule in config.items():
            if isinstance(schedule, dict) and "days" in schedule:
                if day_name in schedule["days"]:
                    return schedule.get("meals", {})
    return None

def is_hall_open_now(hall_name):
    """Check if a hall is currently open based on its meal times"""
    meal_times = get_meal_times_for_hall(hall_name)
    if not meal_times:
        return False

    now = now_ny()
    current_minutes = now.hour * 60 + now.minute

    for meal_name, times in meal_times.items():
        start_h, start_m = times["start"]
        end_h, end_m = times["end"]

        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m

        # Handle overnight hours
        if end_minutes < start_minutes:
            # Crosses midnight
            if current_minutes >= start_minutes or current_minutes < end_minutes:
                return True
        else:
            if start_minutes <= current_minutes < end_minutes:
                return True

    return False

def get_current_meal_for_hall(hall_name):
    """Get the current meal being served at a hall"""
    meal_times = get_meal_times_for_hall(hall_name)
    if not meal_times:
        return None

    now = now_ny()
    current_minutes = now.hour * 60 + now.minute

    for meal_name, times in meal_times.items():
        start_h, start_m = times["start"]
        end_h, end_m = times["end"]

        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m

        # Handle overnight hours
        if end_minutes < start_minutes:
            if current_minutes >= start_minutes or current_minutes < end_minutes:
                return meal_name
        else:
            if start_minutes <= current_minutes < end_minutes:
                return meal_name

    return None

def is_static_hall_open(hall_name):
    """Check if a static menu hall is currently open"""
    if hall_name not in STATIC_MENU_LOCATIONS:
        return False

    config = STATIC_MENU_LOCATIONS[hall_name]
    now = now_ny()
    day_name = now.strftime('%A').lower()
    current_minutes = now.hour * 60 + now.minute

    # Get hours for today
    hours_config = None

    if "days" in config:
        # Simple configuration
        if day_name in config["days"]:
            hours_config = config["hours"]
    else:
        # Check day-specific schedules
        for schedule_name, schedule in config.items():
            if isinstance(schedule, dict) and "days" in schedule:
                if day_name in schedule["days"]:
                    hours_config = schedule.get("hours")
                    break

    if not hours_config:
        return False

    start_h, start_m = hours_config["start"]
    end_h, end_m = hours_config["end"]

    start_minutes = start_h * 60 + start_m
    end_minutes = end_h * 60 + end_m

    # Handle overnight hours (like JJ's Place 12pm - 10am)
    if end_minutes < start_minutes or (end_h == 0 and end_m == 0):
        if end_h == 0 and end_m == 0:
            end_minutes = 24 * 60  # Midnight
        else:
            # Crosses midnight - check if we're after start OR before end
            return current_minutes >= start_minutes or current_minutes < end_minutes

    return start_minutes <= current_minutes < end_minutes

def extract_menu_data(html):
    """Extract menu_data JSON from Columbia HTML"""
    pattern = r'var menu_data = `(.+?)`;'
    match = re.search(pattern, html, re.DOTALL)

    if not match:
        return None

    json_str = match.group(1)

    try:
        import codecs
        json_str_decoded = codecs.decode(json_str, 'unicode_escape')
        menu_data = json.loads(json_str_decoded)
        return menu_data
    except Exception:
        try:
            menu_data = json.loads(json_str)
            return menu_data
        except json.JSONDecodeError:
            return None

def get_operating_hours_display(hall_name):
    """Get the display string for operating hours"""
    if hall_name in STATIC_MENU_LOCATIONS:
        return STATIC_MENU_LOCATIONS[hall_name].get("operating_hours")

    # For dynamic halls, build from meal times
    if hall_name in HALL_MEAL_TIMES:
        config = HALL_MEAL_TIMES[hall_name]
        if "days" in config:
            days = config["days"]
            meals = config.get("meals", {})
            if meals:
                first_meal = list(meals.values())[0]
                last_meal = list(meals.values())[-1]
                start = format_time_tuple(*first_meal["start"])
                end = format_time_tuple(*last_meal["end"])
                day_str = ", ".join([d.capitalize() for d in days])
                return f"{day_str}: {start} - {end}"

    return None

# ==============================================================================
# SCRAPING FUNCTIONS
# ==============================================================================

def scrape_static_hall(hall):
    """Create menu data for a static menu hall"""
    hall_name = hall["name"]

    if hall_name not in STATIC_MENU_LOCATIONS:
        return {
            "name": hall_name,
            "meals": [],
            "status": "closed",
            "source": "columbia",
            "scraped_at": now_ny().isoformat()
        }

    config = STATIC_MENU_LOCATIONS[hall_name]
    is_open = is_static_hall_open(hall_name)

    # Create a single "All Day" meal with the static menu items
    meals = []
    if is_open:
        meals = [{
            "meal_type": "All Day",
            "time": config.get("operating_hours", "Check website for hours"),
            "stations": [{
                "station": "Menu",
                "items": config["menu_items"]
            }]
        }]

    return {
        "name": hall_name,
        "meals": meals,
        "status": "open" if is_open else "closed",
        "source": "columbia",
        "operating_hours": config.get("operating_hours"),
        "is_open": is_open,
        "scraped_at": now_ny().isoformat()
    }

def scrape_dynamic_hall(hall):
    """Scrape a Columbia dining hall with dynamic menu - ONLY Breakfast/Lunch/Dinner"""
    hall_name = hall["name"]

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'en-US,en;q=0.5',
        }

        response = requests.get(hall['url'], headers=headers, timeout=30)
        response.raise_for_status()

        menu_data = extract_menu_data(response.text)

        # Get hall-specific meal times
        meal_times = get_meal_times_for_hall(hall_name)
        is_open = is_hall_open_now(hall_name)
        operating_hours = get_operating_hours_display(hall_name)

        if not menu_data:
            return {
                "name": hall_name,
                "meals": [],
                "status": "open_no_menu" if is_open else "closed",
                "source": "columbia",
                "operating_hours": operating_hours,
                "is_open": is_open,
                "scraped_at": now_ny().isoformat()
            }

        # Station ID to name mapping
        station_names = {
            "10": "Smoothie Bar",
            "12": "Kosher Station",
            "16": "Halal Station",
            "24": "Main Station",
            "27": "Bakery",
            "28": "Soup & Oatmeal",
            "29": "Vegan Station",
            "33": "Grill",
            "100": "Asian Station",
            "159": "Pasta Station"
        }

        # Meal type mapping - ONLY these three
        VALID_MEAL_TYPES = {"6": "Breakfast", "7": "Lunch", "8": "Dinner"}

        # Collect all items by meal type
        meals_by_type = {}

        for menu in menu_data:
            date_ranges = menu.get('date_range_fields', [])

            for date_range in date_ranges:
                # Filter to only today's menu items
                if not is_today_in_date_range(date_range):
                    continue
                menu_types = date_range.get('menu_type', [])

                # Skip if not Breakfast, Lunch, or Dinner
                if not menu_types or menu_types[0] not in VALID_MEAL_TYPES:
                    continue

                meal_type = VALID_MEAL_TYPES[menu_types[0]]

                # Check if this meal type is served at this hall
                if meal_times and meal_type not in meal_times:
                    continue

                # Extract stations with items
                stations_data = []
                stations = date_range.get('stations', [])

                for station in stations:
                    station_ids = station.get('station', [])
                    station_name = station_names.get(station_ids[0] if station_ids else "", "Station")

                    items = []
                    meals_paragraph = station.get('meals_paragraph', [])

                    for meal in meals_paragraph:
                        item = {
                            "name": meal.get('title', '').strip(),
                            "description": meal.get('meal_text', '').strip() if meal.get('meal_text') else None,
                            "allergens": meal.get('allergens', []),
                            "dietary_prefs": meal.get('prefs', [])
                        }

                        if item['name'] and len(item['name']) > 2:
                            items.append(item)

                    if items:
                        stations_data.append({
                            "station": station_name,
                            "items": items
                        })

                # Add to meals by type
                if stations_data:
                    if meal_type not in meals_by_type:
                        meals_by_type[meal_type] = {"stations": []}

                    # Merge stations
                    existing_stations = meals_by_type[meal_type]["stations"]
                    for new_station in stations_data:
                        found = False
                        for existing in existing_stations:
                            if existing["station"] == new_station["station"]:
                                # Merge items
                                existing_names = {it["name"] for it in existing["items"]}
                                for item in new_station["items"]:
                                    if item["name"] not in existing_names:
                                        existing["items"].append(item)
                                        existing_names.add(item["name"])
                                found = True
                                break
                        if not found:
                            existing_stations.append(new_station)

        # Build final meals list with proper times
        meals = []
        meal_order = ["Breakfast", "Lunch", "Dinner"]

        for meal_type in meal_order:
            if meal_type in meals_by_type and meals_by_type[meal_type]["stations"]:
                # Get time from hall config
                time_str = None
                if meal_times and meal_type in meal_times:
                    times = meal_times[meal_type]
                    start_str = format_time_tuple(*times["start"])
                    end_str = format_time_tuple(*times["end"])
                    time_str = f"{start_str} - {end_str}"

                meals.append({
                    "meal_type": meal_type,
                    "time": time_str,
                    "stations": meals_by_type[meal_type]["stations"]
                })

        # Determine status
        if meals:
            status = "open"
        elif is_open:
            status = "open_no_menu"
        else:
            status = "closed"

        return {
            "name": hall_name,
            "meals": meals,
            "status": status,
            "source": "columbia",
            "operating_hours": operating_hours,
            "is_open": is_open,
            "scraped_at": now_ny().isoformat()
        }

    except requests.exceptions.HTTPError as e:
        if '503' in str(e):
            return {
                "name": hall_name,
                "meals": [],
                "status": "service_unavailable",
                "source": "columbia",
                "error": "Columbia Dining website is temporarily down",
                "scraped_at": now_ny().isoformat()
            }
        return {
            "name": hall_name,
            "meals": [],
            "status": "error",
            "source": "columbia",
            "error": str(e),
            "scraped_at": now_ny().isoformat()
        }
    except requests.exceptions.RequestException as e:
        return {
            "name": hall_name,
            "meals": [],
            "status": "network_error",
            "source": "columbia",
            "error": "Unable to reach Columbia Dining website",
            "scraped_at": now_ny().isoformat()
        }
    except Exception as e:
        return {
            "name": hall_name,
            "meals": [],
            "status": "error",
            "source": "columbia",
            "error": str(e),
            "scraped_at": now_ny().isoformat()
        }

def scrape_barnard_hall(hall):
    """Scrape a Barnard dining hall via DineOnCampus API"""
    today = now_ny().strftime("%Y-%m-%d")

    meals = []

    for period_name, period_id in hall['periods'].items():
        url = f"https://apiv4.dineoncampus.com/locations/{hall['location_id']}/menu"

        params = {
            "date": today,
            "period": period_id
        }

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
                'Accept': 'application/json',
                'Origin': 'https://barnard.dineoncampus.com',
                'Referer': 'https://barnard.dineoncampus.com/'
            }

            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()

            period_data = data.get('period', {})
            categories = period_data.get('categories', [])

            stations_data = []

            for category in categories:
                category_name = category.get('name', 'Station')
                items = []

                for item in category.get('items', []):
                    item_obj = {
                        "name": item.get('name', '').strip(),
                        "description": item.get('desc', '').strip() if item.get('desc') else None,
                        "allergens": [f.get('name', '') for f in item.get('filters', []) if not f.get('icon', False)],
                        "dietary_prefs": [f.get('name', '') for f in item.get('filters', []) if f.get('icon', False)]
                    }

                    if item_obj['name'] and len(item_obj['name']) > 2:
                        items.append(item_obj)

                if items:
                    stations_data.append({
                        "station": category_name,
                        "items": items
                    })

            if stations_data:
                meals.append({
                    "meal_type": period_name,
                    "time": "Check Barnard dining hours",
                    "stations": stations_data
                })

        except Exception:
            continue

    # Determine status
    now = now_ny()
    hour = now.hour
    day = now.weekday()

    is_likely_open = (7 <= hour < 23) if day < 5 else (8 <= hour < 22)

    if meals:
        status = "open"
    elif is_likely_open:
        status = "open_no_menu"
    else:
        status = "closed"

    return {
        "name": hall['name'],
        "meals": meals,
        "status": status,
        "source": "barnard",
        "scraped_at": now_ny().isoformat()
    }

def scrape_all_locations():
    """Scrape all Columbia and Barnard dining locations"""
    print("🦁 Columbia & Barnard Dining Scraper")
    print("=" * 50)

    results = []

    # Scrape Columbia dynamic halls
    print("\n📍 Scraping Columbia halls (dynamic menus)...")
    for hall in COLUMBIA_DYNAMIC_HALLS:
        print(f"   {hall['name']}...")
        data = scrape_dynamic_hall(hall)
        results.append(data)

        status = data.get('status', 'unknown')
        meal_count = len(data.get('meals', []))

        if status == 'open' and meal_count > 0:
            print(f"      ✅ Open - {meal_count} meal(s)")
        elif status == 'open_no_menu':
            print(f"      ⚠️  Open but no menu available")
        elif status == 'closed':
            print(f"      ⏰ Closed")
        else:
            print(f"      ❌ Error: {status}")

        time.sleep(1)

    # Scrape Columbia static halls
    print("\n📍 Scraping Columbia cafes (static menus)...")
    for hall in COLUMBIA_STATIC_HALLS:
        print(f"   {hall['name']}...")
        data = scrape_static_hall(hall)
        results.append(data)

        status = data.get('status', 'unknown')
        if status == 'open':
            print(f"      ✅ Open")
        else:
            print(f"      ⏰ Closed")

    # Scrape Barnard halls
    print("\n📍 Scraping Barnard halls...")
    for hall in BARNARD_LOCATIONS:
        print(f"   {hall['name']}...")
        data = scrape_barnard_hall(hall)
        results.append(data)

        meal_count = len(data.get('meals', []))
        if meal_count > 0:
            print(f"      ✅ {meal_count} meal(s)")
        else:
            print(f"      ⏰ Closed or no menu")

        time.sleep(1)

    # Save results
    with open('menu_data.json', 'w') as f:
        json.dump(results, f, indent=2)

    # Summary
    open_count = sum(1 for r in results if r.get('status') == 'open')
    closed_count = sum(1 for r in results if r.get('status') == 'closed')

    print(f"\n✅ Scraped {len(results)} locations")
    print(f"   🟢 Open: {open_count}")
    print(f"   🔴 Closed: {closed_count}")
    print(f"\n📄 Saved to menu_data.json")

    return results

if __name__ == "__main__":
    scrape_all_locations()
