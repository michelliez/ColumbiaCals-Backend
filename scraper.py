#!/usr/bin/env python3
"""
Columbia Official Dining Site Scraper - With Filtering
Scrapes from dining.columbia.edu and filters out non-food items
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import time

# ALL Hall URLs on Columbia's site
DINING_HALL_URLS = {
    "John Jay": "https://dining.columbia.edu/content/john-jay-dining-hall",
    "Ferris": "https://dining.columbia.edu/content/ferris-booth-commons",
    "JJ's": "https://dining.columbia.edu/content/jjs-place",
    "Grace Dodge": "https://dining.columbia.edu/content/grace-dodge-dining-hall",
    "Fac Shack": "https://dining.columbia.edu/content/fac-shack",
    "Chef Mike's": "https://dining.columbia.edu/content/chef-mikes-sub-shop",
    "Faculty House": "https://dining.columbia.edu/content/faculty-house",
    "Robert F. Smith": "https://dining.columbia.edu/content/robert-f-smith-dining-hall",
    "Chef Don's": "https://dining.columbia.edu/content/chef-dons-pizza-pi",
    "Johnny's": "https://dining.columbia.edu/content/johnnys-cafe",
    "Blue Java Butler": "https://dining.columbia.edu/content/blue-java-cafe-butler-library",
    "Blue Java Everett": "https://dining.columbia.edu/content/blue-java-everett-library-cafe",
    "Blue Java Uris": "https://dining.columbia.edu/content/blue-java-cafe-uris",
    "Lenfest Café": "https://dining.columbia.edu/content/lenfest-cafe",
}

# Words/phrases to exclude (not food items)
EXCLUDE_KEYWORDS = [
    'hour', 'hours', 'time', 'open', 'close', 'closed',
    'location', 'address', 'phone', 'contact',
    'menu', 'today', 'tomorrow', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
    'breakfast', 'lunch', 'dinner', 'brunch',
    'flex', 'dollar', 'dining', 'meal', 'plan', 'swipe',
    'copyright', 'privacy', 'terms', 'policy',
    'date', 'schedule', 'calendar',
    'am', 'pm', 'a.m', 'p.m',
    'view', 'click', 'more', 'information',
    'columbia', 'university', 'student',
]

def is_valid_food_item(text):
    """
    Check if text is likely a food item
    """
    text_lower = text.lower().strip()
    
    # Must have reasonable length
    if len(text_lower) < 3 or len(text_lower) > 80:
        return False
    
    # Check for excluded keywords
    for keyword in EXCLUDE_KEYWORDS:
        if keyword in text_lower:
            return False
    
    # Check if it's mostly numbers (dates, times, prices)
    digit_count = sum(c.isdigit() for c in text)
    if digit_count > len(text) * 0.5:
        return False
    
    # Check for time patterns (HH:MM)
    if ':' in text and any(char.isdigit() for char in text):
        return False
    
    # Check for price patterns ($X.XX)
    if '$' in text:
        return False
    
    return True

def get_meal_period_from_hours(hours_str):
    """
    Determine meal period based on opening time
    """
    if "closed" in hours_str.lower():
        return "closed"
    
    try:
        # Extract opening time
        parts = hours_str.lower().split("to")
        if len(parts) < 2:
            parts = hours_str.lower().split("-")
        
        if len(parts) < 2:
            return "lunch"
        
        start_str = parts[0].strip()
        
        # Parse hour
        hour = None
        if ":" in start_str:
            hour_part = start_str.split(":")[0].strip()
            hour = int(hour_part)
            
            # Handle AM/PM
            if "pm" in start_str and hour != 12:
                hour += 12
            elif "am" in start_str and hour == 12:
                hour = 0
        
        if hour is None:
            return "lunch"
        
        # Categorize by opening time
        if 5 <= hour < 11:
            return "breakfast"
        elif 11 <= hour < 16:
            return "lunch"
        else:
            return "dinner"
    except:
        return "lunch"

def scrape_dining_hall(hall_name, url):
    """
    Scrape a single dining hall from Columbia's official site
    """
    print(f"\n📍 Scraping {hall_name}...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"   ❌ Failed to fetch: HTTP {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find hours
        hours = "Hours not available"
        hours_elements = soup.find_all(['p', 'div', 'span'], string=lambda text: text and ('am' in text.lower() or 'pm' in text.lower()) and ('to' in text.lower() or '-' in text.lower()) if text else False)
        
        if hours_elements:
            hours = hours_elements[0].get_text().strip()
        
        # Find menu items
        food_items = []
        
        # Try different selectors for menu items
        menu_items = soup.find_all(['li', 'div', 'p'], class_=lambda x: x and ('menu' in str(x).lower() or 'item' in str(x).lower() or 'food' in str(x).lower()))
        
        if not menu_items:
            menu_section = soup.find(['div', 'section'], class_=lambda x: x and 'menu' in str(x).lower())
            if menu_section:
                menu_items = menu_section.find_all('li')
        
        current_category = "Main"
        
        for item in menu_items:
            text = item.get_text().strip()
            
            # Validate food item
            if not is_valid_food_item(text):
                continue
            
            # Check if this is a category header
            if item.name in ['h2', 'h3', 'h4', 'strong'] or 'header' in str(item.get('class', [])):
                current_category = text
                continue
            
            # Add as food item
            food_items.append({
                'name': text,
                'category': current_category
            })
        
        # Determine meal period
        meal_period = get_meal_period_from_hours(hours)
        
        print(f"   Hours: {hours}")
        print(f"   Meal: {meal_period}")
        print(f"   Items: {len(food_items)}")
        
        if food_items:
            print(f"   ✅ Found menu items")
        else:
            print(f"   ⚠️  No menu items found")
        
        return {
            'name': hall_name,
            'hours': hours,
            'meal_period': meal_period,
            'food_items': food_items
        }
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def scrape_all_halls():
    """
    Scrape all dining halls from Columbia's official site
    """
    print("\n" + "=" * 60)
    print("🦁 Columbia Official Dining Site Scraper (Filtered)")
    print("=" * 60)
    print(f"🕐 Time: {datetime.now().strftime('%I:%M %p')}")
    print("=" * 60)
    
    dining_halls = []
    
    for hall_name, url in DINING_HALL_URLS.items():
        hall_data = scrape_dining_hall(hall_name, url)
        
        if hall_data:
            dining_halls.append(hall_data)
        
        # Rate limiting
        time.sleep(0.5)
    
    return dining_halls

def save_menu_data(dining_halls):
    """Save scraped data"""
    with open('menu_data.json', 'w') as f:
        json.dump(dining_halls, f, indent=2)
    
    print("\n" + "=" * 60)
    print(f"💾 Saved menu data to menu_data.json")
    print(f"✅ Scraped {len(dining_halls)} dining halls")
    
    total_items = sum(len(hall['food_items']) for hall in dining_halls)
    open_halls = sum(1 for hall in dining_halls if hall['food_items'])
    
    print(f"📋 Total menu items: {total_items}")
    print(f"🏛️  Open halls: {open_halls}/{len(dining_halls)}")
    print("=" * 60)

if __name__ == "__main__":
    dining_halls = scrape_all_halls()
    
    if dining_halls:
        save_menu_data(dining_halls)
        print("\n🔄 Next: Run 'python3 nutrition_api.py' to add nutrition data")
    else:
        print("\n❌ No data scraped. Site structure may have changed.")