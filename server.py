#!/usr/bin/env python3
"""
Flask server with integrated background scheduler
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import threading
import schedule
import time
import subprocess
import sys
import os
from datetime import datetime

# Import rating modules
from database import init_db, get_rating_averages, submit_rating, get_user_rating
from meal_periods import get_current_meal_period, get_current_date

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MENU_FILE = os.path.join(BASE_DIR, 'menu_with_nutrition.json')

# Initialize ratings database on startup
init_db()

def update_menus():
    """Run all scrapers (Columbia, Cornell) and nutrition API"""
    print(f"\n{'='*60}")
    print(f"🕐 Scheduled update at {datetime.now().strftime('%I:%M %p')}")
    print(f"{'='*60}\n")

    try:
        # Run all university scrapers
        scraper_path = os.path.join(BASE_DIR, 'run_all_scrapers.py')
        print(f"Step 1/2: Running all scrapers...", flush=True)
        print(f"   Python: {sys.executable}", flush=True)
        print(f"   Script: {scraper_path}", flush=True)
        print(f"   Exists: {os.path.exists(scraper_path)}", flush=True)

        result1 = subprocess.run(
            [sys.executable, scraper_path],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=BASE_DIR
        )

        # Always print all output for debugging (flush to ensure visibility in logs)
        print(f"   Return code: {result1.returncode}", flush=True)
        if result1.stdout:
            print(f"   STDOUT:\n{result1.stdout}", flush=True)
        if result1.stderr:
            print(f"   STDERR:\n{result1.stderr}", flush=True)

        if result1.returncode == 0:
            print("✅ All scrapers complete!")
        else:
            print(f"❌ Scrapers failed with code {result1.returncode}")
            return

        # Run nutrition API
        nutrition_path = os.path.join(BASE_DIR, 'nutrition_api.py')
        print(f"\nStep 2/2: Adding nutrition data...")
        print(f"   Script: {nutrition_path}")
        print(f"   Exists: {os.path.exists(nutrition_path)}")

        result2 = subprocess.run(
            [sys.executable, nutrition_path],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=BASE_DIR
        )

        # Always print all output for debugging (flush to ensure visibility in logs)
        print(f"   Return code: {result2.returncode}", flush=True)
        if result2.stdout:
            print(f"   STDOUT:\n{result2.stdout}", flush=True)
        if result2.stderr:
            print(f"   STDERR:\n{result2.stderr}", flush=True)

        if result2.returncode == 0:
            print("✅ Nutrition data added!")
        else:
            print(f"❌ Nutrition API failed with code {result2.returncode}")
            return
        
        print(f"\n{'='*60}")
        print(f"🎉 Update complete at {datetime.now().strftime('%I:%M %p')}")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def run_scheduler():
    """Run scheduler in background thread"""
    print("🚀 Scheduler thread starting...")

    # Don't run immediately on startup - use committed fallback data
    # The scraper can be triggered manually via /api/refresh if needed

    # Schedule daily updates at 3:00 AM
    schedule.every().day.at("03:00").do(update_menus)

    print("⏰ Updates scheduled at 3:00 AM daily\n")
    print("   Using committed fallback data until next scheduled update")
    
    while True:
        schedule.run_pending()
        time.sleep(60)

_refresh_lock = threading.Lock()
_refresh_in_progress = threading.Event()

def _run_update_menus_guarded():
    with _refresh_lock:
        if _refresh_in_progress.is_set():
            return
        _refresh_in_progress.set()
    try:
        update_menus()
    finally:
        _refresh_in_progress.clear()

def trigger_refresh_async():
    threading.Thread(target=_run_update_menus_guarded, daemon=True).start()

def _normalize_legacy_hall(hall):
    """Convert legacy schema (hours/meal_period/food_items) into meals-based schema."""
    if 'meals' in hall:
        return hall

    raw_items = hall.get('food_items_with_nutrition') or hall.get('food_items') or []
    items = []
    for item in raw_items:
        if isinstance(item, str):
            name = item
            data = {}
        else:
            name = item.get('name', '')
            data = item

        if not name:
            continue

        items.append({
            "name": name,
            "description": None,
            "allergens": [],
            "dietary_prefs": [],
            "calories": data.get('calories'),
            "protein": data.get('protein', data.get('protein_g')),
            "carbs": data.get('carbs', data.get('carbs_g')),
            "fat": data.get('fat', data.get('fat_g')),
            "estimated": bool(data.get('estimated', False)) if isinstance(data, dict) else None
        })

    meal_period = hall.get('meal_period', 'meal')
    meals = [{
        "meal_type": str(meal_period).title(),
        "time": hall.get('hours', hall.get('operating_hours', '')),
        "stations": [
            {
                "station": "Menu",
                "items": items
            }
        ]
    }]

    status = "open" if items else "open_no_menu"

    return {
        "name": hall.get('name', 'Dining Hall'),
        "meals": meals,
        "status": hall.get('status', status),
        "source": hall.get('source', 'legacy'),
        "scraped_at": hall.get('scraped_at', datetime.now().isoformat()),
        "operating_hours": hall.get('hours', hall.get('operating_hours')),
        "is_open": hall.get('is_open')
    }

# Start scheduler in background thread
scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()

# Ensure menu data exists on startup (Render cold start)
if not os.path.exists(MENU_FILE):
    trigger_refresh_async()

@app.route('/api/dining-halls', methods=['GET'])
def get_dining_halls():
    """Return menu data with nutrition"""
    try:
        with open(MENU_FILE, 'r') as f:
            data = json.load(f)
        normalized = [_normalize_legacy_hall(hall) for hall in data]
        return jsonify(normalized)
    except FileNotFoundError:
        # Trigger a refresh and wait briefly for first-time generation
        trigger_refresh_async()
        for _ in range(15):
            if os.path.exists(MENU_FILE):
                with open(MENU_FILE, 'r') as f:
                    data = json.load(f)
                normalized = [_normalize_legacy_hall(hall) for hall in data]
                return jsonify(normalized)
            time.sleep(1)
        return jsonify({"error": "Menu data not available"}), 503

@app.route('/api/refresh', methods=['GET'])
def refresh_menus():
    """Manually trigger menu update"""
    try:
        trigger_refresh_async()
        return jsonify({"status": "success", "message": "Refresh started"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/')
def home():
    """Root endpoint for health checks"""
    return jsonify({
        "service": "ColumbiaCals API",
        "status": "running",
        "endpoints": [
            "/api/dining-halls",
            "/api/ratings",
            "/api/ratings/averages",
            "/api/status"
        ]
    })

@app.route('/api/status', methods=['GET'])
def status():
    """Health check endpoint"""
    return jsonify({"status": "running", "timestamp": datetime.now().isoformat()})

@app.route('/api/usda-search', methods=['GET'])
def usda_search():
    """Lookup a single food in USDA and return best match (uses nutrition_api)"""
    q = request.args.get('q', '')
    if not q:
        return jsonify({"error": "missing_query"}), 400

    try:
        # Call nutrition_api.py in CLI search mode
        result = subprocess.run([sys.executable, 'nutrition_api.py', '--search', q], capture_output=True, text=True, timeout=20)
        if result.returncode == 0:
            try:
                return json.loads(result.stdout)
            except Exception:
                return jsonify({"error": "invalid_response"}), 500
        else:
            # Try to parse JSON error message
            try:
                return json.loads(result.stdout), 404
            except Exception:
                return jsonify({"error": "search_failed"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# RATING ENDPOINTS
# ============================================================================

@app.route('/api/ratings', methods=['POST'])
def post_rating():
    """
    Submit a rating for a dining hall

    Request body:
    {
        "device_id": "uuid-string",
        "hall_name": "John Jay Dining Hall",
        "university": "columbia",
        "rating": 7.5
    }
    """
    data = request.get_json()

    # Validate required fields
    required = ['device_id', 'hall_name', 'university', 'rating']
    if not data or not all(field in data for field in required):
        return jsonify({"error": "Missing required fields"}), 400

    # Validate rating range
    try:
        rating = float(data['rating'])
    except (ValueError, TypeError):
        return jsonify({"error": "Rating must be a number"}), 400

    if not (0 <= rating <= 10):
        return jsonify({"error": "Rating must be between 0 and 10"}), 400

    # Round to nearest 0.1
    rating = round(rating, 1)

    # Get current meal period and date
    meal_period = get_current_meal_period()
    current_date = get_current_date()

    try:
        submit_rating(
            device_id=data['device_id'],
            hall_name=data['hall_name'],
            university=data['university'].lower(),
            meal_period=meal_period,
            rating=rating,
            date=current_date
        )

        return jsonify({
            "status": "success",
            "meal_period": meal_period,
            "rating": rating
        })

    except Exception as e:
        print(f"Error submitting rating: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/ratings/averages', methods=['GET'])
def get_averages():
    """
    Get current meal period average ratings for all halls

    Query params:
    - university: "columbia" or "cornell" (optional, returns all if not specified)

    Response:
    {
        "meal_period": "lunch",
        "date": "2026-02-03",
        "ratings": {
            "John Jay Dining Hall": {"average": 7.5, "count": 42},
            "Ferris Booth Commons": {"average": 8.2, "count": 28}
        }
    }
    """
    university = request.args.get('university')
    if university:
        university = university.lower()

    meal_period = get_current_meal_period()
    current_date = get_current_date()

    try:
        ratings = get_rating_averages(
            university=university,
            meal_period=meal_period,
            date=current_date
        )

        return jsonify({
            "meal_period": meal_period,
            "date": current_date,
            "ratings": ratings
        })

    except Exception as e:
        print(f"Error getting averages: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/ratings/user', methods=['GET'])
def get_user_rating_endpoint():
    """
    Get user's current rating for a specific hall in current meal period

    Query params:
    - device_id: user's device UUID
    - hall_name: name of dining hall
    - university: "columbia" or "cornell"
    """
    device_id = request.args.get('device_id')
    hall_name = request.args.get('hall_name')
    university = request.args.get('university')

    if not all([device_id, hall_name, university]):
        return jsonify({"error": "Missing required parameters"}), 400

    meal_period = get_current_meal_period()
    current_date = get_current_date()

    try:
        rating = get_user_rating(
            device_id=device_id,
            hall_name=hall_name,
            university=university.lower(),
            meal_period=meal_period,
            date=current_date
        )

        if rating is not None:
            return jsonify({
                "has_rated": True,
                "rating": rating,
                "meal_period": meal_period
            })
        else:
            return jsonify({
                "has_rated": False,
                "meal_period": meal_period
            })

    except Exception as e:
        print(f"Error getting user rating: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard_endpoint():
    """
    Get top users by total rating count
    
    Query params:
    - limit: Number of users to return (default: 50, max: 100)
    
    Response:
    {
        "leaderboard": [
            {
                "rank": 1,
                "user_id": "device-uuid",
                "display_name": "User #1",
                "total_ratings": 142
            },
            ...
        ]
    }
    """
    limit = request.args.get('limit', 50, type=int)
    limit = min(limit, 100)  # Cap at 100
    
    try:
        from database import get_leaderboard
        meal_period = get_current_meal_period()
        current_date = get_current_date()
        leaderboard = get_leaderboard(limit=limit, meal_period=meal_period, date=current_date)
        return jsonify({
            "meal_period": meal_period,
            "date": current_date,
            "leaderboard": leaderboard
        })
    except Exception as e:
        print(f"Error getting leaderboard: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/user/stats', methods=['GET'])
def get_user_stats_endpoint():
    """
    Get user's rank and rating statistics
    
    Query params:
    - device_id: user's device UUID
    
    Response:
    {
        "rank": 5,
        "total_ratings": 87
    }
    """
    device_id = request.args.get('device_id')
    
    if not device_id:
        return jsonify({"error": "Missing device_id parameter"}), 400
    
    try:
        from database import get_user_stats
        meal_period = get_current_meal_period()
        current_date = get_current_date()
        stats = get_user_stats(device_id, meal_period=meal_period, date=current_date)
        return jsonify({
            **stats,
            "meal_period": meal_period,
            "date": current_date
        })
    except Exception as e:
        print(f"Error getting user stats: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)