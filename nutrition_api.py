#!/usr/bin/env python3
"""
Improved USDA API Integration with Better Matching
Filters unrealistic results and prioritizes quality matches
"""

import sys
import requests
import json
import time
import difflib
import argparse
import os
from dotenv import load_dotenv

print(f"[nutrition_api] Starting... Python: {sys.executable}", flush=True)
print(f"[nutrition_api] CWD: {os.getcwd()}", flush=True)
print(f"[nutrition_api] __file__: {__file__}", flush=True)

# Load environment variables from .env in backend root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# Load API key from environment variable
USDA_API_KEY = os.environ.get("USDA_API_KEY", "")
if not USDA_API_KEY:
    print("WARNING: USDA_API_KEY environment variable not set!")
    print("Set it with: export USDA_API_KEY='your_key_here'")
    print("Get a free key at: https://fdc.nal.usda.gov/api-key-signup.html")

USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1"

# Simple in-memory cache for USDA lookups during a run
USDA_SEARCH_CACHE = {}

# Manual overrides for common problematic foods
NUTRITION_OVERRIDES = {
    "tacos": {"calories": 210, "protein": 9, "carbs": 13, "fat": 13, "sodium": 450},
    "taco": {"calories": 210, "protein": 9, "carbs": 13, "fat": 13, "sodium": 450},
    "pizza": {"calories": 285, "protein": 12, "carbs": 36, "fat": 10, "sodium": 640},
    "burger": {"calories": 354, "protein": 20, "carbs": 30, "fat": 16, "sodium": 497},
    "hamburger": {"calories": 354, "protein": 20, "carbs": 30, "fat": 16, "sodium": 497},
    "burrito": {"calories": 400, "protein": 18, "carbs": 50, "fat": 14, "sodium": 900},
    "quesadilla": {"calories": 380, "protein": 16, "carbs": 35, "fat": 18, "sodium": 750},
}

# Keyword-based fallback estimates when USDA has no match
KEYWORD_ESTIMATES = {
    # Proteins
    "chicken": {"calories": 165, "protein": 31, "carbs": 0, "fat": 4, "sodium": 74},
    "beef": {"calories": 250, "protein": 26, "carbs": 0, "fat": 15, "sodium": 72},
    "pork": {"calories": 242, "protein": 27, "carbs": 0, "fat": 14, "sodium": 62},
    "fish": {"calories": 206, "protein": 22, "carbs": 0, "fat": 12, "sodium": 59},
    "salmon": {"calories": 208, "protein": 20, "carbs": 0, "fat": 13, "sodium": 59},
    "shrimp": {"calories": 99, "protein": 24, "carbs": 0, "fat": 0, "sodium": 111},
    "tofu": {"calories": 144, "protein": 17, "carbs": 3, "fat": 8, "sodium": 14},
    "egg": {"calories": 155, "protein": 13, "carbs": 1, "fat": 11, "sodium": 124},
    "turkey": {"calories": 189, "protein": 29, "carbs": 0, "fat": 7, "sodium": 70},
    "steak": {"calories": 271, "protein": 26, "carbs": 0, "fat": 18, "sodium": 54},
    "lamb": {"calories": 250, "protein": 25, "carbs": 0, "fat": 16, "sodium": 65},
    "hot dog": {"calories": 290, "protein": 11, "carbs": 24, "fat": 17, "sodium": 810},
    "frank": {"calories": 290, "protein": 11, "carbs": 24, "fat": 17, "sodium": 810},
    # Grains & Carbs
    "rice": {"calories": 130, "protein": 3, "carbs": 28, "fat": 0, "sodium": 1},
    "pasta": {"calories": 131, "protein": 5, "carbs": 25, "fat": 1, "sodium": 1},
    "noodle": {"calories": 138, "protein": 5, "carbs": 25, "fat": 2, "sodium": 5},
    "bread": {"calories": 79, "protein": 3, "carbs": 15, "fat": 1, "sodium": 147},
    "roll": {"calories": 87, "protein": 3, "carbs": 15, "fat": 2, "sodium": 146},
    "bagel": {"calories": 245, "protein": 10, "carbs": 48, "fat": 1, "sodium": 430},
    "croissant": {"calories": 231, "protein": 5, "carbs": 26, "fat": 12, "sodium": 424},
    "pancake": {"calories": 227, "protein": 6, "carbs": 28, "fat": 10, "sodium": 439},
    "waffle": {"calories": 291, "protein": 8, "carbs": 33, "fat": 14, "sodium": 511},
    "fries": {"calories": 312, "protein": 3, "carbs": 41, "fat": 15, "sodium": 210},
    "potato": {"calories": 161, "protein": 4, "carbs": 37, "fat": 0, "sodium": 17},
    "farro": {"calories": 170, "protein": 7, "carbs": 34, "fat": 1, "sodium": 5},
    "quinoa": {"calories": 120, "protein": 4, "carbs": 21, "fat": 2, "sodium": 7},
    "couscous": {"calories": 176, "protein": 6, "carbs": 36, "fat": 0, "sodium": 8},
    "spelt": {"calories": 127, "protein": 5, "carbs": 26, "fat": 1, "sodium": 5},
    # Vegetables
    "salad": {"calories": 20, "protein": 2, "carbs": 3, "fat": 0, "sodium": 25},
    "vegetable": {"calories": 65, "protein": 3, "carbs": 13, "fat": 0, "sodium": 40},
    "broccoli": {"calories": 55, "protein": 4, "carbs": 11, "fat": 1, "sodium": 33},
    "spinach": {"calories": 23, "protein": 3, "carbs": 4, "fat": 0, "sodium": 79},
    "carrot": {"calories": 52, "protein": 1, "carbs": 12, "fat": 0, "sodium": 88},
    "corn": {"calories": 96, "protein": 3, "carbs": 21, "fat": 1, "sodium": 1},
    "beans": {"calories": 127, "protein": 8, "carbs": 23, "fat": 0, "sodium": 1},
    "sprouts": {"calories": 43, "protein": 3, "carbs": 9, "fat": 0, "sodium": 25},
    "lentil": {"calories": 116, "protein": 9, "carbs": 20, "fat": 0, "sodium": 2},
    "pea": {"calories": 81, "protein": 5, "carbs": 14, "fat": 0, "sodium": 5},
    "kale": {"calories": 35, "protein": 2, "carbs": 7, "fat": 0, "sodium": 25},
    "cauliflower": {"calories": 25, "protein": 2, "carbs": 5, "fat": 0, "sodium": 30},
    "zucchini": {"calories": 17, "protein": 1, "carbs": 3, "fat": 0, "sodium": 8},
    "squash": {"calories": 40, "protein": 1, "carbs": 10, "fat": 0, "sodium": 4},
    "asparagus": {"calories": 20, "protein": 2, "carbs": 4, "fat": 0, "sodium": 2},
    "mushroom": {"calories": 22, "protein": 3, "carbs": 3, "fat": 0, "sodium": 5},
    "pepper": {"calories": 30, "protein": 1, "carbs": 6, "fat": 0, "sodium": 4},
    "onion": {"calories": 40, "protein": 1, "carbs": 9, "fat": 0, "sodium": 4},
    "tomato": {"calories": 18, "protein": 1, "carbs": 4, "fat": 0, "sodium": 5},
    # Soups
    "soup": {"calories": 75, "protein": 4, "carbs": 9, "fat": 2, "sodium": 480},
    "chili": {"calories": 256, "protein": 19, "carbs": 22, "fat": 10, "sodium": 520},
    "stew": {"calories": 180, "protein": 15, "carbs": 15, "fat": 8, "sodium": 400},
    "ragout": {"calories": 180, "protein": 12, "carbs": 18, "fat": 6, "sodium": 400},
    "dahl": {"calories": 150, "protein": 8, "carbs": 22, "fat": 3, "sodium": 350},
    "dal": {"calories": 150, "protein": 8, "carbs": 22, "fat": 3, "sodium": 350},
    # Sandwiches & Wraps
    "sandwich": {"calories": 350, "protein": 18, "carbs": 35, "fat": 14, "sodium": 750},
    "wrap": {"calories": 320, "protein": 15, "carbs": 38, "fat": 12, "sodium": 680},
    "sub": {"calories": 400, "protein": 20, "carbs": 45, "fat": 15, "sodium": 900},
    "panini": {"calories": 380, "protein": 18, "carbs": 40, "fat": 15, "sodium": 800},
    # Desserts
    "cake": {"calories": 257, "protein": 3, "carbs": 38, "fat": 11, "sodium": 214},
    "cookie": {"calories": 148, "protein": 2, "carbs": 20, "fat": 7, "sodium": 90},
    "brownie": {"calories": 227, "protein": 3, "carbs": 36, "fat": 9, "sodium": 175},
    "pie": {"calories": 237, "protein": 2, "carbs": 32, "fat": 12, "sodium": 186},
    "ice cream": {"calories": 207, "protein": 4, "carbs": 24, "fat": 11, "sodium": 80},
    "pudding": {"calories": 119, "protein": 3, "carbs": 20, "fat": 3, "sodium": 146},
    "muffin": {"calories": 377, "protein": 6, "carbs": 51, "fat": 17, "sodium": 447},
    "donut": {"calories": 269, "protein": 4, "carbs": 31, "fat": 15, "sodium": 257},
    "fruit": {"calories": 60, "protein": 1, "carbs": 15, "fat": 0, "sodium": 1},
    # Breakfast
    "oatmeal": {"calories": 158, "protein": 6, "carbs": 27, "fat": 3, "sodium": 115},
    "cereal": {"calories": 379, "protein": 7, "carbs": 84, "fat": 2, "sodium": 729},
    "yogurt": {"calories": 100, "protein": 17, "carbs": 6, "fat": 1, "sodium": 65},
    "granola": {"calories": 471, "protein": 10, "carbs": 64, "fat": 20, "sodium": 26},
    "bacon": {"calories": 541, "protein": 37, "carbs": 1, "fat": 42, "sodium": 1717},
    "sausage": {"calories": 301, "protein": 19, "carbs": 1, "fat": 24, "sodium": 749},
    # Drinks
    "milk": {"calories": 149, "protein": 8, "carbs": 12, "fat": 8, "sodium": 105},
    "juice": {"calories": 45, "protein": 1, "carbs": 10, "fat": 0, "sodium": 10},
    "smoothie": {"calories": 150, "protein": 4, "carbs": 30, "fat": 2, "sodium": 40},
    "coffee": {"calories": 2, "protein": 0, "carbs": 0, "fat": 0, "sodium": 5},
    "espresso": {"calories": 5, "protein": 0, "carbs": 1, "fat": 0, "sodium": 5},
    "latte": {"calories": 190, "protein": 10, "carbs": 19, "fat": 7, "sodium": 150},
    "tea": {"calories": 2, "protein": 0, "carbs": 0, "fat": 0, "sodium": 0},
    # Misc
    "curry": {"calories": 220, "protein": 15, "carbs": 18, "fat": 10, "sodium": 600},
    "stir fry": {"calories": 200, "protein": 15, "carbs": 15, "fat": 8, "sodium": 500},
    "fried rice": {"calories": 238, "protein": 6, "carbs": 34, "fat": 9, "sodium": 650},
    "mac and cheese": {"calories": 310, "protein": 11, "carbs": 30, "fat": 16, "sodium": 750},
    "mac & cheese": {"calories": 310, "protein": 11, "carbs": 30, "fat": 16, "sodium": 750},
    "grilled cheese": {"calories": 390, "protein": 14, "carbs": 28, "fat": 25, "sodium": 870},
    "nachos": {"calories": 346, "protein": 9, "carbs": 36, "fat": 19, "sodium": 816},
    "wings": {"calories": 203, "protein": 18, "carbs": 2, "fat": 14, "sodium": 484},
    "nuggets": {"calories": 296, "protein": 15, "carbs": 16, "fat": 19, "sodium": 600},
    "hummus": {"calories": 166, "protein": 8, "carbs": 14, "fat": 10, "sodium": 379},
    "jambalaya": {"calories": 200, "protein": 12, "carbs": 25, "fat": 6, "sodium": 600},
    "gumbo": {"calories": 180, "protein": 14, "carbs": 15, "fat": 8, "sodium": 550},
    "biryani": {"calories": 250, "protein": 10, "carbs": 35, "fat": 8, "sodium": 500},
    "tikka": {"calories": 220, "protein": 20, "carbs": 10, "fat": 12, "sodium": 450},
    "lo mein": {"calories": 220, "protein": 8, "carbs": 30, "fat": 8, "sodium": 700},
    "ramen": {"calories": 380, "protein": 10, "carbs": 52, "fat": 14, "sodium": 1500},
}

# Default fallback when nothing matches
DEFAULT_ESTIMATE = {"calories": 200, "protein": 10, "carbs": 20, "fat": 8, "sodium": 400}

def get_keyword_estimate(food_name):
    """
    Get an estimated nutrition value based on keywords in the food name.
    Returns the best matching keyword estimate or DEFAULT_ESTIMATE.
    """
    food_lower = food_name.lower()

    # Check each keyword
    for keyword, estimate in KEYWORD_ESTIMATES.items():
        if keyword in food_lower:
            print(f"   📊 Using keyword estimate for '{keyword}' in '{food_name}'")
            return {
                "description": food_name,
                "calories": estimate["calories"],
                "protein": estimate["protein"],
                "carbs": estimate["carbs"],
                "fat": estimate["fat"],
                "sodium": estimate["sodium"],
                "serving_size": "1 serving",
                "estimated": True
            }

    # No keyword match, use default
    print(f"   📊 Using default estimate for '{food_name}'")
    return {
        "description": food_name,
        "calories": DEFAULT_ESTIMATE["calories"],
        "protein": DEFAULT_ESTIMATE["protein"],
        "carbs": DEFAULT_ESTIMATE["carbs"],
        "fat": DEFAULT_ESTIMATE["fat"],
        "sodium": DEFAULT_ESTIMATE["sodium"],
        "serving_size": "1 serving",
        "estimated": True
    }

def is_realistic_nutrition(calories, protein, carbs, fat):
    """
    Check if nutrition values are realistic
    Filters out obvious data quality issues
    """
    # Calories should be in reasonable range
    if calories < 5 or calories > 2000:
        return False
    
    # Calculate calories from macros
    calculated_cals = (protein * 4) + (carbs * 4) + (fat * 9)
    
    # Allow some variation, but catch major mismatches
    if calculated_cals > 0:
        ratio = calories / calculated_cals
        if ratio < 0.5 or ratio > 2.0:
            return False
    
    # Check for unrealistic macro ratios
    total_macros = protein + carbs + fat
    if total_macros > 0:
        protein_pct = protein / total_macros
        carbs_pct = carbs / total_macros
        fat_pct = fat / total_macros
        
        # No macro should be more than 95% of total
        if max(protein_pct, carbs_pct, fat_pct) > 0.95:
            return False
    
    return True

def search_usda_food(food_name):
    """
    Search USDA database with improved matching
    Returns best match or None
    """
    print(f"   Searching USDA for: {food_name}")
    
    cache_key = food_name.lower().strip()
    if cache_key in USDA_SEARCH_CACHE:
        print(f"   ✅ Cache hit for '{food_name}'")
        return USDA_SEARCH_CACHE[cache_key]
    
    # Check manual overrides first
    food_lower = food_name.lower().strip()
    for override_key, override_data in NUTRITION_OVERRIDES.items():
        if override_key in food_lower:
            print(f"   ✅ Using manual override for '{food_name}'")
            result = {
                "description": food_name,
                "calories": override_data["calories"],
                "protein": override_data["protein"],
                "carbs": override_data["carbs"],
                "fat": override_data["fat"],
                "sodium": override_data["sodium"],
                "serving_size": "1 serving"
            }
            USDA_SEARCH_CACHE[cache_key] = result
            return result
    
    url = f"{USDA_BASE_URL}/foods/search"
    params = {
        "api_key": USDA_API_KEY,
        "query": food_name,
        "pageSize": 20,  # Get more results to filter through
        "dataType": ["Survey (FNDDS)", "Foundation", "SR Legacy"]
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            foods = data.get("foods", [])
            
            if not foods:
                print(f"   ⚠️  No USDA results for '{food_name}', using keyword estimate")
                result = get_keyword_estimate(food_name)
                USDA_SEARCH_CACHE[cache_key] = result
                return result
            
            # Score and filter results
            scored_results = []
            
            for food in foods:
                nutrients = food.get("foodNutrients", [])
                
                # Extract nutrition values
                calories = None
                protein = None
                carbs = None
                fat = None
                sodium = None
                
                for nutrient in nutrients:
                    name = nutrient.get("nutrientName", "").lower()
                    value = nutrient.get("value", 0)
                    
                    if "energy" in name and "kcal" not in name:
                        calories = value
                    elif "protein" in name:
                        protein = value
                    elif "carbohydrate" in name and "by difference" in name.lower():
                        carbs = value
                    elif "total lipid" in name or "fat" in name:
                        fat = value
                    elif "sodium" in name:
                        sodium = value
                
                # Must have at least calories to be useful
                if calories is None or calories == 0:
                    continue
                
                # Set defaults for missing macros
                if protein is None:
                    protein = 0
                if carbs is None:
                    carbs = 0
                if fat is None:
                    fat = 0
                if sodium is None:
                    sodium = 0
                
                # Filter unrealistic results
                if not is_realistic_nutrition(calories, protein, carbs, fat):
                    print(f"   ❌ Filtered out unrealistic result: {calories} cal, {protein}g protein")
                    continue
                
                # Score the result
                score = 0
                description = food.get("description", "").lower()
                food_lower = food_name.lower()
                
                # Exact match bonus
                if food_lower == description:
                    score += 100
                
                # Partial match
                if food_lower in description or description in food_lower:
                    score += 50
                
                # Prefer "Survey" data (most accurate for prepared foods)
                if food.get("dataType") == "Survey (FNDDS)":
                    score += 30
                
                # Prefer results with reasonable calorie counts
                if 50 < calories < 1000:
                    score += 20
                
                # Prefer results with all macros
                if protein > 0 and carbs > 0 and fat > 0:
                    score += 10
                
                serving_size = "100g"
                if food.get("servingSize") and food.get("servingSizeUnit"):
                    serving_size = f"{int(food['servingSize'])} {food['servingSizeUnit']}"
                
                # Compute similarity between search term and USDA description
                similarity = difflib.SequenceMatcher(None, food_lower, description).ratio()

                scored_results.append({
                    "score": score + int(similarity * 40),
                    "description": food.get("description", food_name),
                    "calories": int(calories),
                    "protein": int(protein),
                    "carbs": int(carbs),
                    "fat": int(fat),
                    "sodium": int(sodium),
                    "serving_size": serving_size,
                    "similarity": similarity
                })
            
            if not scored_results:
                print(f"   ⚠️  No realistic matches for '{food_name}', using keyword estimate")
                result = get_keyword_estimate(food_name)
                USDA_SEARCH_CACHE[cache_key] = result
                return result
            
            # Sort by score and return best match
            scored_results.sort(key=lambda x: x["score"], reverse=True)
            best_match = scored_results[0]
            
            # Determine if the match is estimated (fuzzy) or high-confidence
            similarity = best_match.get('similarity', 0.0)
            is_estimated = False
            # If exact description match, it's confident
            if food_lower == best_match['description'].lower():
                is_estimated = False
            # If similarity is fairly high (>= 0.5), use the USDA result but mark as estimated
            elif similarity >= 0.5:
                is_estimated = True
            # If similarity is low but we have USDA data, still use it (better than generic estimate)
            elif similarity >= 0.3:
                is_estimated = True
                print(f"   ⚠️  Low similarity ({similarity:.2f}) for '{food_name}', using USDA result anyway (estimated)")
            else:
                # Similarity very low — use keyword estimate instead
                print(f"   ⚠️  Very low similarity ({similarity:.2f}) for '{food_name}', using keyword estimate")
                result = get_keyword_estimate(food_name)
                USDA_SEARCH_CACHE[cache_key] = result
                return result

            best_match['estimated'] = is_estimated
            print(f"   ✅ Best match: {best_match['description']} ({best_match['calories']} cal, score: {best_match['score']}, estimated: {is_estimated})")
            
            USDA_SEARCH_CACHE[cache_key] = best_match
            return best_match
            
        else:
            print(f"   ❌ USDA API error: {response.status_code}, using keyword estimate")
            result = get_keyword_estimate(food_name)
            USDA_SEARCH_CACHE[cache_key] = result
            return result

    except Exception as e:
        print(f"   ❌ Error searching USDA: {e}, using keyword estimate")
        result = get_keyword_estimate(food_name)
        USDA_SEARCH_CACHE[cache_key] = result
        return result

def enrich_menu_with_nutrition():
    """
    Main function to add nutrition data to menu
    """
    print("\n" + "=" * 60)
    print("🥗 Adding Nutrition Data (Improved Matching)")
    print("=" * 60)

    # Use absolute paths based on this script's location
    base_dir = os.path.dirname(os.path.abspath(__file__))
    menu_data_path = os.path.join(base_dir, 'menu_data.json')
    output_path = os.path.join(base_dir, 'menu_with_nutrition.json')

    print(f"   Input: {menu_data_path}")
    print(f"   Input exists: {os.path.exists(menu_data_path)}")
    print(f"   Output: {output_path}")

    # Load menu data
    try:
        with open(menu_data_path, 'r') as f:
            dining_halls = json.load(f)
        print(f"   Loaded {len(dining_halls)} dining halls from menu_data.json")
    except FileNotFoundError:
        print("❌ menu_data.json not found. Run scraper.py first.")
        return
    
    total_items = 0
    enriched_items = 0
    failed_items = 0
    
    # Process each dining hall
    for hall in dining_halls:
        hall_name = hall['name']
        # Build a unified list of items to process from either flat 'food_items'
        # or nested meals->stations->items so we enrich whatever structure the scraper produced.
        items_to_process = []

        # If there's a flat list (older scrapers), include those
        if hall.get('food_items'):
            for item in hall.get('food_items', []):
                items_to_process.append({
                    'name': item.get('name', ''),
                    'category': item.get('category', 'Main'),
                    'source': 'food_items',
                    'ref': item
                })

        # If there's a nested meals structure, include those with references for merging
        if hall.get('meals'):
            for m_idx, meal in enumerate(hall.get('meals', [])):
                for s_idx, station in enumerate(meal.get('stations', [])):
                    for i_idx, it in enumerate(station.get('items', [])):
                        items_to_process.append({
                            'name': it.get('name', ''),
                            'category': it.get('category', 'Main'),
                            'source': 'meals',
                            'meal_idx': m_idx,
                            'station_idx': s_idx,
                            'item_idx': i_idx
                        })

        if not items_to_process:
            print(f"\n📍 {hall_name}: No items to process")
            hall['food_items_with_nutrition'] = []
            continue

        print(f"\n📍 {hall_name}: Processing {len(items_to_process)} items...")

        enriched_foods = []

        for entry in items_to_process:
            total_items += 1
            food_name = entry['name']

            # Search USDA
            nutrition = search_usda_food(food_name)

            if nutrition:
                enriched_food = {
                    "name": food_name,
                    "category": entry.get('category', 'Main'),
                    "calories": nutrition['calories'],
                    "protein": nutrition['protein'],
                    "carbs": nutrition['carbs'],
                    "fat": nutrition['fat'],
                    "sodium": nutrition['sodium'],
                    "fiber": None,
                    "sugar": None,
                    "serving_size": nutrition['serving_size'],
                    "grams": None,
                    "estimated": bool(nutrition.get('estimated', False))
                }
                enriched_foods.append(enriched_food)
                enriched_items += 1

                # Merge nutrition back into the originating structure
                try:
                    if entry['source'] == 'food_items' and entry.get('ref') is not None:
                        entry['ref']['calories'] = int(enriched_food['calories'])
                        entry['ref']['protein'] = int(enriched_food['protein'])
                        entry['ref']['carbs'] = int(enriched_food['carbs'])
                        entry['ref']['fat'] = int(enriched_food['fat'])
                        entry['ref']['sodium'] = int(enriched_food['sodium'])
                        entry['ref']['estimated'] = bool(enriched_food.get('estimated', False))

                    elif entry['source'] == 'meals':
                        m = hall['meals'][entry['meal_idx']]
                        station = m['stations'][entry['station_idx']]
                        station['items'][entry['item_idx']]['calories'] = int(enriched_food['calories'])
                        station['items'][entry['item_idx']]['protein'] = int(enriched_food['protein'])
                        station['items'][entry['item_idx']]['carbs'] = int(enriched_food['carbs'])
                        station['items'][entry['item_idx']]['fat'] = int(enriched_food['fat'])
                        station['items'][entry['item_idx']]['sodium'] = int(enriched_food['sodium'])
                        station['items'][entry['item_idx']]['estimated'] = bool(enriched_food.get('estimated', False))
                except Exception as e:
                    print(f"   ⚠️ Failed to merge nutrition into meals structure: {e}")

            else:
                # No realistic match found — do NOT insert mock data. Leave menu item unchanged.
                failed_items += 1
                print(f"   ⚠️  No USDA match for '{food_name}', skipping enrichment.")
            
            # Rate limiting
            time.sleep(0.1)
        
        hall['food_items_with_nutrition'] = enriched_foods
    
    # Check if data has too many errors (scraping failed)
    error_count = sum(1 for hall in dining_halls if hall.get('status') == 'error')
    if error_count > len(dining_halls) / 2:
        print("\n" + "=" * 60)
        print(f"⚠️ Skipping save - too many scraping errors ({error_count}/{len(dining_halls)} halls)")
        print("   Keeping existing menu_with_nutrition.json")
        print("=" * 60)
        return

    # Save enriched data
    with open(output_path, 'w') as f:
        json.dump(dining_halls, f, indent=2)

    print("\n" + "=" * 60)
    print(f"✅ Nutrition enrichment complete!")
    print(f"   Total items: {total_items}")
    print(f"   Enriched with USDA: {enriched_items}")
    print(f"   Using placeholders: {failed_items}")
    if total_items > 0:
        print(f"   Success rate: {int(enriched_items/total_items*100)}%")
    print("=" * 60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Nutrition utilities')
    parser.add_argument('--search', '-s', type=str, help='Search USDA for a food item and return best match as JSON')
    args = parser.parse_args()

    if args.search:
        result = search_usda_food(args.search)
        # Always returns a result now (USDA match or keyword estimate)
        print(json.dumps(result))
        exit(0)
    else:
        enrich_menu_with_nutrition()