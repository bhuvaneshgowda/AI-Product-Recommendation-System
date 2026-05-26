# database.py
# Handles all SQLite database operations for the AI Product Recommender

import sqlite3
import os

# Path to database file — cloud-aware
# Vercel has a read-only filesystem; only /tmp is writable
if os.environ.get('VERCEL'):
    DB_PATH = '/tmp/data/products.db'
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'products.db')


def get_connection():
    """Return a database connection with Row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Create the database and products table if they don't exist.
    Also runs a safe migration to add the 'image' column if missing.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = get_connection()
    cursor = conn.cursor()

    # Create products table (includes image column for new installs)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT    NOT NULL,
            platform        TEXT    NOT NULL,
            price           REAL,
            original_price  REAL,
            discount_percent REAL,
            rating          REAL,
            num_reviews     INTEGER,
            review_text     TEXT,
            sentiment_score REAL,
            sentiment_label TEXT,
            final_score     REAL,
            explanation     TEXT,
            product_url     TEXT,
            image           TEXT,
            search_query    TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Safe Migration ────────────────────────────────────────────────────────
    # If the table already existed without the 'image' column, add it now.
    # This never deletes or alters any existing rows.
    existing_columns = [row[1] for row in cursor.execute("PRAGMA table_info(products)")]

    if 'image' not in existing_columns:
        cursor.execute("ALTER TABLE products ADD COLUMN image TEXT;")
        print("[DB Migration] Added 'image' column to existing products table.")

    if 'sentiment_label' not in existing_columns:
        cursor.execute("ALTER TABLE products ADD COLUMN sentiment_label TEXT;")
        print("[DB Migration] Added 'sentiment_label' column.")

    if 'explanation' not in existing_columns:
        cursor.execute("ALTER TABLE products ADD COLUMN explanation TEXT;")
        print("[DB Migration] Added 'explanation' column.")

    if 'created_at' not in existing_columns:
        cursor.execute("ALTER TABLE products ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
        print("[DB Migration] Added 'created_at' column.")
    # ── End Migration ─────────────────────────────────────────────────────────

    conn.commit()
    conn.close()
    print('Database initialized successfully!')


def save_products(products_list):
    """Save a list of product dictionaries to the database."""
    conn = get_connection()
    cursor = conn.cursor()

    for product in products_list:
        cursor.execute('''
            INSERT INTO products
            (name, platform, price, original_price, discount_percent,
             rating, num_reviews, review_text, sentiment_score, sentiment_label,
             final_score, explanation, product_url, image, search_query, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            product.get('name', ''),
            product.get('platform', ''),
            product.get('price') or 0,
            product.get('original_price') or 0,
            product.get('discount_percent') or 0,
            product.get('rating'),          # Keep None if not available
            product.get('num_reviews'),     # Keep None if not available
            product.get('review_text', ''),
            product.get('sentiment_score') or 0,
            product.get('sentiment_label', 'Neutral'),
            product.get('final_score') or 0,
            product.get('explanation', ''),
            product.get('product_url', ''),
            product.get('image', ''),       # Real image URL or empty string
            product.get('search_query', '')
        ))

    conn.commit()
    conn.close()


def get_products_by_query(query):
    """Fetch all cached products matching a search query, sorted by AI score."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM products
        WHERE LOWER(search_query) = LOWER(?)
        ORDER BY final_score DESC
    ''', (query,))

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def clear_old_results(query):
    """Remove old results for a query before inserting fresh ones."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM products WHERE LOWER(search_query) = LOWER(?)', (query,))
    conn.commit()
    conn.close()


def get_global_stats():
    """Return summary statistics: total products, total searches, top platform."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM products')
    total_products = cursor.fetchone()[0] or 0

    cursor.execute('SELECT COUNT(DISTINCT search_query) FROM products')
    total_searches = cursor.fetchone()[0] or 0

    cursor.execute('''
        SELECT platform, COUNT(*) as cnt
        FROM products
        GROUP BY platform
        ORDER BY cnt DESC
        LIMIT 1
    ''')
    row = cursor.fetchone()
    best_platform = row[0] if row else 'N/A'

    conn.close()
    return {
        'total_products': total_products,
        'total_searches': total_searches,
        'best_platform': best_platform
    }


def get_dashboard_stats():
    """Extended analytics for the /dashboard page."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM products')
    total_products = cursor.fetchone()[0] or 0

    cursor.execute('SELECT COUNT(DISTINCT search_query) FROM products')
    total_searches = cursor.fetchone()[0] or 0

    # Best platform by number of appearances
    cursor.execute('''
        SELECT platform, COUNT(*) as cnt
        FROM products
        GROUP BY platform
        ORDER BY cnt DESC
        LIMIT 1
    ''')
    row = cursor.fetchone()
    best_platform = row[0] if row else 'N/A'

    # Average AI Score across all products
    cursor.execute('SELECT AVG(final_score) FROM products WHERE final_score > 0')
    avg_score_row = cursor.fetchone()[0]
    avg_ai_score = round(avg_score_row, 1) if avg_score_row else 0

    # Average Price across all products
    cursor.execute('SELECT AVG(price) FROM products WHERE price > 0')
    avg_price_row = cursor.fetchone()[0]
    avg_price = round(avg_price_row, 0) if avg_price_row else 0

    # Best (Lowest) Price
    cursor.execute('SELECT MIN(price) FROM products WHERE price > 0')
    best_price_row = cursor.fetchone()[0]
    best_price = round(best_price_row, 0) if best_price_row else 0

    # Best AI Score
    cursor.execute('SELECT MAX(final_score) FROM products')
    best_score_row = cursor.fetchone()[0]
    best_ai_score = round(best_score_row, 1) if best_score_row else 0

    # Latest search query
    try:
        cursor.execute('''
            SELECT search_query FROM products
            ORDER BY created_at DESC LIMIT 1
        ''')
        latest_row = cursor.fetchone()
        latest_search = latest_row[0] if latest_row else 'None yet'
    except Exception:
        cursor.execute('SELECT search_query FROM products ORDER BY id DESC LIMIT 1')
        latest_row = cursor.fetchone()
        latest_search = latest_row[0] if latest_row else 'None yet'

    # Platform breakdown
    cursor.execute('''
        SELECT platform, COUNT(*) as cnt
        FROM products
        GROUP BY platform
        ORDER BY cnt DESC
        LIMIT 8
    ''')
    platform_breakdown = [{'platform': r[0], 'count': r[1]} for r in cursor.fetchall()]

    # Sentiment breakdown
    cursor.execute('SELECT COUNT(*) FROM products WHERE sentiment_label = "Positive"')
    pos_count = cursor.fetchone()[0] or 0
    cursor.execute('SELECT COUNT(*) FROM products WHERE sentiment_label = "Neutral"')
    neu_count = cursor.fetchone()[0] or 0
    cursor.execute('SELECT COUNT(*) FROM products WHERE sentiment_label = "Negative"')
    neg_count = cursor.fetchone()[0] or 0

    conn.close()
    return {
        'total_products': total_products,
        'total_searches': total_searches,
        'best_platform': best_platform,
        'avg_ai_score': avg_ai_score,
        'avg_price': avg_price,
        'best_price': best_price,
        'best_ai_score': best_ai_score,
        'latest_search': latest_search,
        'platform_breakdown': platform_breakdown,
        'sentiment_breakdown': {
            'positive': pos_count,
            'neutral': neu_count,
            'negative': neg_count
        }
    }



def get_search_history():
    """Return a list of recent unique searches with aggregate stats."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT
                search_query              AS query,
                MAX(created_at)           AS date,
                COUNT(*)                  AS product_count,
                MIN(price)                AS best_price,
                (
                    SELECT platform
                    FROM   products p2
                    WHERE  p2.search_query = p1.search_query
                    ORDER  BY final_score DESC
                    LIMIT  1
                ) AS best_platform
            FROM  products p1
            GROUP BY search_query
            ORDER BY date DESC
            LIMIT 50
        ''')
    except Exception:
        # Fallback: database may not have created_at column yet
        cursor.execute('''
            SELECT
                search_query              AS query,
                MAX(id)                   AS date,
                COUNT(*)                  AS product_count,
                MIN(price)                AS best_price,
                (
                    SELECT platform
                    FROM   products p2
                    WHERE  p2.search_query = p1.search_query
                    ORDER  BY final_score DESC
                    LIMIT  1
                ) AS best_platform
            FROM  products p1
            GROUP BY search_query
            ORDER BY date DESC
            LIMIT 50
        ''')

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results

