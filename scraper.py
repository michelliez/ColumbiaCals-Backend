#!/usr/bin/env python3
"""
LionDine.com Real Scraper
Scrapes actual dining hall menus from liondine.com
"""

import requests
from bs4 import BeautifulSoup
import json

def scrape_liondine():
    """
    Scrapes LionDine.com and returns dining hall menus
    """
    print("🔍 Scraping LionDine.com...")
    
    url = "https://liondine.com/"
    
    try:
        # Fetch the webpage
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        dining_halls = []
        
        # Find all dining halls (each is in a div with class "col")
        halls = soup.find_all('div', class_='col')
        
        print(f"Found {len(halls)} dining hall sections\n")
        
        for hall in halls:
            # Get dining hall name
            name_tag = hall.find('h3')
            if not name_tag:
                continue
            hall_name = name_tag.text.strip()
            
            # Get hours
            hours_tag = hall.find('div', class_='hours')
            hours = hours_tag.text.strip() if hours_tag else "Hours not available"
            
            # Get menu
            menu_div = hall.find('div', class_='menu')
            food_items = []
            categories = {}
            
            if menu_div:
                # Check if menu has data
                if "No data available" in menu_div.text:
                    print(f"⚠️  {hall_name}: No menu data")
                else:
                    # Get all food items
                    food_tags = menu_div.find_all('div', class_='food-name')
                    
                    # Get categories too
                    category_tags = menu_div.find_all('div', class_='food-type')
                    
                    current_category = "Main"
                    category_index = 0
                    
                    for i, food_tag in enumerate(food_tags):
                        food_name = food_tag.text.strip()
                        
                        # Figure out which category this food belongs to
                        # (This is approximate - LionDine structure makes it tricky)
                        if category_index < len(category_tags):
                            # Check if we've moved to a new category
                            category_elem = category_tags[category_index]
                            # If this food comes after the category in the HTML
                            if food_tag.find_previous_sibling('div', class_='food-type') == category_elem:
                                current_category = category_elem.text.strip()
                                category_index += 1
                        
                        food_items.append({
                            'name': food_name,
                            'category': current_category
                        })
                    
                    print(f"✅ {hall_name}: {len(food_items)} items")
            else:
                print(f"⚠️  {hall_name}: No menu section")
            
            dining_halls.append({
                'name': hall_name,
                'hours': hours,
                'food_items': food_items
            })
        
        print(f"\n✅ Total: {len(dining_halls)} dining halls scraped")
        return dining_halls
        
    except Exception as e:
        print(f"❌ Error scraping LionDine: {e}")
        import traceback
        traceback.print_exc()
        return []

def save_menu_data(dining_halls):
    """Save scraped data to JSON file"""
    with open('menu_data.json', 'w') as f:
        json.dump(dining_halls, f, indent=2)
    print("💾 Saved menu data to menu_data.json")
    
    # Also print summary
    print("\n📋 Summary:")
    for hall in dining_halls:
        print(f"   {hall['name']}: {len(hall['food_items'])} items - {hall['hours']}")

if __name__ == "__main__":
    print("=" * 60)
    print("🦁 LionDine Real Scraper")
    print("=" * 60 + "\n")
    
    dining_halls = scrape_liondine()
    
    if dining_halls:
        save_menu_data(dining_halls)
        print("\n🔄 Next step: Run 'python3 nutrition_api.py' to add nutrition data")
    else:
        print("\n❌ No data scraped. Check the error above.")