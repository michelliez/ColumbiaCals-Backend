#!/usr/bin/env python3
"""
Cornell University Dining Scraper
Uses Cornell Dining Now API (now.dining.cornell.edu)
"""

import time
from typing import List, Dict, Optional
from datetime import datetime

import requests
import re
import json
from urllib.parse import urljoin

import sys
import os
# Ensure the repository root (parent of 'scrapers') is on sys.path so the
# `scrapers` package can be imported when running this file directly.
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from scrapers.base_scraper import BaseScraper

class CornellScraper(BaseScraper):
    """
    Scraper for Cornell University dining halls.
    Cornell uses their own custom API at now.dining.cornell.edu
    """
    
    # Cornell Dining Now API endpoints
    API_BASE = "https://now.dining.cornell.edu/api/1.0/dining"
    EATERIES_ENDPOINT = f"{API_BASE}/eateries.json"

    # Try a small set of alternative endpoints if the canonical one fails
    EATERIES_ALTERNATES = [
        EATERIES_ENDPOINT,
        f"{API_BASE}/eateries",
        f"{API_BASE}/locations.json",
        f"{API_BASE}/locations",
        # Public page (HTML) - may contain API references or embedded data
        "https://now.dining.cornell.edu/eateries",
        # Known admin API that sometimes holds JSON
        "https://admin-now.dining.cornell.edu/api/1.0/dining/eateries.json",
    ]
    
    # Alternative: GraphQL endpoint from Cornell AppDev
    GRAPHQL_ENDPOINT = "https://eatery-backend.cornellappdev.com/graphQL"
    
    # List of main dining halls (All You Care To Eat)
    MAIN_DINING_HALLS = [
        "104West!",
        "Okenshields", 
        "North Star Dining Room",
        "Risley Dining Room",
        "Robert Purcell Marketplace Eatery",
        "Becker House Dining Room",
        "Cook House Dining Room",
        "Rose House Dining Room",
        "Jansen's Dining Room at Bethe House",
        "Keeton House Dining Room",
        "Carl Becker House",
    ]
    
    # Cafes and retail locations
    CAFES = [
        "Amit Bhatia Libe Café",
        "Bear Necessities",
        "Big Red Barn",
        "Bus Stop Bagels",
        "Café Jennie",
        "Dairy Bar",
        "Goldie's",
        "Green Dragon",
        "Martha's Café",
        "Mattins Café",
        "Terrace Restaurant",
        "Trillium",
    ]
    
    def __init__(self):
        super().__init__("cornell", "America/New_York")
        
        # Update headers for Cornell's API
        self.session.headers.update({
            'Accept': 'application/json',
            'Referer': 'https://now.dining.cornell.edu/',
        })
    
    def scrape(self) -> List[Dict]:
        """
        Main scraping method for Cornell dining halls.
        Attempts multiple data sources in order of preference.
        """
        print("🐻 Cornell University Dining Scraper")
        print("=" * 50)
        print(f"📅 Date: {self.today_str()}")
        print(f"🕐 Time: {self.now().strftime('%I:%M %p')} ET")
        print("=" * 50)
        
        # Try Cornell Dining Now API first
        results = self._scrape_dining_now_api()
        
        if results:
            self._print_summary(results)
            return results
        
        # Fallback: Try GraphQL endpoint
        print("\n⚠️ Cornell Dining Now API unavailable, trying GraphQL...")
        results = self._scrape_graphql()
        
        if results:
            self._print_summary(results)
            return results
        
        # If all else fails, return error state
        print("\n❌ All Cornell data sources unavailable")
        return self._create_error_response()
    
    def _scrape_dining_now_api(self) -> Optional[List[Dict]]:
        """Scrape from Cornell Dining Now JSON API"""
        print("\n📡 Fetching from Cornell Dining Now API (with fallbacks)...")

        raw_data = None
        eateries = None

        # Try all known endpoints until one returns usable JSON with eateries
        for endpoint in self.EATERIES_ALTERNATES:
            print(f"   Trying endpoint: {endpoint}")
            data = self.fetch_json(endpoint)

            if not data:
                # inspect text response in case server returned a message like 'Not Implemented' or HTML/error page
                try:
                    resp = self.session.get(endpoint, timeout=10)
                    snippet = resp.text[:300]
                    print(f"   ⚠️ Non-JSON response: status={resp.status_code} snippet={snippet!r}")
                    if 'not implement' in snippet.lower():
                        print(f"   ⚠️ Endpoint returned 'Not Implemented' (or similar)")
                except requests.RequestException as e:
                    print(f"   ❌ Error fetching (diagnostic) {endpoint}: {e}")
                continue

            # Try common shapes
            if isinstance(data, dict) and data.get('data') and data['data'].get('eateries'):
                raw_data = data
                eateries = data['data']['eateries']
                break

            # Some endpoints may return eateries directly
            if isinstance(data, dict) and data.get('eateries'):
                raw_data = data
                eateries = data['eateries']
                break

            # Or return a list
            if isinstance(data, list):
                raw_data = {'data': {'eateries': data}}
                eateries = data
                break

        if not eateries:
            print("❌ Failed to find a usable eateries payload on Cornell endpoints")

            # Attempt HTML fallback: fetch the public eateries page and look for embedded
            # API URLs or JSON blobs that we can use to retrieve eateries.
            print("⚠️ Attempting HTML fallback: scanning https://now.dining.cornell.edu/eateries for API endpoints or embedded JSON...")
            html = self.fetch_html("https://now.dining.cornell.edu/eateries")

            if html:
                # 1) Find absolute API URLs in page
                candidates = set(re.findall(r'https?://[^" ]+/api/1\.0/dining/[A-Za-z0-9_\-\./]+', html))
                # 2) Find relative API paths
                rels = set(re.findall(r'(/api/1\.0/dining/[A-Za-z0-9_\-\./]+)', html))
                for r in rels:
                    candidates.add(urljoin("https://now.dining.cornell.edu", r))

                # 3) Also include the admin-now endpoint if discovered
                if "admin-now.dining.cornell.edu" in html:
                    candidates.add("https://admin-now.dining.cornell.edu/api/1.0/dining/eateries.json")

                if candidates:
                    print(f"   ⚙️ Found {len(candidates)} candidate API URL(s) in page")
                    for url in candidates:
                        print(f"   Trying discovered API: {url}")
                        data = self.fetch_json(url)
                        if not data:
                            continue

                        # Normalize shapes similar to above
                        if isinstance(data, dict) and data.get('data') and data['data'].get('eateries'):
                            raw_data = data
                            eateries = data['data']['eateries']
                            break

                        if isinstance(data, dict) and data.get('eateries'):
                            raw_data = data
                            eateries = data['eateries']
                            break

                        if isinstance(data, list):
                            raw_data = {'data': {'eateries': data}}
                            eateries = data
                            break

                # 4) Try to extract embedded JSON from script tags (nuxt/initial state etc.)
                if not eateries:
                    m = re.search(r"window\.__NUXT__\s*=\s*(\{.+?\})\s*;", html, re.S)
                    if not m:
                        m = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.+?\})\s*;", html, re.S)

                    if m:
                        try:
                            payload = json.loads(m.group(1))
                            # Try to find eateries in the payload dictionary
                            def find_eateries(obj):
                                if isinstance(obj, dict):
                                    for k, v in obj.items():
                                        if k and 'eatery' in k.lower() and isinstance(v, list):
                                            return v
                                        res = find_eateries(v)
                                        if res:
                                            return res
                                if isinstance(obj, list):
                                    for item in obj:
                                        res = find_eateries(item)
                                        if res:
                                            return res
                                return None

                            found = find_eateries(payload)
                            if found:
                                raw_data = {'data': {'eateries': found}}
                                eateries = found
                        except Exception as e:
                            print(f"   ❌ Error parsing embedded JSON: {e}")

            if not eateries:
                # Nothing found from HTML fallback
                print("   ⚠️ HTML fallback did not yield eateries")
                return None

        print(f"✅ Found {len(eateries)} eateries")

        results = []
        for eatery in eateries:
            hall = self._parse_eatery(eatery)
            if hall:
                results.append(hall)
                status_icon = "✅" if hall["status"] == "open" else "⏰"
                print(f"   {status_icon} {hall['name']}: {hall['status']}")
            time.sleep(0.1)  # Small delay between processing

        return results
    
    def _parse_eatery(self, eatery: Dict) -> Optional[Dict]:
        """Parse a single eatery from Cornell Dining Now API"""
        name = eatery.get("name", "Unknown")
        eatery_type = eatery.get("eateryType", "")
        
        # Get operating hours for today
        operating_hours = eatery.get("operatingHours", [])
        today = self.today_str()
        
        meals = []
        today_hours = None
        
        # Find today's operating hours
        for hours in operating_hours:
            if hours.get("date") == today:
                today_hours = hours
                break
        
        if today_hours and today_hours.get("events"):
            for event in today_hours["events"]:
                meal = self._parse_meal_event(event)
                if meal and meal.get("stations"):
                    meals.append(meal)
        
        # Determine status
        if meals:
            status = "open"
        elif self._is_currently_open(today_hours):
            status = "open_no_menu"
        else:
            status = "closed"
        
        return self.create_dining_hall(
            name=name,
            meals=meals,
            status=status
        )
    
    def _parse_meal_event(self, event: Dict) -> Dict:
        """Parse a meal event (breakfast, lunch, dinner, etc.)"""
        meal_type = event.get("descr") or event.get("calSummary", "Meal")

        # Cornell API provides human-readable times in "start"/"end" fields
        # AND Unix timestamps in "startTimestamp"/"endTimestamp" fields
        # Prefer the human-readable strings as they're already formatted
        start_readable = event.get("start", "")
        end_readable = event.get("end", "")
        start_timestamp = event.get("startTimestamp")
        end_timestamp = event.get("endTimestamp")

        # Format time string - prefer readable strings, fall back to timestamps
        time_str = self._format_time_range(start_readable, end_readable, start_timestamp, end_timestamp)

        # Parse menu items
        menu = event.get("menu", [])
        stations = self._parse_menu_to_stations(menu)

        return self.create_meal(
            meal_type=meal_type,
            time=time_str,
            stations=stations
        )
    
    def _parse_menu_to_stations(self, menu: List[Dict]) -> List[Dict]:
        """Parse Cornell menu format into stations with items"""
        stations = []
        
        for category in menu:
            category_name = category.get("category", "Station")
            items_data = category.get("items", [])
            
            items = []
            for item in items_data:
                # Cornell API uses "item" key for the name
                item_name = item.get("item", item.get("name", ""))
                
                if item_name and len(item_name) > 2:
                    items.append(self.create_menu_item(
                        name=item_name.strip(),
                        description=item.get("description"),
                        allergens=item.get("allergens", []),
                        dietary_prefs=self._extract_dietary_prefs(item)
                    ))
            
            if items:
                stations.append(self.create_station(
                    station_name=category_name,
                    items=items
                ))
        
        return stations
    
    def _extract_dietary_prefs(self, item: Dict) -> List[str]:
        """Extract dietary preferences from item data"""
        prefs = []
        
        if item.get("healthy"):
            prefs.append("Healthy")
        if item.get("vegan"):
            prefs.append("Vegan")
        if item.get("vegetarian"):
            prefs.append("Vegetarian")
        if item.get("glutenFree"):
            prefs.append("Gluten Free")
        
        return prefs
    
    def _is_currently_open(self, today_hours: Optional[Dict]) -> bool:
        """Check if eatery is currently open based on operating hours"""
        if not today_hours or not today_hours.get("events"):
            return False
        
        now = self.now()
        
        for event in today_hours["events"]:
            start = event.get("startTimestamp") or event.get("start", "")
            end = event.get("endTimestamp") or event.get("end", "")
            
            try:
                # Parse timestamps (Cornell uses Unix timestamps or ISO strings)
                if isinstance(start, int):
                    start_dt = datetime.fromtimestamp(start, self.timezone)
                    end_dt = datetime.fromtimestamp(end, self.timezone)
                else:
                    # Try parsing as time string
                    start_dt = self._parse_time_string(start)
                    end_dt = self._parse_time_string(end)
                
                if start_dt and end_dt and start_dt <= now <= end_dt:
                    return True
            except:
                continue
        
        return False
    
    def _parse_time_string(self, time_str: str) -> Optional[datetime]:
        """Parse various time string formats from Cornell API"""
        if not time_str:
            return None
        
        today = self.now().date()
        
        # Try different formats
        formats = [
            "%Y-%m-%d:%I:%M%p",
            "%Y-%m-%dT%H:%M:%S",
            "%H:%M",
            "%I:%M %p",
        ]
        
        for fmt in formats:
            try:
                parsed = datetime.strptime(time_str, fmt)
                # Combine with today's date if no date in format
                if "%Y" not in fmt:
                    parsed = parsed.replace(year=today.year, month=today.month, day=today.day)
                return parsed.replace(tzinfo=self.timezone)
            except ValueError:
                continue
        
        return None
    
    def _format_time_range(self, start_readable: str, end_readable: str,
                           start_timestamp: int = None, end_timestamp: int = None) -> str:
        """Format time range for display

        Cornell API provides both human-readable times (e.g., "5:30pm") and
        Unix timestamps. We prefer the readable strings when available.
        """
        # First, try to use human-readable strings directly if they look valid
        if start_readable and end_readable:
            # Clean up the format - capitalize AM/PM
            start_clean = start_readable.strip()
            end_clean = end_readable.strip()

            # If they look like times (contain am/pm or :), use them directly
            if ('am' in start_clean.lower() or 'pm' in start_clean.lower() or ':' in start_clean):
                # Format nicely: "5:30pm" -> "5:30 PM"
                start_formatted = self._format_readable_time(start_clean)
                end_formatted = self._format_readable_time(end_clean)
                return f"{start_formatted} - {end_formatted}"

        # Fall back to Unix timestamps if available
        if start_timestamp and end_timestamp:
            try:
                start_dt = datetime.fromtimestamp(start_timestamp, self.timezone)
                end_dt = datetime.fromtimestamp(end_timestamp, self.timezone)
                return f"{start_dt.strftime('%I:%M %p').lstrip('0')} - {end_dt.strftime('%I:%M %p').lstrip('0')}"
            except Exception:
                pass

        # Try parsing strings as datetime
        try:
            start_dt = self._parse_time_string(start_readable)
            end_dt = self._parse_time_string(end_readable)

            if start_dt and end_dt:
                return f"{start_dt.strftime('%I:%M %p').lstrip('0')} - {end_dt.strftime('%I:%M %p').lstrip('0')}"
        except Exception:
            pass

        return "Check dining hours"

    def _format_readable_time(self, time_str: str) -> str:
        """Format a readable time string like '5:30pm' to '5:30 PM'"""
        if not time_str:
            return time_str

        # Add space before am/pm if not present
        time_str = time_str.strip()
        time_lower = time_str.lower()

        if 'am' in time_lower:
            idx = time_lower.find('am')
            return time_str[:idx].strip() + ' AM'
        elif 'pm' in time_lower:
            idx = time_lower.find('pm')
            return time_str[:idx].strip() + ' PM'

        return time_str
    
    def _scrape_graphql(self) -> Optional[List[Dict]]:
        """Fallback: Scrape from Cornell AppDev GraphQL API"""
        print("\n📡 Fetching from GraphQL API...")
        
        query = """
        {
            campusEateries {
                id
                name
                eateryType
                location
                operatingHours {
                    date
                    events {
                        calSummary
                        description
                        startTime
                        endTime
                        menu {
                            category
                            items {
                                item
                                healthy
                            }
                        }
                    }
                }
            }
        }
        """
        
        try:
            response = self.session.post(
                self.GRAPHQL_ENDPOINT,
                json={"query": query},
                timeout=30
            )
        except requests.exceptions.SSLError as e:
            # SSL verification failed (hostname mismatch etc.) - retry with verification disabled for diagnostics
            print(f"❌ GraphQL SSL error: {e}")
            print("   ⚠️ Retrying GraphQL request with SSL verification disabled for diagnostic purposes...")
            try:
                response = self.session.post(self.GRAPHQL_ENDPOINT, json={"query": query}, timeout=30, verify=False)
            except Exception as e2:
                print(f"❌ GraphQL retry failed: {e2}")
                return None

        try:
            if response.status_code != 200:
                print(f"❌ GraphQL API returned status {response.status_code}")
                # If the server returned a body, print a short snippet for diagnostics
                try:
                    text = response.text
                    print(f"   Response snippet: {text[:400]!r}")
                    if 'not implement' in text.lower():
                        print("   ⚠️ GraphQL endpoint reports 'Not Implemented'")
                except Exception:
                    pass
                return None

            try:
                data = response.json()
            except ValueError as e:
                print(f"❌ Error decoding GraphQL JSON: {e}")
                try:
                    print(f"   Snippet: {response.text[:500]!r}")
                except Exception:
                    pass
                return None

            eateries = data.get("data", {}).get("campusEateries", [])

            if not eateries:
                print("❌ No eateries in GraphQL response")
                return None

            print(f"✅ Found {len(eateries)} eateries via GraphQL")

            results = []
            for eatery in eateries:
                hall = self._parse_graphql_eatery(eatery)
                if hall:
                    results.append(hall)

            return results
        except Exception as e:
            print(f"❌ GraphQL error: {e}")
            return None
    
    def _parse_graphql_eatery(self, eatery: Dict) -> Dict:
        """Parse eatery from GraphQL response"""
        name = eatery.get("name", "Unknown")
        
        # Parse operating hours similar to main API
        operating_hours = eatery.get("operatingHours", [])
        today = self.today_str()
        
        meals = []
        
        for hours in operating_hours:
            if hours.get("date") == today:
                for event in hours.get("events", []):
                    meal_type = event.get("description") or event.get("calSummary", "Meal")
                    
                    # Parse menu
                    menu_data = event.get("menu", [])
                    stations = []
                    
                    for category in menu_data:
                        items = []
                        for item in category.get("items", []):
                            item_name = item.get("item", "")
                            if item_name:
                                dietary = ["Healthy"] if item.get("healthy") else []
                                items.append(self.create_menu_item(
                                    name=item_name,
                                    dietary_prefs=dietary
                                ))
                        
                        if items:
                            stations.append(self.create_station(
                                station_name=category.get("category", "Station"),
                                items=items
                            ))
                    
                    if stations:
                        # Format time from GraphQL response
                        start_time = event.get('startTime', '')
                        end_time = event.get('endTime', '')
                        time_str = self._format_time_range(start_time, end_time)

                        meals.append(self.create_meal(
                            meal_type=meal_type,
                            time=time_str,
                            stations=stations
                        ))
                break
        
        status = self.determine_status(meals)
        
        return self.create_dining_hall(
            name=name,
            meals=meals,
            status=status
        )
    
    def _create_error_response(self) -> List[Dict]:
        """Create graceful fallback responses for known dining halls

        Instead of returning a 'service_unavailable' state which looks like a server outage,
        return a status that better reflects the user experience: either 'open_no_menu' when
        we're in typical dining hours (menu likely exists but wasn't retrievable) or 'closed'.
        """
        fallback = []
        likely_open = self.is_likely_open()

        status = "open_no_menu" if likely_open else "closed"

        for hall in self.MAIN_DINING_HALLS:
            fallback.append(self.create_dining_hall(
                name=hall,
                meals=[],
                status=status,
                error="Cornell Dining data currently unavailable for this location"
            ))

        return fallback
    
    def _print_summary(self, results: List[Dict]):
        """Print scraping summary"""
        open_count = sum(1 for r in results if r["status"] == "open")
        closed_count = sum(1 for r in results if r["status"] == "closed")
        no_menu_count = sum(1 for r in results if r["status"] == "open_no_menu")
        
        total_items = sum(
            len(station.get("items", []))
            for r in results
            for meal in r.get("meals", [])
            for station in meal.get("stations", [])
        )
        
        print(f"\n{'=' * 50}")
        print(f"✅ Cornell scraping complete!")
        print(f"   📊 Total eateries: {len(results)}")
        print(f"   🟢 Open: {open_count}")
        print(f"   🔴 Closed: {closed_count}")
        print(f"   🟡 No menu: {no_menu_count}")
        print(f"   🍽️  Total items: {total_items}")
        print(f"{'=' * 50}")


# Main entry point function for imports
def scrape_cornell():
    """Run Cornell scraper and return results"""
    scraper = CornellScraper()
    results = scraper.scrape()
    return results


# Script entry point
if __name__ == "__main__":
    scraper = CornellScraper()
    results = scraper.scrape()
    scraper.save_results(results, "menu_data_cornell.json")