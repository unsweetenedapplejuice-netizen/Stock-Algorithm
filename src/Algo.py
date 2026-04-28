# Code created and edited using Gemini, originally based on pseudocode I designed

import time
from datetime import datetime
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

# --- Configuration ---
API_KEY = 'YOUR_API_KEY'
SECRET_KEY = 'YOUR_SECRET_KEY'

# Initialize the Data Client
data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

def get_ipo_price(symbol):
    """Fetches the opening price of the first day the stock traded."""
    try:
        # Request the first daily bar since 1970
        request_params = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=datetime(1970, 1, 1),
            limit=1 # We only want the very first bar
        )
        
        bars = data_client.get_stock_bars(request_params)
        
        # Extract the opening price of that first bar
        ipo_price = bars[symbol][0].open
        print(f"IPO/First Trade Price for {symbol}: ${ipo_price}")
        return ipo_price
        
    except Exception as e:
        print(f"Could not fetch IPO price: {e}")
        return None

# --- Usage in your main script ---
SYMBOL = "AAPL"

# Initialize Clients
trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)
data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

def get_live_prices(symbol):
    """Fetches the last 5 minutes of bar data to create the prices_list"""
    request_params = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Minute,
        limit=5  # We only need the last few for current and 'yesterday' (previous)
    )
    bars = data_client.get_stock_bars(request_params)
    # Convert bars to a simple list of closing prices
    return [bar.close for bar in bars[symbol]]

def run_bot():
    print(f"Starting bot for {SYMBOL}...")
    while True:
        try:
            # 1. Fetch data
            prices_list = get_live_prices(SYMBOL)
            
            # 2. Run your trade logic (The function we built previously)
            # This will check conditions and submit orders if necessary
            execute_trade_logic(SYMBOL, prices_list, ORIGINAL_PRICE)
            
            # 3. Wait before the next check (e.g., 60 seconds)
            print(f"Check complete. Current price: {prices_list[-1]}. Waiting...")
            time.sleep(60) 
            
        except Exception as e:
            print(f"Main Loop Error: {e}")
            time.sleep(10) # Wait a bit before retrying on error

if __name__ == "__main__":
    # Get the IPO price once when the bot starts
    ORIGINAL_PRICE = get_ipo_price(SYMBOL)
    
    if ORIGINAL_PRICE:
        run_bot() # Start your loop
    else:
        print("Failed to initialize original price. Exiting.")

        # pip install command:  C:/Users/S1855921/AppData/Local/Python/pythoncore-3.14-64/python.exe -m pip install alpaca-trade-api