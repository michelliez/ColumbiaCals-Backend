#!/usr/bin/env python3
"""
Flask server with integrated background scheduler
"""

from flask import Flask, jsonify
from flask_cors import CORS
import json
import threading
import schedule
import time
import subprocess
import sys
from datetime import datetime

app = Flask(__name__)
CORS(app)

def update_menus():
    """Run scraper and nutrition API"""
    print(f"\n{'='*60}")
    print(f"🕐 Scheduled update at {datetime.now().strftime('%I:%M %p')}")
    print(f"{'='*60}\n")
    
    try:
        # Run scraper
        print("Step 1/2: Running scraper...")
        result1 = subprocess.run([sys.executable, 'scraper.py'], 
                                capture_output=True, text=True, timeout=60)
        
        if result1.returncode == 0:
            print("✅ Scraper complete!")
        else:
            print(f"❌ Scraper failed: {result1.stderr}")
            return
        
        # Run nutrition API
        print("\nStep 2/2: Adding nutrition data...")
        result2 = subprocess.run([sys.executable, 'nutrition_api.py'], 
                                capture_output=True, text=True, timeout=120)
        
        if result2.returncode == 0:
            print("✅ Nutrition data added!")
        else:
            print(f"❌ Nutrition API failed: {result2.stderr}")
            return
        
        print(f"\n{'='*60}")
        print(f"🎉 Update complete at {datetime.now().strftime('%I:%M %p')}")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def run_scheduler():
    """Run scheduler in background thread"""
    print("🚀 Scheduler thread starting...")
    
    # Run immediately on startup
    update_menus()
    
    # Schedule hourly updates at :01
    schedule.every().hour.at(":01").do(update_menus)
    
    print("⏰ Updates scheduled at :01 of every hour\n")
    
    while True:
        schedule.run_pending()
        time.sleep(60)

# Start scheduler in background thread
scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()

@app.route('/api/dining-halls', methods=['GET'])
def get_dining_halls():
    """Return menu data with nutrition"""
    try:
        with open('menu_with_nutrition.json', 'r') as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"error": "Menu data not available"}), 404

@app.route('/api/refresh', methods=['GET'])
def refresh_menus():
    """Manually trigger menu update"""
    try:
        update_menus()
        return jsonify({"status": "success", "message": "Menus updated"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/status', methods=['GET'])
def status():
    """Health check endpoint"""
    return jsonify({"status": "running", "timestamp": datetime.now().isoformat()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)