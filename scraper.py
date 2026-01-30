#!/usr/bin/env python3
"""
Columbia Dining Scraper (Selenium - Filtered)
Scrapes dining.columbia.edu with JavaScript support
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time
from datetime import datetime

DINING_LOCATIONS = [
    "john-jay",
    "ferris-booth-commons",
    "jjs-place",
    "grace-dodge",
    "faculty-house",
    "hewitt",
    "diana-center",
    "fac-shack",
    "chef-mikes",
    "chef-dons-pizza-pi",
    "robert-f-smith",
    "blue-java-butler",
    "blue-java-uris",
    "lenfest-cafe"
]

# Keywords to filter out non-food items
EXCLUSION_KEYWORDS = [
    'hours', 'hour', 'closed', 'open', 'date', 'time',
    'january', 'february', 'march', 'april', 'may', 'june',
    'july', 'august', 'september', 'october', 'november', 'december',
    'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
    'announcement', 'notice', 'information'
]

def is_food_item(text):
    """Filter out non-food items based on keywords"""
    text_lower = text.lower().strip()
    
    # Filter out empty or very short items
    if len(text_lower) < 3:
        return False
    
    # Filter out items containing exclusion keywords
    for keyword in EXCLUSION_KEYWORDS:
        if keyword in text_lower:
            return False
    
    return True

def scrape_dining_hall(location):
    """Scrape a single dining hall using Selenium"""
    url = f"https://dining.columbia.edu/content/{location}"
    
    # Setup Chrome options - OPTIMIZED FOR LOW MEMORY
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-software-rasterizer')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-logging')
    chrome_options.add_argument('--disable-features=VizDisplayCompositor')
    chrome_options.add_argument('--single-process')  # CRITICAL for low memory
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--window-size=1920,1080')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        
        driver.get(url)
        time.sleep(3)  # Reduced from 4
        
        # Rest of your code...
        food_elements = driver.find_elements(By.CLASS_NAME, "meal-title")
        
        food_items = []
        for element in food_elements:
            text = element.text.strip()
            if text and is_food_item(text):
                food_items.append(text)
        
        driver.quit()  # IMPORTANT: Close immediately
        
        return {
            "name": location.replace("-", " ").title(),
            "food_items": food_items,
            "scraped_at": datetime.now().isoformat()
        }
    
    except Exception as e:
        print(f"❌ Error scraping {location}: {e}")
        try:
            driver.quit()  # Make sure to close on error
        except:
            pass
        return {
            "name": location.replace("-", " ").title(),
            "food_items": [],
            "error": str(e)
        }

def scrape_all_locations():
    """Scrape all dining locations"""
    print("🦁 Columbia Dining Scraper (Selenium - Filtered)")
    print("=" * 50)
    
    results = []
    
    print("🌐 Starting Chrome browser...")
    
    for location in DINING_LOCATIONS:
        print(f"📍 Scraping {location}...")
        data = scrape_dining_hall(location)
        results.append(data)
        print(f"   ✅ Found {len(data['food_items'])} food items")
        time.sleep(2)  # Be nice to the server
    
    # Save results
    with open('menu_data.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Scraped {len(results)} locations")
    print(f"📄 Saved to menu_data.json")
    
    return results

if __name__ == "__main__":
    scrape_all_locations()