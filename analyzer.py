# analyzer.py
# AI module: Sentiment Analysis + Product Scoring

from textblob import TextBlob
import nltk

# Download required NLTK data (only needed once)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

def analyze_sentiment(review_text):
    """
    Analyze the sentiment of a review.
    Returns a score between -1.0 (very negative) and +1.0 (very positive)
    0.0 means neutral.
    """
    if not review_text or review_text.strip() == '':
        return 0.0
    
    analysis = TextBlob(review_text)
    return round(analysis.sentiment.polarity, 3)

def get_sentiment_label(score):
    """Convert sentiment score to human-readable label"""
    if score >= 0.3:
        return 'Positive'
    elif score <= -0.1:
        return 'Negative'
    else:
        return 'Neutral'

def calculate_final_score(product, min_price, max_price):
    """
    Calculate a final recommendation score for a product.
    Returns a score between 0 and 100 based on user-defined weights:
    - Price: 40%
    - Rating: 35%
    - Sentiment: 20%
    - Discount: 5%
    """
    # --- Price Score (40 points max) ---
    price = float(product.get('price'))
    if max_price > min_price:
        price_score = (1 - (price - min_price) / (max_price - min_price)) * 40
    else:
        price_score = 40  # If all prices are the same, they get max price score
            
    # --- Rating Score (35 points max) ---
    rating = product.get('rating')
    if rating is None:
        calc_rating = 3.5  # Neutral rating for missing data scoring ONLY
    else:
        calc_rating = float(rating)
    rating_score = (calc_rating / 5.0) * 35
    
    # --- Sentiment Score (20 points max) ---
    sentiment = product.get('sentiment_score', 0.0)
    sentiment_score = ((sentiment + 1) / 2) * 20
    
    # --- Discount Bonus (5 points max) ---
    discount = float(product.get('discount_percent', 0))
    discount_bonus = min(discount / 20, 5)
    
    final = price_score + rating_score + sentiment_score + discount_bonus
    return round(final, 2)

def generate_explanation(product, is_best_price):
    """Generates a clear user-friendly explanation of why a product is recommended."""
    reasons = []
    
    if is_best_price:
        reasons.append("Best price.")
    if product.get('rating') and float(product['rating']) >= 4.0:
        reasons.append("Good rating.")
    if product.get('sentiment_label') == 'Positive':
        reasons.append("Positive sentiment.")
    if product.get('discount_percent', 0) > 0:
        reasons.append("Discount available.")
        
    if not reasons:
        reasons.append("Solid overall choice.")
        
    return " ".join(reasons)

def process_products(products_list):
    """
    Process all products: validate, run sentiment analysis, and calculate scores.
    Returns the processed list sorted by final score (best first).
    """
    print(f"[Analyzer] Processing {len(products_list)} products...")
    valid_products = []
    
    # 1. First Pass: Validate and Filter
    for p in products_list:
        if not p.get('name') or str(p['name']).strip() == '':
            continue
        if not p.get('price') or float(p['price']) <= 0:
            continue
        if not p.get('product_url'):
            continue
        if not p.get('platform'):
            continue
            
        valid_products.append(p)
        
    if not valid_products:
        print("[Analyzer] ERROR: No products passed validation (Check names/prices/URLs)")
        return []
    
    print(f"[Analyzer] {len(valid_products)} products passed validation.")
    
    # Calculate price extremes for scaling
    prices = [float(p['price']) for p in valid_products]
    min_price = min(prices)
    max_price = max(prices)
    
    processed = []
    for product in valid_products:
        # Step 1: Sentiment Analysis
        sentiment = analyze_sentiment(product.get('review_text', ''))
        product['sentiment_score'] = sentiment
        product['sentiment_label'] = get_sentiment_label(sentiment)
        
        # Step 2: Scoring
        product['final_score'] = calculate_final_score(product, min_price, max_price)
        
        # Step 3: Explanation
        is_best_price = (float(product['price']) == min_price)
        product['explanation'] = generate_explanation(product, is_best_price)
        
        processed.append(product)
    
    # Sort by final score descending
    processed.sort(key=lambda x: x['final_score'], reverse=True)
    
    return processed
