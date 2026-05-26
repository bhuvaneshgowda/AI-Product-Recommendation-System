# app.py
# Main Flask web application

from flask import Flask, render_template, request
from scraper import scrape_products
from analyzer import process_products
from database import init_db, save_products, get_products_by_query, clear_old_results, get_global_stats

import os
from dotenv import load_dotenv

# Load .env from the same directory as this script (works from any cwd)
dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(dotenv_path)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-fallback-key-change-in-prod')

# Initialize database when app starts
init_db()

key = os.getenv("SERPAPI_KEY")
print(f"--- SYSTEM STARTUP ---")
print(f"API KEY DETECTED: {bool(key)}")
if key:
    print(f"API KEY START: {key[:5]}...")
print(f"----------------------")


@app.route('/')
def home():
    """Home page - shows the search form with real-time stats"""
    from database import get_global_stats
    stats = get_global_stats()
    return render_template('index.html', stats=stats)

@app.route('/dashboard')
def dashboard():
    """Dashboard page showing real database analytics"""
    from database import get_dashboard_stats, get_search_history
    stats = get_dashboard_stats()
    recent_searches = get_search_history()
    return render_template('dashboard.html', stats=stats, recent_searches=recent_searches)

@app.route('/history')
def history():
    """Search history page"""
    from database import get_search_history
    searches = get_search_history()
    return render_template('history.html', searches=searches)

@app.route('/saved')
def saved():
    """Saved products page (managed via localStorage in browser)"""
    return render_template('saved.html')


@app.route('/search', methods=['GET', 'POST'])
def search():
    """
    Handle search form submission.
    1. Get search query from form
    2. Collect product data
    3. Run AI analysis
    4. Save to database
    5. Display results
    """
    # Support both form POSTs and direct GET requests with query params
    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        category = request.form.get('category', 'All')
    else:
        # GET: accept ?query=... and optional ?category=...
        query = request.args.get('query', request.args.get('q', '')).strip()
        category = request.args.get('category', 'All')
    full_query = f"{query} {category}" if category != 'All' else query
    
    if not query:
        return render_template('index.html', error='Please enter a product name!')
    
    # --- CACHING LOGIC ---
    try:
        from datetime import datetime, timedelta
        cached_results = get_products_by_query(query)
        # ONLY use cache if it actually has products in it!
        if cached_results and len(cached_results) > 0:
            try:
                last_created_str = cached_results[0].get('created_at')
                if last_created_str:
                    last_created = datetime.strptime(last_created_str, '%Y-%m-%d %H:%M:%S')
                    if datetime.now() - last_created < timedelta(minutes=60):
                        print(f"[Cache Hit] Found {len(cached_results)} fresh results for: {query}")
                        best_product = cached_results[0]
                        valid_prices = [p['price'] for p in cached_results if p.get('price')]
                        return render_template(
                            'results.html',
                            products=cached_results,
                            best_product=best_product,
                            query=query,
                            total=len(cached_results),
                            average_price=sum(valid_prices) / len(valid_prices) if valid_prices else 0,
                            lowest_price=min(valid_prices) if valid_prices else 0
                        )
            except Exception as e:
                print(f"[Cache Warning] Could not parse timestamp, doing live search: {e}")
        else:
            print(f"[Cache Miss] No fresh results found in DB for: {query}")
    except Exception as e:
        print(f"[Cache Error] Database lookup failed: {e}")
    # --- END CACHING LOGIC ---
    
    # Step 1: Collect raw product data
    print(f'---> PERFORMING LIVE API SEARCH FOR: {query}')
    scraper_error = None
    try:
        raw_products = scrape_products(query if category == 'All' else f"{query} {category}")
    except Exception as e:
        scraper_error = str(e)
        print(f"[Search Error] {scraper_error}")
        raw_products = []
    
    if not raw_products:
        error_msg = scraper_error or "No products found for this search. Try different keywords."
        print(f"[Search] Returning no results with error: {error_msg}")
        return render_template(
            'results.html', 
            products=[], 
            query=query, 
            total=0, 
            error=error_msg
        )
    
    # Step 2: Run AI analysis
    try:
        analyzed_products = process_products(raw_products)
    except Exception as e:
        print(f"Analysis error: {e}")
        analyzed_products = raw_products 
    
    # Step 3: Persistence
    try:
        clear_old_results(query)
        save_products(analyzed_products)
    except Exception as e:
        print(f"Database save error: {e}")
    
    # Step 4: Get best product & statistics
    best_product = analyzed_products[0] if analyzed_products else None
    valid_prices = [p['price'] for p in analyzed_products if p.get('price')]
    average_price = sum(valid_prices) / len(valid_prices) if valid_prices else 0
    lowest_price = min(valid_prices) if valid_prices else 0
    
    # Step 5: Render results page
    return render_template(
        'results.html',
        products=analyzed_products,
        best_product=best_product,
        query=query,
        total=len(analyzed_products),
        average_price=average_price,
        lowest_price=lowest_price
    )


# Run the app
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5008))
    debug_flag = os.environ.get('FLASK_DEBUG', 'false').lower() in ('1', 'true', 'yes')
    app.run(host='0.0.0.0', port=port, debug=debug_flag)
