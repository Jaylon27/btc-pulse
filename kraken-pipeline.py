import requests
import sqlite3
import datetime
import os

# Get the directory where pipeline.py lives
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

URL = "https://api.kraken.com/0/public/Ticker"
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

    conn.commit()
    conn.close()

def fetch_current_price():
    try:
        response = requests.get(URL, params=PARAMS)
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

def insert_price(price, source="Kraken"):
    """Inserts a price record into the SQLite database."""
    # Capture the exact current time in UTC ISO format (YYYY-MM-DD HH:MM:SS)
    current_time = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Insert data safely using parameterized queries to prevent SQL injection
    cursor.execute('''
        INSERT INTO btc_prices (timestamp, source, price)
        VALUES (?, ?, ?)
    ''', (current_time, source, price))
    
    conn.commit()
    conn.close()
    print(f"📥 Saved to DB: ${price:,.2f} from {source} at {current_time} UTC")

def main():
    try:
        # Initialize the database table
        init_db()
        
        # Run extraction and loading
        price = fetch_current_price()
        insert_price(price)
        
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")

if __name__ == "__main__":
    main()