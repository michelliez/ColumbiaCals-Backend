#!/usr/bin/env python3
"""
Columbia & Barnard Dining Scraper - Separate Barnard Halls
"""

import requests
import json
import re
from datetime import datetime
import time
from bs4 import BeautifulSoup

# Columbia Dining Halls (CORRECT URLs)
COLUMBIA_LOCATIONS = [
    {"name": "John Jay Dining Hall", "url": "https://dining.columbia.edu/content/john-jay-dining-hall"},
    {"name": "Ferris Booth Commons", "url": "https://dining.columbia.edu/content/ferris-booth-commons-0"},
    {"name": "JJ's Place", "url": "https://dining.columbia.edu/content/jjs-place-0"},
    {"name": "Grace Dodge", "url": "https://dining.columbia.edu/content/grace-dodge-dining-hall-0"},
    {"name": "Faculty House 2nd Floor", "url": "https://dining.columbia.edu/content/faculty-house-2nd-floor-0"},
    {"name": "Faculty House Skyline", "url": "https://dining.columbia.edu/content/faculty-house-4th-floor-skyline-room"},
    {"name": "Robert F. Smith", "url": "https://dining.columbia.edu/content/robert-f-smith-dining-hall-0"},
    {"name": "Blue Java Butler", "url": "https://dining.columbia.edu/content/blue-java-cafe-butler-library-0"},
    {"name": "Blue Java Uris", "url": "https://dining.columbia.edu/content/blue-java-cafe-uris-hall"},
    {"name": "Blue Java Mudd", "url": "https://dining.columbia.edu/content/blue-java-cafe-mudd-hall-0"},
    {"name": "Blue Java Everett", "url": "https://dining.columbia.edu/content/blue-java-everett-library-cafe"},
    {"name": "Lenfest Cafe", "url": "https://dining.columbia.edu/content/lenfest-cafe-0"},
    {"name": "Fac Shack", "url": "https://dining.columbia.edu/content/fac-shack-0"},
    {"name": "Chef Mike's", "url": "https://dining.columbia.edu/chef-mikes"},
    {"name": "Johnny's", "url": "https://dining.columbia.edu/johnnys"}
]

# Barnard Dining Halls (DineOnCampus API)
BARNARD_LOCATIONS = [
    {
        "name": "Hewitt Dining Hall",
        "location_id": "5d27a0461ca48e0aca2a104c",
        "period_id": "697fa349771598a5a6eb2f3e"
    },
    {
        "name": "Diana Center",
        "location_id": "5d27a073e5be796ca46a93f9",
        "period_id": "697fa349771598a5a6eb2f3e"
    },
    {
        "name": "Liz's Place",
        "location_id": "5d27a0c31ca48e0aca2a104d",
        "period_id": "697fa349771598a5a6eb2f3e"
    }
]

def extract_menu_data(html):
    """Extract menu_data JSON from Columbia HTML"""
    pattern = r'var menu_data = `(.+?)`;'
    match = re.search(pattern, html, re.DOTALL)
    
    if not match:
        return None
    
    json_str = match.group(1)
    
    try:
        menu_data = json.loads(json_str)
        return menu_data
    except json.JSONDecodeError as e:
        print(f"❌ JSON parse error: {e}")
        return None

def scrape_columbia_hall(hall):
    """Scrape a Columbia dining hall"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://dining.columbia.edu/',
            'Cache-Control': 'max-age=0'
        }
        
        response = requests.get(hall['url'], headers=headers, timeout=30)
        response.raise_for_status()
        
        menu_data = extract_menu_data(response.text)
        
        if not menu_data:
            return {
                "name": hall['name'],
                "food_items": [],
                "source": "columbia",
                "scraped_at": datetime.now().isoformat()
            }
        
        # Extract food items
        food_items = set()
        
        for menu in menu_data:
            date_ranges = menu.get('date_range_fields', [])
            for date_range in date_ranges:
                stations = date_range.get('stations', [])
                for station in stations:
                    meals = station.get('meals_paragraph', [])
                    for meal in meals:
                        title = meal.get('title', '').strip()
                        if title and len(title) > 2:
                            food_items.add(title)
        
        return {
            "name": hall['name'],
            "food_items": sorted(list(food_items)),
            "source": "columbia",
            "scraped_at": datetime.now().isoformat()
        }
    
    except Exception as e:
        print(f"❌ Error scraping {hall['name']}: {e}")
        return {
            "name": hall['name'],
            "food_items": [],
            "source": "columbia",
            "error": str(e)
        }

def scrape_barnard_hall(hall):
    """Scrape a Barnard dining hall via DineOnCampus API"""
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://apiv4.dineoncampus.com/locations/{hall['location_id']}/menu"
    
    params = {
        "date": today,
        "period": hall['period_id']
    }
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Origin': 'https://barnard.dineoncampus.com',
            'Referer': 'https://barnard.dineoncampus.com/'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract food items from Barnard API format
        food_items = set()
        
        # Barnard API structure: menu -> periods -> categories -> items
        menu = data.get('menu', {})
        periods = menu.get('periods', {})
        
        for period_name, period_data in periods.items():
            categories = period_data.get('categories', [])
            for category in categories:
                items = category.get('items', [])
                for item in items:
                    name = item.get('name', '').strip()
                    if name and len(name) > 2:
                        food_items.add(name)
        
        return {
            "name": hall['name'],
            "food_items": sorted(list(food_items)),
            "source": "barnard",
            "scraped_at": datetime.now().isoformat()
        }
    
    except Exception as e:
        print(f"❌ Error scraping Barnard {hall['name']}: {e}")
        return {
            "name": hall['name'],
            "food_items": [],
            "source": "barnard",
            "error": str(e)
        }

def scrape_all_locations():
    """Scrape all Columbia and Barnard dining locations"""
    print("🦁 Columbia & Barnard Dining Scraper")
    print("=" * 50)
    
    results = []
    
    # Scrape Columbia halls
    print("\n📍 Scraping Columbia halls...")
    for hall in COLUMBIA_LOCATIONS:
        print(f"   {hall['name']}...")
        data = scrape_columbia_hall(hall)
        results.append(data)
        print(f"      ✅ Found {len(data['food_items'])} food items")
        time.sleep(1)  # Wait 1 second between requests
    
    # Scrape Barnard halls
    print("\n📍 Scraping Barnard halls...")
    for hall in BARNARD_LOCATIONS:
        print(f"   {hall['name']}...")
        data = scrape_barnard_hall(hall)
        results.append(data)
        print(f"      ✅ Found {len(data['food_items'])} food items")
        time.sleep(1)  # Wait 1 second between requests
    
    # Save results
    with open('menu_data.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    total_items = sum(len(r['food_items']) for r in results)
    
    print(f"\n✅ Scraped {len(results)} locations")
    print(f"   Columbia: {len(COLUMBIA_LOCATIONS)} halls")
    print(f"   Barnard: {len(BARNARD_LOCATIONS)} halls")
    print(f"📊 Total: {total_items} food items")
    print(f"📄 Saved to menu_data.json")
    
    return results

if __name__ == "__main__":
    scrape_all_locations()