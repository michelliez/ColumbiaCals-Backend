#!/usr/bin/env python3
"""
LionDine.com All-Meals Scraper
Tries all meal periods and uses whichever has data
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

def scrape_meal_period(meal_code, meal_display):
    """Scrape a specific meal period"""
    url = f"https://liondine.com/?meal={meal_code}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            return parse_dining_halls(soup, meal_code)
    except:
        return []
    
    return []

def parse_dining_halls(soup, meal_period):
    """Parse dining halls from BeautifulSoup object"""
    dining_halls = []
    halls = soup.find_all('div', class_='col')
    
    for hall in halls:
        name_tag = hall.find('h3')
        if not name_tag:
            continue
        hall_name = name_tag.text.strip()
        
        hours_tag = hall.find('div', class_='hours')
        hours = hours_tag.text.strip() if hours_tag else "Hours not available"
        
        menu_div = hall.find('div', class_='menu')
        food_items = []
        
        if menu_div and "No data available" not in menu_div.text:
            food_tags = menu_div.find_all('div', class_='food-name')
            current_category = "Main"
            
            for food_tag in food_tags:
                food_name = food_tag.text.strip()
                
                prev_category = food_tag.find_previous_sibling('div', class_='food-type')
                if prev_category:
                    current_category = prev_category.text.strip()
                
                food_items.append({
                    'name': food_name,
                    'category': current_category
                })
        
        dining_halls.append({
            'name': hall_name,
            'hours': hours,
            'meal_period': meal_period,
            'food_items': food_items
        })
    
    return dining_halls

def merge_hall_data(all_meals_data):
    """Merge data from different meal periods, preferring ones with food"""
    merged = {}
    
    for meal_data in all_meals_data:
        for hall in meal_data:
            hall_name = hall['name']
            
            if hall_name not in merged:
                merged[hall_name] = hall
            elif len(hall['food_items']) > len(merged[hall_name]['food_items']):
                # This meal period has more items, use it
                merged[hall_name] = hall
    
    return list(merged.values())

def scrape_all_meals():
    """Scrape all meal periods"""
    print("\n" + "=" * 60)
    print("🦁 LionDine All-Meals Scraper")
    print("=" * 60)
    print(f"🕐 Time: {datetime.now().strftime('%I:%M %p')}")
    print("=" * 60)
    
    all_meals_data = []
    
    for meal_code, meal_display in [("breakfast", "Breakfast"), ("lunch", "Lunch"), ("dinner", "Dinner")]:
        print(f"\n📋 Scraping {meal_display}...")
        meal_data = scrape_meal_period(meal_code, meal_display)
        
        if meal_data:
            open_count = sum(1 for hall in meal_data if hall['food_items'])
            print(f"   Found {len(meal_data)} halls, {open_count} with menus")
            all_meals_data.append(meal_data)
    
    # Merge data
    print("\n🔀 Merging data from all meal periods...")
    merged_halls = merge_hall_data(all_meals_data)
    
    return merged_halls

def save_menu_data(dining_halls):
    """Save scraped data"""
    with open('menu_data.json', 'w') as f:
        json.dump(dining_halls, f, indent=2)
    
    print("\n" + "=" * 60)
    print(f"💾 Saved to menu_data.json")
    print("=" * 60)
    
    total_items = sum(len(hall['food_items']) for hall in dining_halls)
    open_halls = sum(1 for hall in dining_halls if hall['food_items'])
    
    print(f"\n✅ Summary:")
    print(f"   Total halls: {len(dining_halls)}")
    print(f"   Open halls: {open_halls}")
    print(f"   Total items: {total_items}")
    print("\n📋 Halls with menus:")
    for hall in dining_halls:
        if hall['food_items']:
            print(f"   - {hall['name']}: {len(hall['food_items'])} items ({hall['meal_period']})")

if __name__ == "__main__":
    dining_halls = scrape_all_meals()
    
    if dining_halls:
        save_menu_data(dining_halls)
        print("\n🔄 Next: Run 'python3 nutrition_api.py'")
    else:
        print("\n❌ No data scraped")