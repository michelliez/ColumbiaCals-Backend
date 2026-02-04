"""
meal_periods.py - Meal period detection utilities for ratings

Meal periods:
- Breakfast: before 11:00 AM
- Lunch: 11:00 AM - 4:00 PM
- Dinner: after 4:00 PM
"""

from datetime import datetime
from zoneinfo import ZoneInfo

# New York timezone for all meal period calculations
NY_TZ = ZoneInfo('America/New_York')


def get_current_meal_period():
    """
    Determine current meal period based on time of day in NY timezone

    Returns:
        str: 'breakfast', 'lunch', or 'dinner'
    """
    now = datetime.now(NY_TZ)
    hour = now.hour

    if hour < 11:
        return 'breakfast'
    elif hour < 16:  # 4 PM
        return 'lunch'
    else:
        return 'dinner'


def get_current_date():
    """
    Get current date string in YYYY-MM-DD format (NY timezone)

    Returns:
        str: Date in YYYY-MM-DD format
    """
    return datetime.now(NY_TZ).strftime('%Y-%m-%d')


def get_meal_period_display_name(period):
    """
    Convert meal period to display name

    Args:
        period: 'breakfast', 'lunch', or 'dinner'

    Returns:
        str: Capitalized display name
    """
    return {
        'breakfast': 'Breakfast',
        'lunch': 'Lunch',
        'dinner': 'Dinner'
    }.get(period, 'Unknown')


def get_meal_period_time_range(period):
    """
    Get human-readable time range for a meal period

    Args:
        period: 'breakfast', 'lunch', or 'dinner'

    Returns:
        str: Time range description
    """
    return {
        'breakfast': 'Before 11:00 AM',
        'lunch': '11:00 AM - 4:00 PM',
        'dinner': 'After 4:00 PM'
    }.get(period, '')


if __name__ == "__main__":
    # Test output
    print(f"Current meal period: {get_current_meal_period()}")
    print(f"Current date: {get_current_date()}")
    print(f"Display name: {get_meal_period_display_name(get_current_meal_period())}")
