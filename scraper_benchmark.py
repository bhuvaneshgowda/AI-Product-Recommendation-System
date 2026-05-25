from scraper import scrape_products
import time

if __name__ == '__main__':
    query = 'laptop'
    start = time.perf_counter()
    results = scrape_products(query)
    elapsed = time.perf_counter() - start
    print(f"elapsed={elapsed:.2f}s")
    print(f"count={len(results)}")
    if results:
        print(f"first={results[0]['name']}")
