#!/usr/bin/env python3
"""
LionDine.com Simple Time-Aware Scraper
Only scrapes the current meal period based on time
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
        return "breakfast", "🌅 Breakfast"
    elif 11 <= hour < 16:
        return "lunch", "🌞 Lunch"
    else:
        return "dinner", "🌙 Dinner"

def scrape_liondine():
    """Main scraping function - only scrapes current meal period"""
    meal_code, meal_display = get_current_meal_period()
    current_time = datetime.now().strftime('%I:%M %p')
    
    print("=" * 60)
    print("🦁 LionDine Simple Scraper")
    print("=" * 60)
    print(f"🕐 Current time: {current_time}")
    print(f"🍽️  Scraping: {meal_display}")
    print("=" * 60)
    
    # Try different URL patterns
    urls_to_try = [
        f"https://liondine.com/?meal={meal_code}",
        f"https://liondine.com/{meal_code}",
        "https://liondine.com/"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    for url in urls_to_try:
        try:
            print(f"\n🔍 Trying: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                halls = soup.find_all('div', class_='col')
                
                if halls and len(halls) > 0:
                    # Check if any halls have menu data
                    has_data = False
                    for hall in halls:
                        menu_div = hall.find('div', class_='menu')
                        if menu_div and "No data available" not in menu_div.text:
                            food_items = menu_div.find_all('div', class_='food-name')
                            if food_items:
                                has_data = True
                                break
                    
                    if has_data:
                        print(f"   ✅ Found {meal_display} data!")
                        return parse_dining_halls(soup, meal_code)
                    else:
                        print(f"   ⚠️  No menu data on this page")
            else:
                print(f"   ❌ HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue
    
    print(f"\n❌ Could not find {meal_display} menus")
    return []

def parse_dining_halls(soup, meal_period):
    """Parse dining halls from BeautifulSoup object"""
    dining_halls = []
    halls = soup.find_all('div', class_='col')
    
    print(f"\n📋 Parsing dining halls:")
    
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
                
                # Find category
                prev_category = food_tag.find_previous_sibling('div', class_='food-type')
                if prev_category:
                    current_category = prev_category.text.strip()
                
                food_items.append({
                    'name': food_name,
                    'category': current_category
                })
        
        status = f"{len(food_items)} items" if food_items else "Closed"
        print(f"   {hall_name}: {status} - {hours}")
        
        dining_halls.append({
            'name': hall_name,
            'hours': hours,
            'meal_period': meal_period,
            'food_items': food_items
        })
    
    return dining_halls

def save_menu_data(dining_halls):
    """Save scraped data"""
    with open('menu_data.json', 'w') as f:
        json.dump(dining_halls, f, indent=2)
    
    meal_period = dining_halls[0].get('meal_period', 'unknown') if dining_halls else 'unknown'
    
    print("\n" + "=" * 60)
    print(f"💾 Saved {meal_period.upper()} menu data to menu_data.json")
    print("=" * 60)
    
    total_items = sum(len(hall['food_items']) for hall in dining_halls)
    open_halls = sum(1 for hall in dining_halls if hall['food_items'])
    
    print(f"\n✅ Summary:")
    print(f"   Total halls: {len(dining_halls)}")
    print(f"   Open halls: {open_halls}")
    print(f"   Total items: {total_items}")

if __name__ == "__main__":
    dining_halls = scrape_liondine()
    
    if dining_halls:
        save_menu_data(dining_halls)
        print("\n🔄 Next: Run 'python3 nutrition_api.py' to add nutrition data")
    else:
        print("\n❌ No data scraped. LionDine might be down or structure changed.")
        print("💡 Try visiting https://liondine.com/ manually to check.")