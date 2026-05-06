# scraper.py
# Production-ready SerpAPI Google Shopping scraper
# No web scraping. No fake data. Real products only.

import os
import re
import threading
import time
from dotenv import load_dotenv
from serpapi import GoogleSearch

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

def get_immersive_data_with_timeout(search_obj, timeout=10):
    """Get immersive data with timeout to prevent hanging"""
    result = [None]
    exception = [None]

    def worker():
        try:
            result[0] = search_obj.get_dict()
        except Exception as e:
            exception[0] = e

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        # Timeout occurred
        return None
    if exception[0]:
        raise exception[0]
    return result[0]

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

# TRUSTED Indian e-commerce platforms ONLY - strict whitelist
TRUSTED_DOMAINS = {
    'amazon.in':           'Amazon',
    'flipkart.com':        'Flipkart',
    'myntra.com':          'Myntra',
    'meesho.com':          'Meesho',
    'snapdeal.com':        'Snapdeal',
    'ajio.com':            'Ajio',
    'tatacliq.com':        'Tata CLiQ',
    'nykaa.com':           'Nykaa',
    'croma.com':           'Croma',
    'reliancedigital.com': 'Reliance Digital',
}


def detect_platform_from_url(url: str) -> str:
    """Detect platform from trusted ecommerce domain."""
    url_lower = url.lower()
    for domain, platform_name in TRUSTED_DOMAINS.items():
        if domain in url_lower:
            return platform_name
    return None


def normalize_platform(url: str) -> str:
    """Get platform name - URL first, then fallback."""
    platform = detect_platform_from_url(url)
    return platform if platform else 'Unknown'


def is_valid_product_url(url: str) -> tuple:
    """Validate URL is from TRUSTED ecommerce domain ONLY.
    Returns: (is_valid, reason)
    """
    if not url:
        return False, "Empty"
    if not url.startswith('http'):
        return False, "NoHttp"
    
    url_lower = url.lower()
    
    if 'google.com' in url_lower:
        return False, "Google"
    if 'serpapi.com' in url_lower:
        return False, "SerpAPI"
    
    for trusted_domain in TRUSTED_DOMAINS.keys():
        if trusted_domain in url_lower:
            return True, "OK"
    
    return False, "Untrusted"


def clean_price(price_val) -> float | None:
    """
    Strip ₹, Rs, commas, spaces and convert to float.
    Returns None if the value is invalid or zero.
    """
    if price_val is None:
        return None
    cleaned = re.sub(r'[^\d.]', '', str(price_val).replace(',', ''))
    try:
        val = float(cleaned)
        return val if val > 0 else None
    except ValueError:
        return None


def safe_rating(rating_val) -> float | None:
    """
    Safely convert rating to float.
    Returns None if missing or unparseable — never forces a fake value.
    """
    if rating_val is None:
        return None
    try:
        val = float(rating_val)
        return val if 0.0 < val <= 5.0 else None
    except (ValueError, TypeError):
        return None


# ─────────────────────────────────────────────────────────────
# Main Scraper
# ─────────────────────────────────────────────────────────────

def scrape_products(query: str) -> list[dict]:
    """
    Fetch real product data from Google Shopping via SerpAPI.

    Returns a list of validated product dicts ready for:
      - analyzer.py  (scoring + sentiment)
      - database.py  (caching)
      - results.html (UI rendering)

    Returns empty list if API key missing or API call fails.
    """
    print(f"\n[Scraper] Query: '{query}'")

    api_key = os.environ.get("SERPAPI_KEY", "").strip()
    print(f"[Debug] API Key found: {bool(api_key)} (Length: {len(api_key)})")
    
    if not api_key or api_key == "your_api_key_here":
        print("[Scraper] ERROR: SERPAPI_KEY is missing or invalid in .env")
        return []

    params = {
        "engine":  "google_shopping",
        "q":       query,
        "hl":      "en",
        "gl":      "in",
        "api_key": api_key,
        "num":     40,
    }

    print("[Scraper] Calling SerpAPI Google Shopping...")
    valid_products = []
    rejected = 0

    try:
        search  = GoogleSearch(params)
        data    = search.get_dict()
        
        print(f"[Debug] Response Keys: {list(data.keys())}")
        if "search_metadata" in data:
            print(f"[Debug] Search Status: {data['search_metadata'].get('status')}")

        if "error" in data:
            error_msg = data['error']
            print(f"[Scraper] API Error: {error_msg}")
            raise Exception(f"SerpAPI Error: {error_msg}")
        
        if "search_metadata" in data:
            status = data['search_metadata'].get('status')
            if status and status != "Success":
                error_msg = f"API returned status: {status}"
                print(f"[Scraper] {error_msg}")
                raise Exception(error_msg)

        shopping_results = data.get("shopping_results", [])
        print(f"[Scraper] Raw shopping_results count: {len(shopping_results)}")

        for item in shopping_results:
            name = (item.get("title") or "").strip()
            price = item.get("extracted_price")
            if not price:
                price = clean_price(item.get("price"))
            else:
                price = clean_price(price)

            # === GET REAL ECOMMERCE URL ===
            product_url = ""
            page_token = item.get("immersive_product_page_token")
            if page_token:
                try:
                    immersive_params = {
                        "engine": "google_immersive_product",
                        "page_token": page_token,
                        "api_key": api_key
                    }
                    immersive_search = GoogleSearch(immersive_params)
                    immersive_data = get_immersive_data_with_timeout(immersive_search, timeout=8)
                    if "product_results" in immersive_data:
                        product_info = immersive_data["product_results"]
                        if "stores" in product_info:
                            stores = product_info["stores"]
                            # Find FIRST store from TRUSTED domain
                            for store in stores:
                                store_link = store.get("link", "")
                                if store_link:
                                    is_valid, _ = is_valid_product_url(store_link)
                                    if is_valid:
                                        product_url = store_link
                                        break
                except Exception:
                    pass

            # === VALIDATE URL ===
            is_url_valid, url_reason = is_valid_product_url(product_url)
            if not is_url_valid:
                print(f"  [✗ {url_reason}] '{name[:35]}'")
                rejected += 1
                continue

            # === VALIDATE NAME & PRICE ===
            if not name:
                print(f"  [✗ NoName] Item #{rejected+1}")
                rejected += 1
                continue
            if not price or price <= 0:
                print(f"  [✗ BadPrice] '{name[:35]}'")
                rejected += 1
                continue

            # === EXTRACT FIELDS ===
            rating = safe_rating(item.get("rating"))
            image = (item.get("thumbnail") or item.get("serpapi_thumbnail") or "").strip()
            platform = normalize_platform(product_url)
            snippet = (item.get("snippet") or "").strip()

            # === BUILD PRODUCT ===
            product = {
                "name": name,
                "price": price,
                "rating": rating,
                "platform": platform,
                "image": image,
                "product_url": product_url,
                "review_text": snippet,
                "discount_percent": 0.0,
                "search_query": query,
            }

            valid_products.append(product)
            print(f"  [✓] {platform:15} | ₹{price:7.0f} | {name[:35]}")

            if len(valid_products) >= 20:
                break
            if len(valid_products) >= 20:
                break

    except Exception as e:
        print(f"[Scraper] Request failed: {e}")

    print(f"[Scraper] Valid: {len(valid_products)} | Rejected: {rejected}\n")
    return valid_products
