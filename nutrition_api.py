#!/usr/bin/env python3
"""
USDA Nutrition API - Full Nutrition Data
Gets calories, protein, carbs, fat, sodium, fiber, sugar
"""

import requests
import json
import time

USDA_API_KEY = "ewKS5i9HHXzrJfWRzK88q9EcjJfBT2ufivWOx6BK"
USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1"

def estimate_serving_size(food_name):
    """Estimate realistic serving size based on food type"""
    food_lower = food_name.lower()
    
    # Liquids
    if any(word in food_lower for word in ['soup', 'sauce', 'broth', 'juice']):
        return "1 cup", 240
    
    # Pasta/Rice
    if any(word in food_lower for word in ['pasta', 'rice', 'noodle', 'spaghetti']):
        return "1 cup cooked", 200
    
    # Meat/Protein
    if any(word in food_lower for word in ['chicken', 'beef', 'pork', 'fish', 'salmon', 'turkey', 'steak', 'tenders']):
        return "4 oz", 115
    
    # Bread items
    if any(word in food_lower for word in ['bread', 'roll', 'bun', 'bagel', 'toast']):
        return "1 piece", 50
    
    # Pizza
    if 'pizza' in food_lower:
        return "1 slice", 100
    
    # Sandwiches/Subs
    if any(word in food_lower for word in ['sandwich', 'sub', 'burger', 'wrap']):
        return "1 whole", 250
    
    # Breakfast items
    if any(word in food_lower for word in ['egg', 'bacon', 'sausage']):
        if 'egg' in food_lower:
            return "2 eggs", 100
        return "2-3 pieces", 60
    
    if any(word in food_lower for word in ['pancake', 'waffle', 'french toast']):
        return "2 pieces", 140
    
    # Vegetables
    if any(word in food_lower for word in ['salad', 'broccoli', 'carrot', 'vegetable', 'greens']):
        return "1 cup", 150
    
    # Sides
    if any(word in food_lower for word in ['fries', 'chips', 'tots']):
        return "1 cup", 100
    
    # Desserts
    if any(word in food_lower for word in ['cake', 'cookie', 'brownie', 'pie']):
        if 'cookie' in food_lower:
            return "1 cookie", 40
        return "1 slice", 80
    
    # Beans/Legumes
    if any(word in food_lower for word in ['beans', 'lentils', 'chickpeas']):
        return "1/2 cup", 90
    
    # Dairy
    if any(word in food_lower for word in ['yogurt', 'milk', 'cheese']):
        if 'cheese' in food_lower:
            return "1 oz", 28
        return "1 cup", 240
    
    return "1 serving", 100

def search_food_usda(food_name):
    """Search USDA database for FULL nutrition data"""
    print(f"   🔎 {food_name[:40]}")
    
    url = f"{USDA_BASE_URL}/foods/search"
    params = {
        'api_key': USDA_API_KEY,
        'query': food_name,
        'pageSize': 1
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('foods') and len(data['foods']) > 0:
            food = data['foods'][0]
            nutrients = food.get('foodNutrients', [])
            
            # Extract all nutrients (USDA data is per 100g)
            nutrition_per_100g = {
                'calories': 0,
                'protein': 0,
                'carbs': 0,
                'fat': 0,
                'sodium': 0,
                'fiber': 0,
                'sugar': 0
            }
            
            for nutrient in nutrients:
                name = nutrient.get('nutrientName', '').lower()
                value = nutrient.get('value', 0)
                
                if 'energy' in name or 'calorie' in name:
                    nutrition_per_100g['calories'] = int(value)
                elif 'protein' in name:
                    nutrition_per_100g['protein'] = int(value)
                elif 'carbohydrate' in name and 'by difference' in name:
                    nutrition_per_100g['carbs'] = int(value)
                elif 'total lipid' in name or ('fat' in name and 'fatty' not in name):
                    nutrition_per_100g['fat'] = int(value)
                elif 'sodium' in name:
                    nutrition_per_100g['sodium'] = int(value)
                elif 'fiber' in name and 'total dietary' in name:
                    nutrition_per_100g['fiber'] = int(value)
                elif 'sugars, total' in name:
                    nutrition_per_100g['sugar'] = int(value)
            
            # Get serving size
            serving_desc, serving_grams = estimate_serving_size(food_name)
            
            # Scale nutrition to serving size
            scale_factor = serving_grams / 100
            nutrition = {
                'calories': int(nutrition_per_100g['calories'] * scale_factor),
                'protein': int(nutrition_per_100g['protein'] * scale_factor),
                'carbs': int(nutrition_per_100g['carbs'] * scale_factor),
                'fat': int(nutrition_per_100g['fat'] * scale_factor),
                'sodium': int(nutrition_per_100g['sodium'] * scale_factor),
                'fiber': int(nutrition_per_100g['fiber'] * scale_factor) if nutrition_per_100g['fiber'] > 0 else None,
                'sugar': int(nutrition_per_100g['sugar'] * scale_factor) if nutrition_per_100g['sugar'] > 0 else None,
                'serving_size': serving_desc,
                'grams': serving_grams
            }
            
            print(f"      ✅ {nutrition['calories']}cal | P:{nutrition['protein']}g | C:{nutrition['carbs']}g | F:{nutrition['fat']}g")
            return nutrition
            
        else:
            # Fallback estimates
            print(f"      ⚠️  Using estimates")
            serving_desc, serving_grams = estimate_serving_size(food_name)
            return {
                'calories': 200,
                'protein': 10,
                'carbs': 25,
                'fat': 8,
                'sodium': 200,
                'fiber': 2,
                'sugar': 3,
                'serving_size': serving_desc,
                'grams': serving_grams
            }
            
    except Exception as e:
        print(f"      ❌ Error - using estimates")
        serving_desc, serving_grams = estimate_serving_size(food_name)
        return {
            'calories': 200,
            'protein': 10,
            'carbs': 25,
            'fat': 8,
            'sodium': 200,
            'fiber': 2,
            'sugar': 3,
            'serving_size': serving_desc,
            'grams': serving_grams
        }

def add_nutrition_to_menus(menu_file='menu_data.json'):
    """Add FULL nutrition info"""
    print("\n📊 Adding FULL nutrition data (Protein, Carbs, Fat, Sodium)...\n")
    
    try:
        with open(menu_file, 'r') as f:
            dining_halls = json.load(f)
    except FileNotFoundError:
        print("❌ menu_data.json not found!")
        return
    
    for hall in dining_halls:
        print(f"\n🏛️  {hall['name']}")
        enriched_items = []
        
        food_items = hall.get('food_items', [])
        
        for i, food_item in enumerate(food_items):
            if isinstance(food_item, dict):
                food_name = food_item.get('name', 'Unknown')
                category = food_item.get('category', 'Main')
            else:
                food_name = str(food_item)
                category = 'Main'
            
            nutrition = search_food_usda(food_name)
            nutrition['name'] = food_name
            nutrition['category'] = category
            
            enriched_items.append(nutrition)
            
            if i < len(food_items) - 1:
                time.sleep(0.3)
        
        hall['food_items_with_nutrition'] = enriched_items
        print(f"   ✅ {len(enriched_items)} items completed")
    
    with open('menu_with_nutrition.json', 'w') as f:
        json.dump(dining_halls, f, indent=2)
    
    print("\n" + "="*60)
    print("✅ Full nutrition data saved!")
    print("="*60)

if __name__ == "__main__":
    print("="*60)
    print("🍽️  Columbia Cals - FULL Nutrition Tracker")
    print("="*60)
    add_nutrition_to_menus()