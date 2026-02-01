#!/usr/bin/env python3
"""
Columbia & Barnard Dining Scraper - Unified
Handles both Columbia (HTML JSON) and Barnard (API JSON)
"""

import requests
import json
import re
from datetime import datetime

# Columbia Dining Halls (dining.columbia.edu)
COLUMBIA_LOCATIONS = [
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

# Barnard Dining Halls (Dine On Campus API)
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

def scrape_columbia_hall(location):
    """Scrape a Columbia dining hall"""
    url = f"https://dining.columbia.edu/content/{location}"
    
    try:
        headers = {
            'User-Agent': 'CalRoarie-Student-App/1.3 (nutrition tracker for Columbia students)'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        menu_data = extract_menu_data(response.text)
        
        if not menu_data:
            return {
                "name": location.replace("-", " ").title(),
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
            "name": location.replace("-", " ").title(),
            "food_items": sorted(list(food_items)),
            "source": "columbia",
            "scraped_at": datetime.now().isoformat()
        }
    
    except Exception as e:
        print(f"❌ Error scraping Columbia {location}: {e}")
        return {
            "name": location.replace("-", " ").title(),
            "food_items": [],
            "source": "columbia",
            "error": str(e)
        }

def scrape_barnard_hall(hall):
    """Scrape a Barnard dining hall via Dine On Campus API"""
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://apiv4.dineoncampus.com/locations/{hall['location_id']}/menu"
    
    params = {
        "date": today,
        "period": hall['period_id']
    }
    
    try:
        headers = {
            'User-Agent': 'CalRoarie-Student-App/1.3 (nutrition tracker for Columbia students)'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract food items from Barnard API format
        food_items = set()
        
        # Barnard API structure: periods -> categories -> items
        periods = data.get('menu', {}).get('periods', {})
        
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
    for location in COLUMBIA_LOCATIONS:
        print(f"   {location}...")
        data = scrape_columbia_hall(location)
        results.append(data)
        print(f"      ✅ Found {len(data['food_items'])} food items")
    
    # Scrape Barnard halls
    print("\n📍 Scraping Barnard halls...")
    for hall in BARNARD_LOCATIONS:
        print(f"   {hall['name']}...")
        data = scrape_barnard_hall(hall)
        results.append(data)
        print(f"      ✅ Found {len(data['food_items'])} food items")
    
    # Save results
    with open('menu_data.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    total_items = sum(len(r['food_items']) for r in results)
    
    print(f"\n✅ Scraped {len(results)} locations")
    print(f"📊 Total: {total_items} food items")
    print(f"📄 Saved to menu_data.json")
    
    return results

if __name__ == "__main__":
    scrape_all_locations()