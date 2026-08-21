import os
import time
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

# Import your existing utility (ensure this path is correct in your repo)
try:
    from utils.status import getStatus
except ImportError:
    # Fallback in case the import path differs in the GitHub Actions environment
    def getStatus(open_price, close_price):
        if close_price > open_price:
            return 1
        elif close_price < open_price:
            return -1
        return 0

# Configuration
CSV_FILE_PATH = Path("../data/nepse.csv")  # Adjust if your GitHub Actions working directory differs
SHARE_SANSAR_URL = "https://www.sharesansar.com/index-history-data"
INDEX_ID = "12"  # NEPSE Index ID

def update_nepse_index():
    if not os.path.exists(CSV_FILE_PATH):
        print(f"❌ CSV file not found at {CSV_FILE_PATH}")
        return

    # 1. Read existing data to find the last recorded date
    df_existing = pd.read_csv(CSV_FILE_PATH)
    last_date_str = str(df_existing["published_date"].iloc[-1])
    last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
    
    # 2. Define the date range to fetch (from the day after the last record to today)
    start_date = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    print(f"🔍 Checking for new NEPSE index data from {start_date} to {end_date}...")

    # 3. Setup requests session with headers to mimic a real browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": "https://www.sharesansar.com/index-history-data"
    }

    session = requests.Session()
    session.headers.update(headers)
    session.get("https://www.sharesansar.com/index-history-data")  # Warm up cookies

    # 4. Fetch data from ShareSansar API
    params = {
        "index_id": INDEX_ID,
        "from": start_date,
        "to": end_date,
        "draw": 1,
        "start": 0,
        "length": 50  # Safe for daily updates. If run is delayed >50 days, increase this or add pagination.
    }

    response = session.get(SHARE_SANSAR_URL, params=params)
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch data. HTTP Status: {response.status_code}")
        return

    data = response.json()
    records = data.get('data', [])

    if not records:
        print("✅ No new data found. CSV is up to date.")
        return

    # 5. Format new records to match your CSV structure
    new_rows = []
    for row in records:
        date_str = row['published_date']
        open_price = float(row['open'].replace(',', '')) if row['open'] else 0.0
        high = float(row['high'].replace(',', '')) if row['high'] else 0.0
        low = float(row['low'].replace(',', '')) if row['low'] else 0.0
        close = float(row['current'].replace(',', '')) if row['current'] else 0.0
        per_change = float(row['per_change']) if row['per_change'] else 0.0
        
        # Note: ShareSansar's index API does not provide total traded quantity (volume), 
        # only turnover. We set it to 0.0 to maintain the exact CSV column structure.
        traded_quantity = 0.0 
        traded_amount = float(row['turnover'].replace(',', '')) if row['turnover'] else 0.0
        
        status = getStatus(open_price, close)
        
        new_rows.append({
            'published_date': date_str,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'per_change': per_change,
            'traded_quantity': traded_quantity,
            'traded_amount': traded_amount,
            'status': status
        })

    # 6. Append to CSV
    if new_rows:
        new_df = pd.DataFrame(new_rows)
        # Ensure chronological order before appending
        new_df = new_df.sort_values('published_date')
        
        new_df.to_csv(CSV_FILE_PATH, mode='a', header=False, index=False)
        print(f"🎉 Successfully appended {len(new_df)} new record(s) to {CSV_FILE_PATH}")
    else:
        print("✅ No new records to append.")

if __name__ == "__main__":
    update_nepse_index()
