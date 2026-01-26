# ColumbiaCals Backend

Backend API for ColumbiaCals - A nutrition tracking app for Columbia University dining halls.

## Features
- Scrapes daily menus from LionDine.com
- Fetches nutrition data from USDA API
- Provides REST API for mobile app
- Automatic daily updates

## Setup
```bash
pip install -r requirements.txt
python3 scraper.py
python3 nutrition_api.py
python3 server.py
```

## API Endpoints
- `GET /api/dining-halls` - Get all dining halls with nutrition data
- `GET /api/status` - Check server status
- `GET /api/refresh` - Trigger manual refresh

## Environment Variables
- `USDA_API_KEY` - Your USDA FoodData Central API key

## Tech Stack
- Python 3.11
- Flask
- BeautifulSoup4
- Requests
