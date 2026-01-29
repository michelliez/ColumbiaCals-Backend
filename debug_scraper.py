#!/usr/bin/env python3
"""
Debug scraper to see what's happening with Hewitt, Diana, Faculty House
"""

import requests
from bs4 import BeautifulSoup

url = "https://liondine.com/?meal=lunch"

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

print("Fetching LionDine lunch data...\n")

try:
    response = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    halls = soup.find_all('div', class_='col')
    
    print(f"Found {len(halls)} halls\n")
    print("=" * 60)
    
    # Focus on the problem halls
    target_halls = ["Hewitt", "Diana", "Faculty House"]
    
    for hall in halls:
        name_tag = hall.find('h3')
        if not name_tag:
            continue
        
        hall_name = name_tag.text.strip()
        
        # Only show problem halls
        if hall_name not in target_halls:
            continue
        
        print(f"\n🏛️  {hall_name}")
        print("-" * 60)
        
        # Get hours
        hours_tag = hall.find('div', class_='hours')
        hours = hours_tag.text.strip() if hours_tag else "No hours found"
        print(f"Hours: {hours}")
        
        # Get menu div
        menu_div = hall.find('div', class_='menu')
        
        if menu_div:
            print(f"Menu div found: Yes")
            
            # Check for "No data available"
            if "No data available" in menu_div.text:
                print("Status: 'No data available' text found")
            else:
                print("Status: Menu div has content")
            
            # Find food items
            food_tags = menu_div.find_all('div', class_='food-name')
            print(f"Food items found: {len(food_tags)}")
            
            if food_tags:
                print("\nFirst 5 items:")
                for i, food_tag in enumerate(food_tags[:5]):
                    print(f"  {i+1}. {food_tag.text.strip()}")
            else:
                print("\n⚠️  No food-name divs found!")
                print("\nMenu div HTML preview:")
                print(menu_div.prettify()[:500])
        else:
            print("Menu div found: No")
            print("⚠️  No menu div with class='menu'")
        
        print("=" * 60)

except Exception as e:
    print(f"Error: {e}")