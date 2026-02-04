#!/usr/bin/env python3
"""
Unified Dining Scraper Runner
Runs all university-specific scrapers and combines results
"""

import sys
import os
import json
from datetime import datetime

print(f"[run_all_scrapers] Starting... Python: {sys.executable}", flush=True)
print(f"[run_all_scrapers] CWD: {os.getcwd()}", flush=True)
print(f"[run_all_scrapers] __file__: {__file__}", flush=True)

# Add scrapers directory to path
scrapers_dir = os.path.join(os.path.dirname(__file__), 'scrapers')
sys.path.insert(0, scrapers_dir)
print(f"[run_all_scrapers] Added to path: {scrapers_dir}")
print(f"[run_all_scrapers] Scrapers dir exists: {os.path.exists(scrapers_dir)}")

try:
    print("[run_all_scrapers] Importing columbia.scraper...")
    from columbia.scraper import scrape_all_locations as scrape_columbia
    print("[run_all_scrapers] Importing cornell.scraper...")
    from cornell.scraper import scrape_cornell
    print("[run_all_scrapers] All imports successful!")
except ImportError as e:
    print(f"[run_all_scrapers] IMPORT ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

def run_all_scrapers():
    """Run all university scrapers and combine results"""
    print("\n" + "=" * 60)
    print("🍽️  ColumbiaCals Unified Dining Scraper")
    print("=" * 60)
    
    all_results = []
    
    # Run Columbia scraper
    try:
        columbia_results = scrape_columbia()
        all_results.extend(columbia_results)
    except Exception as e:
        print(f"\n❌ Columbia scraper failed: {e}")
    
    # Run Cornell scraper
    try:
        cornell_results = scrape_cornell()
        all_results.extend(cornell_results)
    except Exception as e:
        print(f"\n❌ Cornell scraper failed: {e}")
    
    # Check if data has too many errors (scraping failed)
    output_file = os.path.join(os.path.dirname(__file__), 'menu_data.json')
    error_count = sum(1 for r in all_results if r.get('status') == 'error')

    if error_count > len(all_results) / 2:
        print(f"\n⚠️ Skipping save - too many scraping errors ({error_count}/{len(all_results)} halls)")
        print("   Keeping existing menu_data.json")
    else:
        # Save combined results
        with open(output_file, 'w') as f:
            json.dump(all_results, f, indent=2)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    by_university = {}
    total_open = 0
    total_items = 0
    
    for result in all_results:
        uni = result.get('university', 'unknown')
        status = result.get('status', 'unknown')
        
        if uni not in by_university:
            by_university[uni] = {'open': 0, 'closed': 0, 'error': 0, 'items': 0}
        
        if status == 'open':
            by_university[uni]['open'] += 1
            total_open += 1
            for meal in result.get('meals', []):
                for station in meal.get('stations', []):
                    count = len(station.get('items', []))
                    by_university[uni]['items'] += count
                    total_items += count
        elif status == 'closed':
            by_university[uni]['closed'] += 1
        else:
            by_university[uni]['error'] += 1
    
    for uni, stats in by_university.items():
        print(f"\n{uni.upper()}:")
        print(f"  🟢 Open: {stats['open']}")
        print(f"  🔴 Closed: {stats['closed']}")
        print(f"  ❌ Errors: {stats['error']}")
        if stats['items'] > 0:
            print(f"  📝 Items: {stats['items']}")
    
    print(f"\n📌 TOTAL")
    print(f"  Open dining halls: {total_open}")
    print(f"  Total menu items: {total_items}")
    print(f"  Saved to: {output_file}")
    print("=" * 60 + "\n")
    
    return all_results

if __name__ == "__main__":
    run_all_scrapers()
