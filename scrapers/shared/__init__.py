"""
Shared utilities for dining scrapers
"""

from datetime import datetime

def is_likely_open_now():
    """Check if dining halls are typically open at this time"""
    now = datetime.now()
    hour = now.hour
    day = now.weekday()  # 0=Monday, 6=Sunday
    
    # Most dining halls operate:
    # Weekdays: 7am - 11pm
    # Weekends: 8am - 10pm (more limited)
    
    if day < 5:  # Monday-Friday
        return 7 <= hour < 23
    else:  # Saturday-Sunday
        return 8 <= hour < 22

def is_time_in_range(start_time_str, end_time_str):
    """Check if current time is within the given time range"""
    try:
        now = datetime.now()
        
        # Parse start and end times
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
        
        # Case 1: Meal starts today
        if start_time.date() == now.date():
            # Check if we're in the time range
            if end_time.date() > start_time.date():
                # Meal crosses midnight (e.g., 10 PM today - 2 AM tomorrow)
                return now >= start_time
            else:
                # Normal range (doesn't cross midnight)
                return start_time <= now <= end_time
        
        # Case 2: Meal started yesterday and crosses into today
        # (e.g., 10 PM yesterday - 2 AM today, and it's currently 1 AM today)
        elif start_time.date() < now.date() and end_time.date() == now.date():
            # We're in the portion that crosses into today
            return now <= end_time
        
        # Case 3: Not today at all
        else:
            return False
            
    except Exception as e:
        print(f"⚠️ Error checking time range: {e}")
        return False

def is_today(date_str):
    """Check if a date string is today"""
    try:
        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        today = datetime.now().date()
        return date.date() == today
    except:
        return False
