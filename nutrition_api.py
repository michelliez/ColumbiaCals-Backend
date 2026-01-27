#!/usr/bin/env python3
"""
Improved USDA API Integration with Better Matching
Filters unrealistic results and prioritizes quality matches
"""

import requests
import json
import time

USDA_API_KEY = "ewKS5i9HHXzrJfWRzK88q9EcjJfBT2ufivWOx6BK"
USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1"

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
    
    # Check manual overrides first
    food_lower = food_name.lower().strip()
    for override_key, override_data in NUTRITION_OVERRIDES.items():
        if override_key in food_lower:
            print(f"   ✅ Using manual override for '{food_name}'")
            return {
                "description": food_name,
                "calories": override_data["calories"],
                "protein": override_data["protein"],
                "carbs": override_data["carbs"],
                "fat": override_data["fat"],
                "sodium": override_data["sodium"],
                "serving_size": "1 serving"
            }
    
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
                print(f"   ⚠️  No USDA results for '{food_name}'")
                return None
            
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
                
                scored_results.append({
                    "score": score,
                    "description": food.get("description", food_name),
                    "calories": int(calories),
                    "protein": int(protein),
                    "carbs": int(carbs),
                    "fat": int(fat),
                    "sodium": int(sodium),
                    "serving_size": serving_size
                })
            
            if not scored_results:
                print(f"   ⚠️  No realistic matches for '{food_name}'")
                return None
            
            # Sort by score and return best match
            scored_results.sort(key=lambda x: x["score"], reverse=True)
            best_match = scored_results[0]
            
            print(f"   ✅ Best match: {best_match['description']} ({best_match['calories']} cal, score: {best_match['score']})")
            
            return best_match
            
        else:
            print(f"   ❌ USDA API error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"   ❌ Error searching USDA: {e}")
        return None

def enrich_menu_with_nutrition():
    """
    Main function to add nutrition data to menu
    """
    print("\n" + "=" * 60)
    print("🥗 Adding Nutrition Data (Improved Matching)")
    print("=" * 60)
    
    # Load menu data
    try:
        with open('menu_data.json', 'r') as f:
            dining_halls = json.load(f)
    except FileNotFoundError:
        print("❌ menu_data.json not found. Run scraper.py first.")
        return
    
    total_items = 0
    enriched_items = 0
    failed_items = 0
    
    # Process each dining hall
    for hall in dining_halls:
        hall_name = hall['name']
        food_items = hall.get('food_items', [])
        
        if not food_items:
            print(f"\n📍 {hall_name}: No items to process")
            hall['food_items_with_nutrition'] = []
            continue
        
        print(f"\n📍 {hall_name}: Processing {len(food_items)} items...")
        
        enriched_foods = []
        
        for item in food_items:
            total_items += 1
            food_name = item['name']
            
            # Search USDA
            nutrition = search_usda_food(food_name)
            
            if nutrition:
                enriched_food = {
                    "name": food_name,
                    "category": item['category'],
                    "calories": nutrition['calories'],
                    "protein": nutrition['protein'],
                    "carbs": nutrition['carbs'],
                    "fat": nutrition['fat'],
                    "sodium": nutrition['sodium'],
                    "fiber": None,
                    "sugar": None,
                    "serving_size": nutrition['serving_size'],
                    "grams": None
                }
                enriched_foods.append(enriched_food)
                enriched_items += 1
            else:
                # Use placeholder for failed matches
                enriched_food = {
                    "name": food_name,
                    "category": item['category'],
                    "calories": 150,
                    "protein": 5,
                    "carbs": 20,
                    "fat": 5,
                    "sodium": 300,
                    "fiber": None,
                    "sugar": None,
                    "serving_size": "1 serving",
                    "grams": None
                }
                enriched_foods.append(enriched_food)
                failed_items += 1
                print(f"   ⚠️  Using placeholder for '{food_name}'")
            
            # Rate limiting
            time.sleep(0.1)
        
        hall['food_items_with_nutrition'] = enriched_foods
    
    # Save enriched data
    with open('menu_with_nutrition.json', 'w') as f:
        json.dump(dining_halls, f, indent=2)
    
    print("\n" + "=" * 60)
    print(f"✅ Nutrition enrichment complete!")
    print(f"   Total items: {total_items}")
    print(f"   Enriched with USDA: {enriched_items}")
    print(f"   Using placeholders: {failed_items}")
    print(f"   Success rate: {int(enriched_items/total_items*100)}%")
    print("=" * 60)

if __name__ == "__main__":
    enrich_menu_with_nutrition()