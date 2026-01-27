#!/usr/bin/env python3
"""
LionDine Multi-Meal Scraper with Smart Time-Aware Matching
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

def get_current_meal_period():
    """Determine current meal period based on time"""
    now = datetime.now()
    hour = now.hour
    
    if 5 <= hour < 11:
        return "breakfast"
    elif 11 <= hour < 16:
        return "lunch"
    else:
        return "dinner"

def scrape_liondine_meal(meal_period):
    """Scrape LionDine for a specific meal period"""
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

def hall_matches_time_period(hours_str, target_period):
    """
    Check if a hall's hours match the target meal period
    Returns True if the hall serves during this period
    """
    if "closed" in hours_str.lower():
        return False
    
    # Parse hours like "11:00 AM to 4:00 PM"
    parts = hours_str.lower().split("to")
    if len(parts) != 2:
        return False
    
    try:
        start_str = parts[0].strip()
        start_hour = parse_hour_from_string(start_str)
        
        if start_hour is None:
            return False
        
        # Breakfast: 5 AM - 11 AM starts
        if target_period == "breakfast":
            return 5 <= start_hour < 11
        
        # Lunch: 11 AM - 4 PM starts  
        elif target_period == "lunch":
            return 11 <= start_hour < 16
        
        # Dinner: 4 PM onwards starts
        elif target_period == "dinner":
            return start_hour >= 16
        
    except:
        pass
    
    return False

def parse_hour_from_string(time_str):
    """Parse hour from '11:00 AM' format"""
    try:
        parts = time_str.split(":")
        if len(parts) != 2:
            return None
        
        hour = int(parts[0].strip())
        is_pm = "pm" in time_str.lower()
        
        if is_pm and hour != 12:
            hour += 12
        elif not is_pm and hour == 12:
            hour = 0
        
        return hour
    except:
        return None

def scrape_all_meals():
    """Scrape all three meal periods and intelligently combine"""
    print("\n" + "=" * 60)
    print("🦁 LionDine Smart Multi-Meal Scraper")
    print("=" * 60)
    
    current_time = datetime.now().strftime('%I:%M %p')
    current_period = get_current_meal_period()
    
    print(f"🕐 Current time: {current_time}")
    print(f"🍽️  Current period: {current_period}")
    print("=" * 60)
    
    # Scrape all three meals
    breakfast_halls = scrape_liondine_meal("breakfast")
    lunch_halls = scrape_liondine_meal("lunch")
    dinner_halls = scrape_liondine_meal("dinner")
    
    # Create master list organized by hall name
    all_halls = {}
    
    # Add all halls from each meal
    for meal, halls in [("breakfast", breakfast_halls), ("lunch", lunch_halls), ("dinner", dinner_halls)]:
        for hall in halls:
            hall_name = hall['name']
            
            if hall_name not in all_halls:
                all_halls[hall_name] = {}
            
            all_halls[hall_name][meal] = hall
    
    # For each hall, pick the right meal based on its hours
    final_halls = []
    
    for hall_name, meals in all_halls.items():
        chosen_hall = None
        
        # Try to find the hall version that matches current time period
        if current_period in meals:
            candidate = meals[current_period]
            if hall_matches_time_period(candidate['hours'], current_period):
                chosen_hall = candidate
        
        # If no match for current period, try other periods
        if not chosen_hall:
            for period in ["breakfast", "lunch", "dinner"]:
                if period in meals:
                    candidate = meals[period]
                    if hall_matches_time_period(candidate['hours'], period):
                        chosen_hall = candidate
                        break
        
        # Fallback: use any version we have
        if not chosen_hall and meals:
            chosen_hall = list(meals.values())[0]
        
        if chosen_hall:
            final_halls.append(chosen_hall)
    
    print("\n" + "=" * 60)
    print(f"📋 Combined Menu Summary (showing {current_period}):")
    
    total_items = 0
    for hall in final_halls:
        items = len(hall['food_items'])
        total_items += items
        meal = hall.get('meal_period', 'unknown')
        status = f"{items} items ({meal})" if items > 0 else "Closed"
        print(f"   {hall['name']}: {status} - {hall['hours']}")
    
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