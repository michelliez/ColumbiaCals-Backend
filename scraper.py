#!/usr/bin/env python3
"""
LionDine.com Multi-Meal Scraper
Scrapes breakfast, lunch, and dinner, then intelligently matches halls to meals
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

def scrape_liondine_meal(meal_period):
    """
    Scrape LionDine for a specific meal period
    """
    print(f"🔍 Scraping {meal_period} menus...")
    
    urls_to_try = [
        f"https://liondine.com/?meal={meal_period}",
        f"https://liondine.com/{meal_period}",
        "https://liondine.com/"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    for url in urls_to_try:
        try:
            print(f"   Trying: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                halls = soup.find_all('div', class_='col')
                
                if halls and len(halls) > 0:
                    has_data = False
                    for hall in halls:
                        menu_div = hall.find('div', class_='menu')
                        if menu_div and "No data available" not in menu_div.text:
                            food_items = menu_div.find_all('div', class_='food-name')
                            if food_items:
                                has_data = True
                                break
                    
                    if has_data:
                        print(f"   ✅ Found {meal_period} data!")
                        return parse_dining_halls(soup, meal_period)
        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue
    
    print(f"   ⚠️  No {meal_period} data found")
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
        
        if food_items:
            print(f"      ✅ {hall_name}: {len(food_items)} items")
        
        dining_halls.append({
            'name': hall_name,
            'hours': hours,
            'meal_period': meal_period,
            'food_items': food_items
        })
    
    return dining_halls

def parse_hours_to_minutes(hours_str):
    """
    Parse hours like "11:00 AM to 4:00 PM" into (start_minutes, end_minutes)
    Returns None if can't parse
    """
    if "closed" in hours_str.lower():
        return None
    
    parts = hours_str.lower().split("to")
    if len(parts) != 2:
        return None
    
    try:
        start_str = parts[0].strip()
        end_str = parts[1].strip()
        
        start_mins = parse_time_to_minutes(start_str)
        end_mins = parse_time_to_minutes(end_str)
        
        if start_mins is not None and end_mins is not None:
            return (start_mins, end_mins)
    except:
        pass
    
    return None

def parse_time_to_minutes(time_str):
    """Parse '11:00 AM' to minutes since midnight"""
    try:
        parts = time_str.split(":")
        if len(parts) != 2:
            return None
        
        hour = int(parts[0].strip())
        min_part = parts[1].strip().split()[0]
        minutes = int(min_part)
        
        is_pm = "pm" in time_str.lower()
        
        if is_pm and hour != 12:
            hour += 12
        elif not is_pm and hour == 12:
            hour = 0
        
        return hour * 60 + minutes
    except:
        return None

def get_meal_period_from_hours(hours_str):
    """
    Determine which meal period this hall is serving based on its hours
    """
    time_range = parse_hours_to_minutes(hours_str)
    if not time_range:
        return None
    
    start, end = time_range
    
    # Breakfast: typically 5 AM - 11 AM (300 - 660 minutes)
    if start >= 300 and start < 660:
        return "breakfast"
    
    # Lunch: typically 11 AM - 4 PM (660 - 960 minutes)
    if start >= 660 and start < 960:
        return "lunch"
    
    # Dinner: typically 4 PM onwards (960+ minutes)
    if start >= 960:
        return "dinner"
    
    # Default to dinner for late hours
    return "dinner"

def scrape_all_meals():
    """
    Scrape all three meal periods and combine intelligently
    """
    print("\n" + "=" * 60)
    print("🦁 LionDine Multi-Meal Scraper")
    print("=" * 60)
    print(f"🕐 Time: {datetime.now().strftime('%I:%M %p')}")
    print("=" * 60)
    
    # Scrape all three meals
    breakfast_halls = scrape_liondine_meal("breakfast")
    lunch_halls = scrape_liondine_meal("lunch")
    dinner_halls = scrape_liondine_meal("dinner")
    
    # Create lookup by hall name
    all_meals = {
        'breakfast': {h['name']: h for h in breakfast_halls},
        'lunch': {h['name']: h for h in lunch_halls},
        'dinner': {h['name']: h for h in dinner_halls}
    }
    
    # Get all unique hall names
    all_hall_names = set()
    for meal_halls in [breakfast_halls, lunch_halls, dinner_halls]:
        for hall in meal_halls:
            all_hall_names.add(hall['name'])
    
    # Match each hall to the right meal based on hours
    final_halls = []
    
    for hall_name in all_hall_names:
        # Try to find this hall in each meal period
        hall_data = None
        
        # Check all three meals for this hall
        for meal in ['breakfast', 'lunch', 'dinner']:
            if hall_name in all_meals[meal]:
                candidate = all_meals[meal][hall_name]
                
                # Determine which meal this hall is actually serving based on hours
                inferred_meal = get_meal_period_from_hours(candidate['hours'])
                
                # If the scraped meal matches the inferred meal, use it
                if inferred_meal == meal:
                    hall_data = candidate
                    break
                
                # Otherwise, keep as fallback
                if hall_data is None:
                    hall_data = candidate
        
        if hall_data:
            final_halls.append(hall_data)
    
    print("\n" + "=" * 60)
    print(f"📋 Combined Menu Summary:")
    total_items = 0
    for hall in final_halls:
        items = len(hall['food_items'])
        total_items += items
        meal = hall.get('meal_period', 'unknown')
        status = f"{items} items ({meal})" if items > 0 else "Closed"
        print(f"   {hall['name']}: {status}")
    
    print(f"\n✅ Total: {len(final_halls)} halls, {total_items} menu items")
    
    return final_halls

def save_menu_data(dining_halls):
    """Save scraped data"""
    with open('menu_data.json', 'w') as f:
        json.dump(dining_halls, f, indent=2)
    
    print("\n" + "=" * 60)
    print(f"💾 Saved menu data to menu_data.json")
    print("=" * 60)

if __name__ == "__main__":
    dining_halls = scrape_all_meals()
    
    if dining_halls:
        save_menu_data(dining_halls)
        print("\n🔄 Next: Run 'python3 nutrition_api.py' to add nutrition data")
    else:
        print("\n❌ No data scraped. LionDine might be down or structure changed.")