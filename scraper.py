def scrape_dining_hall(location):
    """Scrape a single dining hall using Selenium"""
    url = f"https://dining.columbia.edu/content/{location}"
    
    # Simpler Chrome options for Selenium Docker image
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    try:
        # Chrome is already installed in this image at /usr/bin/google-chrome
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        
        driver.get(url)
        time.sleep(4)
        
        food_elements = driver.find_elements(By.CLASS_NAME, "meal-title")
        
        food_items = []
        for element in food_elements:
            text = element.text.strip()
            if text and is_food_item(text):
                food_items.append(text)
        
        driver.quit()
        
        return {
            "name": location.replace("-", " ").title(),
            "food_items": food_items,
            "scraped_at": datetime.now().isoformat()
        }
    
    except Exception as e:
        print(f"❌ Error scraping {location}: {e}")
        try:
            driver.quit()
        except:
            pass
        return {
            "name": location.replace("-", " ").title(),
            "food_items": [],
            "error": str(e)
        }