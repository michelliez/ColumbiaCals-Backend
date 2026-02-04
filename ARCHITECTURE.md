# ColumbiaCals Backend - Multi-University Architecture

## 📁 New Structure

```
ColumbiaCals-Backend/
├── scrapers/
│   ├── shared/
│   │   └── __init__.py          # Shared utilities (time checks, etc.)
│   ├── columbia/
│   │   └── scraper.py           # Columbia & Barnard scraper
│   └── cornell/
│       └── scraper.py           # Cornell scraper (placeholder)
├── run_all_scrapers.py          # Unified runner (combines all scrapers)
├── server.py                    # Flask API server
├── nutrition_api.py             # Nutrition data enrichment
├── menu_data.json               # Combined output from all scrapers
├── requirements.txt             # Dependencies
└── README.md                    # This file
```

## 🏫 University Support

### Columbia University ✅
- **Status**: Fully implemented
- **Coverage**: Columbia dining halls + Barnard dining halls
- **Scraper**: `scrapers/columbia/scraper.py`
- **Locations**: John Jay, Ferris Booth, Grace Dodge, Faculty House, Robert F. Smith, Blue Java cafes, etc.

### Cornell University 🚧
- **Status**: Placeholder (ready for implementation)
- **Scraper**: `scrapers/cornell/scraper.py`
- **Next Steps**: 
  1. Find Cornell's dining API or website
  2. Implement Cornell-specific scraping logic
  3. Add actual dining hall locations

## 🚀 Usage

### Run all scrapers (Recommended)
```bash
python3 run_all_scrapers.py
```

### Run specific university scraper
```bash
python3 scrapers/columbia/scraper.py    # Columbia only
python3 scrapers/cornell/scraper.py     # Cornell only (not yet implemented)
```

### Start the API server
```bash
python3 server.py
```

## 📊 Output Format

All scrapers output to `menu_data.json` with this structure:

```json
[
  {
    "name": "John Jay Dining Hall",
    "university": "columbia",
    "status": "open",
    "meals": [
      {
        "meal_type": "Lunch",
        "time": "11:30 AM - 2:00 PM",
        "stations": [
          {
            "station": "Main Station",
            "items": [
              {
                "name": "Grilled Chicken",
                "description": "...",
                "dietary_prefs": ["halal"],
                "allergens": ["gluten"]
              }
            ]
          }
        ]
      }
    ],
    "scraped_at": "2026-02-01T12:34:56.789123"
  }
]
```

## 🔧 Adding a New University

1. Create a new folder: `scrapers/[university_name]/`
2. Create `scrapers/[university_name]/scraper.py` with:
   - Function `scrape_[university_name]()` that returns list of dining hall data
   - Import from `shared` for utilities
3. Update `run_all_scrapers.py`:
   ```python
   from [university_name].scraper import scrape_[university_name]
   
   # In run_all_scrapers():
   [university_name]_results = scrape_[university_name]()
   all_results.extend([university_name]_results)
   ```

## 📝 Requirements

See `requirements.txt`:
- Flask
- Flask-CORS
- Requests
- BeautifulSoup4
- Schedule

## 🌐 API Endpoints

The Flask server (`server.py`) provides:

- `GET /api/dining` - Get all dining data
- `GET /api/dining?university=columbia` - Get Columbia-specific data
- `GET /api/dining?university=cornell` - Get Cornell-specific data

## 📅 Scheduled Updates

The server includes a background scheduler that runs:
1. All scrapers (via `run_all_scrapers.py`)
2. Nutrition API enrichment (via `nutrition_api.py`)

Runs automatically at scheduled intervals or can be manually triggered.
