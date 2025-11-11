import json
import time
import random
import logging
import os
from dotenv import load_dotenv
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from playwright_behaviour_function import play_simulate_human_behavior

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='mobile_shopeee_category_product.log',
    filemode='a'
)

load_dotenv()
email = os.getenv('shoppy_mail')
password = os.getenv('shoppy_password')

# --- Utility function to normalize expiry ---
def get_expiry(cookie):
    for key in ("expiry", "expirationDate", "expires", "expire", "expiration"):
        if key in cookie and cookie[key]:
            try:
                return int(float(cookie[key]))
            except Exception:
                pass
    return None

def Product_Scrape_by_Category(categories, cookies_json):
    # Example stealth User-Agent (realistic)
    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/118.0.5993.90 Safari/537.36"
    )
    all_products_data = []
    success = True  # Assume success unless an error occurs
   
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-gpu",
                    "--no-sandbox",
                    "--disable-dev-shm-usage"
                ]
            )
            # Create context with extra stealthy options
            context = browser.new_context(
                user_agent=user_agent,
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="Asia/Dhaka", # change if you prefer UTC
                ignore_https_errors=True,
                java_script_enabled=True,
            )
            # Additional init scripts to reduce fingerprinting
            # - hide navigator.webdriver
            # - set navigator.languages
            # - add plugins length
            context.add_init_script(
                """
                // navigator.webdriver removal
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                // mock languages
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});
                // mock plugins
                Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
                // mock permissions.query to avoid detection
                const origQuery = window.navigator.permissions && window.navigator.permissions.query;
                if (origQuery) {
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            origQuery(parameters)
                    );
                }
                """
            )
            page = context.new_page()
            # Intercept network responses for Shopee API
            api_requests = []
            def capture_response(response):
                """Capture Shopee API JSON responses"""
                try:
                    if "shopee.sg/api/v4/search/search_items" in response.url:
                        logging.info(f"Attempting to capture API response from: {response.url}")
                        try:
                            # Try parsing JSON body directly
                            body_text = response.text()
                            try:
                                json_data = json.loads(body_text)
                            except json.JSONDecodeError as json_err:
                                logging.error(f"JSON decode error for {response.url}: {json_err}")
                                json_data = {"raw_text": body_text}
                            entry = {
                                "url": response.url,
                                "status_code": response.status,
                                "response": json_data
                            }
                            # Append to memory list
                            api_requests.append(entry)
                            logging.info(f"Successfully captured API: {response.url}")
                        except Exception as e:
                            logging.error(f"Error reading body for {response.url}: {e}")
                except Exception as e:
                    logging.error(f"Error in capture_response for {getattr(response, 'url', 'unknown')}: {e}")
            # Listen on responses
            context.on("response", capture_response)
            site_url = "https://shopee.sg"
            logging.info(f"Opening {site_url}")
            try:
                page.goto(site_url, wait_until="networkidle")
                logging.info(f"Successfully opened {site_url}")
            except Exception as e:
                logging.error(f"Failed to open {site_url}: {e}")
                success = False
                return all_products_data, success # Early return on failure
            
            # Use provided cookies_json (list of dicts) instead of loading from file
            logging.info("Using provided cookies from device")
            cookies = cookies_json
            if isinstance(cookies, str):
                try:
                    cookies = json.loads(cookies)
                    logging.info("Successfully parsed cookies JSON string into list")
                except json.JSONDecodeError as e:
                    logging.error(f"Failed to parse cookies JSON: {e}")
                    success = False
                    cookies = []
            
            current_host = urlparse(page.url).hostname
            valid_cookies = []
            for cookie in cookies:
                try:
                    cookie_payload = {
                        "name": cookie.get("name"),
                        "value": cookie.get("value", ""),
                        "path": cookie.get("path", "/"),
                    }
                    if "secure" in cookie:
                        cookie_payload["secure"] = bool(cookie["secure"])
                    if "httpOnly" in cookie:
                        cookie_payload["httpOnly"] = bool(cookie["httpOnly"])
                    expiry = get_expiry(cookie)
                    if expiry:
                        # Playwright expects 'expires' as int seconds since epoch
                        cookie_payload["expires"] = expiry
                    domain = cookie.get("domain")
                    if domain:
                        normalized = domain.lstrip(".")
                        if normalized == current_host:
                            cookie_payload["domain"] = normalized
                        else:
                            # skip cookies for other domains
                            continue
                    valid_cookies.append(cookie_payload)
                except Exception as e:
                    logging.error(f"Error processing cookie: {e}")
                    success = False
            if valid_cookies:
                try:
                    context.add_cookies(valid_cookies)
                    logging.info(f"Added {len(valid_cookies)} cookies.")
                except Exception as e:
                    logging.error(f"Error adding cookies: {e}")
                    success = False
            else:
                logging.warning("No valid cookies added to the context.")
            try:
                page.reload(wait_until="networkidle")
                logging.info("Page reloaded successfully")
            except Exception as e:
                logging.error(f"Error reloading page: {e}")
                success = False
            time.sleep(4)
            # Try closing popup (same xpath as before)
            try:
                page.locator('xpath=//*[@id="HomePagePopupBannerSection"]/div[2]/div').click(timeout=3000)
                logging.info("Closed popup successfully")
            except Exception:
                logging.info("No popup found or error closing popup")
            # Simulate human behaviour (your function supports Playwright page.evaluate)
            try:
                play_simulate_human_behavior(page, random.randint(1, 7))
                logging.info("Simulated human behavior on home page")
            except Exception as e:
                logging.error(f"Error simulating human behavior: {e}")
                success = False
            
            for cat in categories:
                try:
                    parent_catId = cat["parent_catid"]
                    cat_Id = cat["catid"]
                    for i in range(2):
                        api_requests = [] # Clear for each page to capture only current page's APIs
                        page_url = f"https://shopee.sg/abc-cat.{parent_catId}.{cat_Id}?page={i}&sortBy=sales"
                        logging.info(f"Opening category page: {page_url}")
                        try:
                            page.goto(page_url, wait_until="networkidle")
                            logging.info(f"Successfully opened {page_url}")
                        except Exception as e:
                            logging.error(f"Failed to open {page_url}: {e}")
                            success = False
                            continue
                       
                        play_simulate_human_behavior(page, random.randint(1, 7))
                        # Extract product data
                        products_data = []
                        found_products = False
                        for entry in api_requests:
                            try:
                                data = entry["response"]
                                if isinstance(data, dict) and 'items' in data:
                                    for item_wrapper in data['items']:
                                        if 'item_basic' in item_wrapper:
                                            item = item_wrapper['item_basic']
                                           
                                            # Extract the data you need, adding category info
                                            product_info = {
                                                "parent_category_id": parent_catId,
                                                "child_category_id": cat_Id,
                                                "price": item.get('price', 0) / 100000, # Convert to actual price
                                                "price_before_discount": item.get('price_before_discount', 0) / 100000,
                                                "raw_discount": item.get('raw_discount', 0),
                                                "discount_percentage": item.get('discount', '0%'),
                                                "name": item.get('name', ''),
                                                "image": f"https://down-sg.img.susercontent.com/file/{item.get('image', '')}",
                                                "sold": item.get('sold', 0),
                                                "historical_sold": item.get('historical_sold', 0),
                                                "shop_name": item.get('shop_name', ''),
                                                "item_id": item.get('itemid', ''),
                                                "shop_id": item.get('shopid', ''),
                                                "rating_star": item.get('item_rating', {}).get('rating_star', 0),
                                                "rating_count": sum(item.get('item_rating', {}).get('rating_count', [0])),
                                                "shop_location": item.get('shop_location', ''),
                                                "stock": item.get('stock', 0),
                                            }
                                           
                                            products_data.append(product_info)
                                   
                                    found_products = True
                                    logging.info(f"Extracted {len(products_data)} products from {page_url}")
                            except Exception as e:
                                logging.error(f"Error processing API entry for {entry.get('url', 'unknown')}: {e}")
                                success = False
                        if found_products and products_data:
                            all_products_data.extend(products_data)
                        else:
                            logging.warning(f"No products found for page: {page_url}")
                        # Debug info: if no API requests were captured
                        if not api_requests:
                            logging.warning("No API requests captured for 'search_items'.")
                            try:
                                logging.info(f"Total network requests: {len(context.requests)}")
                                # Log the first 20 requests to help debugging
                                for req in context.requests[:20]:
                                    try:
                                        logging.info(f" - {req.url}")
                                    except Exception:
                                        pass
                            except Exception as e:
                                logging.error(f"Error logging network requests: {e}")
                                success = False
                except Exception as e:
                    logging.error(f"Failed to scrape subcategory {cat_Id} under parent {parent_catId}: {e}")
                    success = False
                    continue  # Continue to next subcategory
    except Exception as e:
        logging.error(f"Unexpected error in Product_Scrape_by_Category: {e}")
        success = False
   
    finally:
        try:
            context.close()
            browser.close()
            logging.info("Browser and context closed")
        except Exception as e:
            logging.error(f"Error closing browser/context: {e}")
            success = False
   
    return all_products_data, success