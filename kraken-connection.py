import requests

URL = "https://api.kraken.com/0/public/Ticker"
PARAMS = {"pair": "XBTUSD"}

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
    print(f"Current Kraken BTC Price: ${current_price:,.2f} USD")

except requests.exceptions.HTTPError as http_err:
    print(f"HTTP error occurred: {http_err}")
except KeyError:
    print("Error: Could not parse the expected keys from Kraken's response payload.")
    print("Raw Response:", data)
except Exception as err:
    print(f"An unexpected error occurred: {err}")