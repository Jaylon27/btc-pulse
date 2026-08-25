import requests
import sqlite3
import datetime
import os

# Get the directory where pipeline.py lives
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

KRAKEN_URL = "https://api.kraken.com/0/public/Ticker"
# Use the mempool.space JSON API for recommended fee estimates
MEMPOOL_URL = "https://mempool.space/api/v1/fees/recommended"

PARAMS = {"pair": "XBTUSD"}
DB_NAME = os.path.join(BASE_DIR, "bitcoin_price_data.db")

def init_db():
    """Creates the SQLite database and table if they do not exist."""
    # This connects to the file. If it doesn't exist, SQLite creates it automatically.
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Create a table matching your required schema
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS btc_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            source TEXT NOT NULL,
            price REAL NOT NULL
        )
    ''')

    # Table to store mempool fee estimates (allow NULL for economy_fee if not provided)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS btc_fees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            fastest_fee REAL,
            half_hour_fee REAL,
            hour_fee REAL,
            economy_fee REAL
        )
    ''')

    conn.commit()
    conn.close()

def fetch_current_price():
    try:
        response = requests.get(KRAKEN_URL, params=PARAMS)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        print(data)

        # Extract the Spot Price
        # Kraken's payload nests data under the asset pair name.
        # Use the first item in `result` to avoid depending on a specific key name.
        try:
            ticker_data = next(iter(data["result"].values()))
        except (KeyError, StopIteration):
            raise KeyError("Unexpected response structure from Kraken API")

        current_price_str = ticker_data["c"][0]
        current_price = float(current_price_str)

        print(f"✅ Connection Successful!")
        return current_price

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except KeyError:
        print("Error: Could not parse the expected keys from Kraken's response payload.")
        print("Raw Response:", data)
    except Exception as err:
        print(f"An unexpected error occurred: {err}")

def fetch_mempool_fees():
    """Fetches recommended fee estimates from Mempool.space."""
    response = requests.get(MEMPOOL_URL, timeout=10)
    response.raise_for_status()
    return response.json()

def insert_data(price, fee_data):
    """Inserts a price record into the SQLite database."""
    # Capture the exact current time in UTC ISO format (YYYY-MM-DD HH:MM:SS)
    current_time = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Insert data safely using parameterized queries to prevent SQL injection
    cursor.execute('''
        INSERT INTO btc_prices (timestamp, source, price)
        VALUES (?, 'Kraken', ?)
    ''', (current_time, price))

    # Normalize fee fields and allow missing economy fee
    fastest = fee_data.get("fastestFee")
    half_hour = fee_data.get("halfHourFee")
    hour = fee_data.get("hourFee")
    economy = fee_data.get("economyFee")

    cursor.execute('''
        INSERT INTO btc_fees (timestamp, fastest_fee, half_hour_fee, hour_fee, economy_fee)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        current_time,
        fastest,
        half_hour,
        hour,
        economy
    ))
    
    conn.commit()
    conn.close()
    print(f"📥 Saved data at {current_time} UTC | Price: ${price:,.2f} | Next Block Fee: {fee_data['fastestFee']} sat/vB")

def main():
    try:
        # Initialize the database table
        init_db()
        
        # Run extraction and loading
        price = fetch_current_price()
        fee_data = fetch_mempool_fees()
        insert_data(price, fee_data)

    except Exception as e:
        print(f"❌ Pipeline failed: {e}")

if __name__ == "__main__":
    main()