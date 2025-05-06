import os
import json
from datetime import datetime

# Define the tickers you want to cache
TICKERS = ['SXR8.DE','EUNL.DE',  'LIRU.DE', 'MEUD.PA']
actual_prices = [528.59, 95.33, 83.21, 254.50]
QUANTITY = [1,1,1,1]

# Create cache directory
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)
    print(f"Created cache directory: {CACHE_DIR}")
i = 0
# Create initial cache files with dummy data
for ticker in TICKERS:
    cache_file = os.path.join(CACHE_DIR, f"{ticker.replace('/', '_').replace(':', '_')}.json")
    
    # Create initial cache data
    initial_data = {
        'ticker': ticker,
        'last_close': actual_prices[i]*QUANTITY[i],  # Dummy value
        'last_date': datetime.now().strftime('%Y-%m-%d'),
        'last_datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'dates': [datetime.now().strftime('%Y-%m-%d')],
        'values': [actual_prices[i]*QUANTITY[i]]  # Dummy value
    }
    i += 1
    # Write to cache file
    try:
        with open(cache_file, 'w') as f:
            json.dump(initial_data, f)
        print(f"Created initial cache for {ticker} at {cache_file}")
    except Exception as e:
        print(f"Error creating cache for {ticker}: {e}")

print("Cache initialization complete. You can now run your application with initial cached data.")