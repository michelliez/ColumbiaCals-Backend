#!/usr/bin/env python3
"""
Base Scraper
Common functionality for all school scrapers.
"""

import requests
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Optional, Any
from zoneinfo import ZoneInfo


class BaseScraper(ABC):
    """
    Abstract base class for all school dining scrapers.
    Each school-specific scraper must implement the scrape() method.
    """
    
    def __init__(self, school_id: str, timezone: str = "America/New_York"):
        self.school_id = school_id
        self.timezone = ZoneInfo(timezone)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'en-US,en;q=0.9',
        })
    
    def now(self) -> datetime:
        """Get current time in school's timezone"""
        return datetime.now(self.timezone)
    
    def today_str(self) -> str:
        """Get today's date as YYYY-MM-DD string"""
        return self.now().strftime("%Y-%m-%d")
    
    def is_likely_open(self) -> bool:
        """Check if dining halls are typically open at current time"""
        now = self.now()
        hour = now.hour
        day = now.weekday()  # 0=Monday, 6=Sunday
        
        if day < 5:  # Monday-Friday
            return 7 <= hour < 23
        else:  # Saturday-Sunday
            return 8 <= hour < 22
    
    @abstractmethod
    def scrape(self) -> List[Dict]:
        """
        Main scraping method - must be implemented by each school scraper.
        
        Returns:
            List of dining hall dictionaries with structure:
            {
                "name": str,
                "meals": [
                    {
                        "meal_type": str,
                        "time": str,
                        "stations": [
                            {
                                "station": str,
                                "items": [
                                    {
                                        "name": str,
                                        "description": str | None,
                                        "allergens": List[str],
                                        "dietary_prefs": List[str]
                                    }
                                ]
                            }
                        ]
                    }
                ],
                "status": str,  # "open", "closed", "open_no_menu", "error"
                "source": str,
                "scraped_at": str  # ISO timestamp
            }
        """
        pass
    
    def create_dining_hall(
        self,
        name: str,
        meals: List[Dict] = None,
        status: str = "unknown",
        error: Optional[str] = None
    ) -> Dict:
        """Helper to create a standardized dining hall response"""
        result = {
            "name": name,
            "meals": meals or [],
            "status": status,
            "source": self.school_id,
            "university": self.school_id,
            "scraped_at": self.now().isoformat()
        }
        if error:
            result["error"] = error
        return result
    
    def create_meal(
        self,
        meal_type: str,
        time: str,
        stations: List[Dict] = None
    ) -> Dict:
        """Helper to create a standardized meal"""
        return {
            "meal_type": meal_type,
            "time": time,
            "stations": stations or []
        }
    
    def create_station(
        self,
        station_name: str,
        items: List[Dict] = None
    ) -> Dict:
        """Helper to create a standardized station"""
        return {
            "station": station_name,
            "items": items or []
        }
    
    def create_menu_item(
        self,
        name: str,
        description: Optional[str] = None,
        allergens: List[str] = None,
        dietary_prefs: List[str] = None
    ) -> Dict:
        """Helper to create a standardized menu item"""
        return {
            "name": name,
            "description": description,
            "allergens": allergens or [],
            "dietary_prefs": dietary_prefs or []
        }
    
    def fetch_json(self, url: str, timeout: int = 30) -> Optional[Dict]:
        """Safely fetch and parse JSON from URL with better diagnostics"""
        response = None
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"   ❌ Error fetching {url}: {e}")
            # If the request yielded a response object, print a short snippet for diagnostics
            try:
                resp = getattr(e, 'response', response) or response
                if resp is not None:
                    print(f"      Status: {getattr(resp, 'status_code', 'N/A')}, Snippet: {getattr(resp, 'text', '')[:300]!r}")
            except Exception:
                pass
            return None

        try:
            return response.json()
        except ValueError as e:
            # Response wasn't valid JSON - print a helpful snippet
            try:
                print(f"   ❌ Error decoding JSON from {url}: {e}")
                print(f"      Status: {response.status_code}, Snippet: {response.text[:500]!r}")
            except Exception:
                pass
            return None
    
    def fetch_html(self, url: str, timeout: int = 30) -> Optional[str]:
        """Safely fetch HTML from URL"""
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"   ❌ Error fetching {url}: {e}")
            return None
    
    def save_results(self, results: List[Dict], filename: str) -> None:
        """Save scraper results to JSON file"""
        try:
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"✅ Results saved to {filename}")
        except Exception as e:
            print(f"❌ Error saving results: {e}")
    
    def _create_error_response(self) -> List[Dict]:
        """Create an error response when scraping fails"""
        return [
            self.create_dining_hall(
                name="Unable to fetch menu",
                status="error",
                error="Dining website is temporarily unavailable"
            )
        ]
    
    def _print_summary(self, results: List[Dict]) -> None:
        """Print a summary of scraping results"""
        open_count = sum(1 for r in results if r.get("status") == "open")
        closed_count = sum(1 for r in results if r.get("status") == "closed")
        no_menu_count = sum(1 for r in results if r.get("status") == "open_no_menu")
        error_count = sum(1 for r in results if r.get("status") == "error")
        
        total_items = sum(
            len(item) for r in results 
            for meal in r.get("meals", []) 
            for station in meal.get("stations", [])
            for item in station.get("items", [])
        )
        
        print(f"\n{'=' * 50}")
        print(f"✅ Scraping complete!")
        print(f"   📊 Total locations: {len(results)}")
        print(f"   🟢 Open: {open_count}")
        print(f"   🔴 Closed: {closed_count}")
        print(f"   🟡 No menu: {no_menu_count}")
        print(f"   ⚠️  Errors: {error_count}")
        print(f"   🍽️  Total items: {total_items}")
        print(f"{'=' * 50}")
