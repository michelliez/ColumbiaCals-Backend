#!/usr/bin/env python3
"""
Scheduler that runs scraper at :01 of every hour
Updates menus for breakfast, lunch, and dinner automatically
"""

import schedule
import time
import subprocess
import sys
from datetime import datetime

def update_menus():
    """Run scraper and nutrition API"""
    print(f"\n{'='*60}")
    print(f"🕐 Scheduled update at {datetime.now().strftime('%I:%M %p')}")
    print(f"{'='*60}\n")
    
    try:
        # Run scraper (it auto-detects meal period)
        print("Step 1/2: Running scraper...")
        result1 = subprocess.run([sys.executable, 'scraper.py'], 
                                capture_output=True, text=True, timeout=60)
        
        if result1.returncode == 0:
            print("✅ Scraper complete!")
            print(result1.stdout)
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

if __name__ == "__main__":
    print("🚀 Scheduler starting...")
    
    # Run immediately on startup
    update_menus()
    
    # Schedule at :01 of every hour (6:01, 7:01, 8:01, etc.)
    schedule.every().hour.at(":01").do(update_menus)
    
    print("\n⏰ Updates scheduled at :01 of every hour")
    print("   (6:01 AM, 7:01 AM, 8:01 AM, 12:01 PM, 6:01 PM, etc.)")
    print("   Meal periods auto-detected based on time:")
    print("   • 5 AM - 11 AM: Breakfast")
    print("   • 11 AM - 4 PM: Lunch")
    print("   • 4 PM - 5 AM: Dinner\n")
    
    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)