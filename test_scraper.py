#!/usr/bin/env python
"""Test script to debug the scraper"""

import os
import sys
from dotenv import load_dotenv
from scraper import scrape_products

load_dotenv()

print("=== SCRAPER TEST ===")
print(f"API Key Available: {bool(os.getenv('SERPAPI_KEY'))}")
print(f"API Key Length: {len(os.getenv('SERPAPI_KEY', ''))}")

# Test with a simple search
test_queries = ["laptop"]  # Only test one query to avoid hanging

for query in test_queries:
    print(f"\n--- Testing: {query} ---")
    try:
        results = scrape_products(query)
        print(f"Results found: {len(results)}")
        if results:
            print(f"First result: {results[0].get('name', 'N/A')}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
