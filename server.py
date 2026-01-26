#!/usr/bin/env python3
"""
ColumbiaCals API Server
Flask server that serves dining hall data as JSON
"""

from flask import Flask, jsonify
import json
import os
import subprocess
import sys

app = Flask(__name__)

def load_menu_data():
    """Load the enriched menu data"""
    if os.path.exists('menu_with_nutrition.json'):
        with open('menu_with_nutrition.json', 'r') as f:
            return json.load(f)
    elif os.path.exists('menu_data.json'):
        with open('menu_data.json', 'r') as f:
            return json.load(f)
    else:
        return {"error": "No menu data found. Run scraper.py first!"}

@app.route('/')
def home():
    """Homepage"""
    return """
    <h1>ColumbiaCals API Server 🍽️</h1>
    <h2>Available Endpoints:</h2>
    <ul>
        <li><a href="/api/dining-halls">/api/dining-halls</a> - Get all dining halls</li>
        <li>/api/dining-halls/&lt;name&gt; - Get specific dining hall</li>
        <li><a href="/api/status">/api/status</a> - Server status</li>
        <li><a href="/api/refresh">/api/refresh</a> - Trigger data refresh</li>
    </ul>
    <p>💡 Tip: The iOS app can call /api/refresh to update the menu!</p>
    """

@app.route('/api/dining-halls')
def get_dining_halls():
    """
    Returns all dining halls with nutrition data
    Example: http://localhost:8080/api/dining-halls
    """
    data = load_menu_data()
    return jsonify(data)

@app.route('/api/dining-halls/<hall_name>')
def get_hall_menu(hall_name):
    """
    Returns menu for a specific dining hall
    Example: http://localhost:8080/api/dining-halls/Ferris
    """
    data = load_menu_data()
    
    if isinstance(data, dict) and 'error' in data:
        return jsonify(data), 500
    
    # Find the specific hall
    for hall in data:
        if hall_name.lower() in hall['name'].lower():
            return jsonify(hall)
    
    return jsonify({"error": "Dining hall not found"}), 404

@app.route('/api/status')
def status():
    """Server status check"""
    has_data = os.path.exists('menu_with_nutrition.json') or os.path.exists('menu_data.json')
    return jsonify({
        "status": "running",
        "server": "ColumbiaCals API",
        "version": "1.0",
        "has_data": has_data
    })

@app.route('/api/refresh')
def refresh_data():
    """
    Trigger a refresh of menu data
    This runs the scraper and nutrition API
    """
    try:
        print("\n🔄 Manual refresh triggered from iOS app...")
        
        # Run scraper
        print("Step 1/2: Running scraper...")
        result1 = subprocess.run([sys.executable, 'scraper.py'], 
                                capture_output=True, text=True, timeout=30)
        
        if result1.returncode != 0:
            return jsonify({
                "success": False,
                "message": "Scraper failed",
                "error": result1.stderr
            }), 500
        
        # Run nutrition API
        print("Step 2/2: Running nutrition API...")
        result2 = subprocess.run([sys.executable, 'nutrition_api.py'], 
                                capture_output=True, text=True, timeout=60)
        
        if result2.returncode != 0:
            return jsonify({
                "success": False,
                "message": "Nutrition API failed",
                "error": result2.stderr
            }), 500
        
        print("✅ Manual refresh complete!\n")
        
        return jsonify({
            "success": True,
            "message": "Menu data refreshed successfully",
            "timestamp": subprocess.check_output(['date']).decode().strip()
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({
            "success": False,
            "message": "Refresh timed out"
        }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 ColumbiaCals API Server Starting...")
    print("="*50)
    print("\n📍 Server running at: http://localhost:8080")
    print("📍 API endpoint: http://localhost:8080/api/dining-halls")
    print("📍 Refresh endpoint: http://localhost:8080/api/refresh")
    print("\n💡 Tips:")
    print("   - Test in browser: http://localhost:8080")
    print("   - For iOS: Use your Mac's IP instead of localhost")
    print("   - Find IP: ipconfig getifaddr en0")
    print("   - iOS app can call /api/refresh to update menus")
    print("\n⌨️  Press Ctrl+C to stop\n")
    
    app.run(debug=True, host='0.0.0.0', port=8080)