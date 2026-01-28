#!/usr/bin/env python3
"""
Columbia Dining Scraper - Selenium Version with Filtering
Scrapes from dining.columbia.edu and filters out non-food items
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
from datetime import datetime
import time

# ALL 14 Dining Locations on Columbia's site
DINING_HALL_URLS = {
    # Main Dining Halls
    "John Jay": "https://dining.columbia.edu/content/john-jay-dining-hall",
    "Ferris": "https://dining.columbia.edu/content/ferris-booth-commons",
    "JJ's": "https://dining.columbia.edu/content/jjs-place",
    "Grace Dodge": "https://dining.columbia.edu/content/grace-dodge-dining-hall",
    "Fac Shack": "https://dining.columbia.edu/content/fac-shack",
    "Chef Mike's": "https://dining.columbia.edu/content/chef-mikes-sub-shop",
    
    # Faculty/Additional Halls
    "Faculty House": "https://dining.columbia.edu/content/faculty-house",
    "Robert F. Smith": "https://dining.columbia.edu/content/robert-f-smith-dining-hall",
    "Chef Don's": "https://dining.columbia.edu/content/chef-dons-pizza-pi",
    "Johnny's": "https://dining.columbia.edu/content/johnnys-cafe",
    
    # Blue Java Cafés
    "Blue Java Butler": "https://dining.columbia.edu/content/blue-java-cafe-butler-library",
    "Blue Java Everett": "https://dining.columbia.edu/content/blue-java-everett-library-cafe",
    "Blue Java Uris": "https://dining.columbia.edu/content/blue-java-cafe-uris",
    "Lenfest Café": "https://dining.columbia.edu/content/lenfest-cafe",
}

# Words/phrases to exclude (not food items)
EXCLUDE_KEYWORDS = [
    'hour', 'hours', 'time', 'open', 'close', 'closed',
    'location', 'address', 'phone', 'contact',
    'menu', 'today', 'tomorrow', 
    'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
    'breakfast', 'lunch', 'dinner', 'brunch',
    'flex', 'dollar', 'dining', 'meal', 'plan', 'swipe',
    'copyright', 'privacy', 'terms', 'policy',
    'date', 'schedule', 'calendar',
    'week', 'month', 'year',
    'message', 'announcement', 'notice',
    'staff', 'feature', 'special event',
    'night', 'day', 'celebration',
    'deal', 'located', 'location', 'exchange', 'payable', 'change',
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
    
    # Check for date patterns (MM/DD, 1/27, etc)
    if '/' in text and any(char.isdigit() for char in text):
        return False
    
    # Check for price patterns ($X.XX)
    if '$' in text:
        return False
    
    # Skip if ALL CAPS (likely title/announcement)
    if text.isupper() and len(text) > 10:
        return False
    
    return True

def get_meal_period_from_hours(hours_str):
    """Determine meal period based on opening time"""
    if "closed" in hours_str.lower():
        return "closed"
    
    try:
        parts = hours_str.lower().split("to")
        if len(parts) < 2:
            parts = hours_str.lower().split("-")
        
        if len(parts) < 2:
            return "lunch"
        
        start_str = parts[0].strip()
        
        hour = None
        if ":" in start_str:
            hour_part = start_str.split(":")[0].strip()
            try:
                hour = int(hour_part)
            except:
                return "lunch"
            
            if "pm" in start_str and hour != 12:
                hour += 12
            elif "am" in start_str and hour == 12:
                hour = 0
        
        if hour is None:
            return "lunch"
        
        if 5 <= hour < 11:
            return "breakfast"
        elif 11 <= hour < 16:
            return "lunch"
        else:
            return "dinner"
    except:
        return "lunch"

def setup_driver():
    """Setup Chrome driver with headless options"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def scrape_dining_hall(hall_name, url, driver):
    """Scrape a single dining hall"""
    print(f"\n📍 Scraping {hall_name}...")
    
    try:
        driver.get(url)
        
        # Wait for Angular to load the menu items
        time.sleep(4)  # Give Angular time to render
        
        # Find hours
        hours = "Hours not available"
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            lines = body_text.split('\n')
            for line in lines:
                if ('am' in line.lower() or 'pm' in line.lower()) and ':' in line:
                    if 'to' in line.lower() or '-' in line:
                        hours = line.strip()
                        break
        except:
            pass
        
        # Find food items using the Angular class we identified
        food_items = []
        current_category = "Main"
        
        try:
            # Wait for meal items to appear
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "meal-title"))
            )
            
            # Find all meal titles
            meal_elements = driver.find_elements(By.CLASS_NAME, "meal-title")
            
            print(f"   Found {len(meal_elements)} potential items")
            
            for element in meal_elements:
                try:
                    food_name = element.text.strip()
                    
                    # Validate that this is actually a food item
                    if food_name and is_valid_food_item(food_name):
                        food_items.append({
                            'name': food_name,
                            'category': current_category
                        })
                    else:
                        print(f"   ⚠️  Filtered out: {food_name}")
                except:
                    continue
                    
        except Exception as e:
            print(f"   ⚠️  No menu items found (hall may be closed)")
        
        meal_period = get_meal_period_from_hours(hours)
        
        print(f"   Hours: {hours}")
        print(f"   Meal: {meal_period}")
        print(f"   Valid food items: {len(food_items)}")
        
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
    """Scrape all 14 halls using Selenium"""
    print("\n" + "=" * 60)
    print("🦁 Columbia Dining Scraper (Selenium - Filtered)")
    print("=" * 60)
    print(f"🕐 Time: {datetime.now().strftime('%I:%M %p')}")
    print("=" * 60)
    
    print("\n🌐 Starting Chrome browser...")
    driver = setup_driver()
    
    dining_halls = []
    
    try:
        for hall_name, url in DINING_HALL_URLS.items():
            hall_data = scrape_dining_hall(hall_name, url, driver)
            
            if hall_data:
                dining_halls.append(hall_data)
            
            time.sleep(1)  # Rate limiting
    finally:
        driver.quit()
        print("\n🔒 Browser closed")
    
    return dining_halls

def save_menu_data(dining_halls):
    """Save scraped data"""
    with open('menu_data.json', 'w') as f:
        json.dump(dining_halls, f, indent=2)
    
    print("\n" + "=" * 60)
    print(f"💾 Saved to menu_data.json")
    print(f"✅ Scraped {len(dining_halls)} locations")
    
    total_items = sum(len(hall['food_items']) for hall in dining_halls)
    open_halls = sum(1 for hall in dining_halls if hall['food_items'])
    
    print(f"📋 Total food items: {total_items}")
    print(f"🏛️  Open locations: {open_halls}/{len(dining_halls)}")
    print("=" * 60)

if __name__ == "__main__":
    dining_halls = scrape_all_halls()
    
    if dining_halls:
        save_menu_data(dining_halls)
        print("\n🔄 Next: Run 'python3 nutrition_api.py'")
    else:
        print("\n❌ No data scraped")
