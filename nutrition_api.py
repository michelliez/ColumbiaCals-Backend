#!/usr/bin/env python3
"""
USDA Nutrition API Integration - More Robust Version
Adds nutrition data to menu items with better error handling
"""

import requests
import json
import time

USDA_API_KEY = "DEMO_KEY"  # Using demo key (limited to 30 requests/hour)
USDA_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

# Manual overrides for common foods
NUTRITION_OVERRIDES = {
    "tacos": {"calories": 210, "protein": 9, "carbs": 13, "fat": 13, "sodium": 450},
    "pizza": {"calories": 285, "protein": 12, "carbs": 36, "fat": 10, "sodium": 640},
    "burger": {"calories": 354, "protein": 20, "carbs": 30, "fat": 16, "sodium": 497},
    "hamburger": {"calories": 354, "protein": 20, "carbs": 30, "fat": 16, "sodium": 497},
    "burrito": {"calories": 400, "protein": 18, "carbs": 50, "fat": 14, "sodium": 900},
    "quesadilla": {"calories": 380, "protein": 16, "carbs": 35, "fat": 18, "sodium": 750},
    "chicken": {"calories": 165, "protein": 31, "carbs": 0, "fat": 3.6, "sodium": 74},
    "rice": {"calories": 130, "protein": 2.7, "carbs": 28, "fat": 0.3, "sodium": 1},
    "pasta": {"calories": 131, "protein": 5, "carbs": 25, "fat": 1.3, "sodium": 1},
    "salad": {"calories": 33, "protein": 2.8, "carbs": 6.3, "fat": 0.2, "sodium": 89},
    "fries": {"calories": 312, "protein": 3.4, "carbs": 41, "fat": 15, "sodium": 210},
    "sandwich": {"calories": 250, "protein": 12, "carbs": 30, "fat": 8, "sodium": 500},
}

def get_nutrition_from_override(food_name):
    """Check if food has manual override"""
    food_lower = food_name.lower()
    for key, nutrition in NUTRITION_OVERRIDES.items():
        if key in food_lower:
            print(f"      Using override for: {food_name}")
            return nutrition
    return None

def search_usda_food(food_name, retries=2):
    """Search USDA database for food with retries"""
    # Check overrides first
    override = get_nutrition_from_override(food_name)
    if override:
        return override
    
    for attempt in range(retries):
        try:
            params = {
                "query": food_name,
                "pageSize": 20,
                "api_key": USDA_API_KEY,
                "dataType": ["Survey (FNDDS)", "Foundation", "SR Legacy"]
            }
            
            response = requests.get(USDA_SEARCH_URL, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('foods'):
                    # Get best match
                    best_food = None
                    best_score = 0
                    
                    for food in data['foods'][:10]:
                        score = calculate_match_score(food_name, food)
                        if score > best_score:
                            best_score = score
                            best_food = food
                    
                    if best_food:
                        return extract_nutrition(best_food)
            
            elif response.status_code == 429:
                # Rate limited
                print(f"      Rate limited, waiting {5 * (attempt + 1)}s...")
                time.sleep(5 * (attempt + 1))
                continue
            
            # If we get here, no good results
            return get_default_nutrition()
            
        except requests.exceptions.Timeout:
            print(f"      Timeout (attempt {attempt + 1}/{retries})")
            if attempt < retries - 1:
                time.sleep(2)
            continue
        except Exception as e:
            print(f"      Error: {str(e)[:50]}")
            if attempt < retries - 1:
                time.sleep(2)
            continue
    
    # All retries failed
    return get_default_nutrition()

def calculate_match_score(query, food_item):
    """Score how well a USDA food matches the query"""
    score = 0
    query_lower = query.lower()
    food_name = food_item.get('description', '').lower()
    
    # Exact match bonus
    if query_lower == food_name:
        score += 100
    
    # Partial match
    if query_lower in food_name or food_name in query_lower:
        score += 50
    
    # Prefer Survey/FNDDS data
    if food_item.get('dataType') == 'Survey (FNDDS)':
        score += 30
    
    # Get nutrition data
    nutrients = {n['nutrientId']: n.get('value', 0) for n in food_item.get('foodNutrients', [])}
    calories = nutrients.get(1008, 0)  # Energy
    protein = nutrients.get(1003, 0)   # Protein
    
    # Reasonable calorie range
    if 50 <= calories <= 1000:
        score += 20
    
    # Has protein data
    if protein > 0:
        score += 10
    
    # Filter unrealistic values
    if calories < 5 or calories > 2000:
        score -= 50
    
    return score

def extract_nutrition(food_item):
    """Extract nutrition from USDA food item"""
    nutrients = {n['nutrientId']: n.get('value', 0) for n in food_item.get('foodNutrients', [])}
    
    nutrition = {
        'calories': round(nutrients.get(1008, 0)),      # Energy (kcal)
        'protein': round(nutrients.get(1003, 0), 1),    # Protein (g)
        'carbs': round(nutrients.get(1005, 0), 1),      # Carbohydrates (g)
        'fat': round(nutrients.get(1004, 0), 1),        # Fat (g)
        'sodium': round(nutrients.get(1093, 0))         # Sodium (mg)
    }
    
    # Validate
    if nutrition['calories'] < 5:
        return get_default_nutrition()
    
    return nutrition

def get_default_nutrition():
    """Return default nutrition when API fails"""
    return {
        'calories': 150,
        'protein': 5,
        'carbs': 20,
        'fat': 5,
        'sodium': 200
    }

def add_nutrition_to_menu():
    """Main function to add nutrition data"""
    print("\n" + "=" * 60)
    print("🥗 Adding Nutrition Data")
    print("=" * 60)
    
    # Load menu data
    try:
        with open('menu_data.json', 'r') as f:
            dining_halls = json.load(f)
    except FileNotFoundError:
        print("❌ menu_data.json not found. Run scraper first.")
        return
    
    total_items = 0
    processed_items = 0
    
    for hall in dining_halls:
        hall_name = hall['name']
        food_items = hall.get('food_items', [])
        
        if not food_items:
            print(f"\n🏛️  {hall_name}: No items (closed)")
            continue
        
        print(f"\n🏛️  {hall_name}: {len(food_items)} items")
        
        items_with_nutrition = []
        
        for i, item in enumerate(food_items):
            food_name = item['name']
            total_items += 1
            
            # Progress indicator
            if i % 10 == 0 and i > 0:
                print(f"   Progress: {i}/{len(food_items)}")
            
            # Get nutrition
            nutrition = search_usda_food(food_name)
            
            if nutrition:
                items_with_nutrition.append({
                    **item,
                    **nutrition,
                    'serving_size': '1 serving'
                })
                processed_items += 1
            else:
                # Use default
                items_with_nutrition.append({
                    **item,
                    **get_default_nutrition(),
                    'serving_size': '1 serving'
                })
                processed_items += 1
            
            # Rate limiting
            time.sleep(0.2)
        
        hall['food_items_with_nutrition'] = items_with_nutrition
        print(f"   ✅ Completed: {len(items_with_nutrition)} items")
    
    # Save
    with open('menu_with_nutrition.json', 'w') as f:
        json.dump(dining_halls, f, indent=2)
    
    print("\n" + "=" * 60)
    print(f"💾 Saved to menu_with_nutrition.json")
    print(f"✅ Processed {processed_items}/{total_items} items")
    print("=" * 60)

if __name__ == "__main__":
    add_nutrition_to_menu()