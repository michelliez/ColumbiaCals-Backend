#!/usr/bin/env python3
"""
Daily Update Automation
Automatically scrapes LionDine and updates nutrition data daily
"""

import schedule
import time
from datetime import datetime
import subprocess
import sys

def daily_update():
    """
    Run the full pipeline: scrape → enrich → save
    """
    print("\n" + "="*50)
    print(f"🔄 Starting daily update at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50 + "\n")
    
    # Step 1: Scrape LionDine
    print("Step 1/2: Scraping LionDine...")
    try:
        subprocess.run([sys.executable, 'scraper.py'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Scraper failed: {e}")
        return
    
    # Step 2: Add nutrition data
    print("\nStep 2/2: Adding nutrition data...")
    try:
        subprocess.run([sys.executable, 'nutrition_api.py'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Nutrition API failed: {e}")
        return
    
    print("\n" + "="*50)
    print("✅ Daily update complete!")
    print("="*50 + "\n")

def main():
    """Main scheduler loop"""
    print("\n⏰ ColumbiaCals Daily Update Scheduler")
    print("="*50)
    print("📅 Schedule: Daily at 6:00 AM")
    print("🔄 You can also run manually by pressing 'u' + Enter")
    print("⌨️  Press Ctrl+C to stop\n")
    
    # Schedule daily update at 6 AM
    schedule.every().day.at("06:00").do(daily_update)
    
    # Run immediately on start (optional)
    print("🚀 Running initial update now...")
    daily_update()
    
    print("\n⏰ Scheduler is now running. Waiting for scheduled time...")
    
    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Scheduler stopped. Goodbye!")