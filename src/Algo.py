# Code created and edited using Gemini, originally based on pseudocode I designed

import os
import time
from datetime import datetime
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame
from dotenv import load_dotenv 

load_dotenv() # This line loads the variables from the .env file

# --- Configuration ---
API_KEY = os.getenv('ALPACA_API_KEY')
SECRET_KEY = os.getenv('ALPACA_SECRET_KEY')

# Initialize the Data Client
try:
    data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
    trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)
except ValueError as e:
    print(f"Authentication Error: {e}")
    exit()

# --- Binary Tree Implementation ---
class PriceNode:
    def __init__(self, price):
        self.price = price
        self.timestamp = datetime.now()
        self.left = None
        self.right = None

class StockPriceTree:
    def __init__(self):
        self.root = None

    def insert(self, price):
        if not self.root:
            self.root = PriceNode(price)
        else:
            self._insert_recursive(self.root, price)

    def _insert_recursive(self, current_node, price):
        if price < current_node.price:
            if current_node.left is None:
                current_node.left = PriceNode(price)
            else:
                self._insert_recursive(current_node.left, price)
        else:
            if current_node.right is None:
                current_node.right = PriceNode(price)
            else:
                self._insert_recursive(current_node.right, price)

    def find_min(self, node):
        current = node
        while current and current.left is not None:
            current = current.left
        return current.price if current else None

    def find_max(self, node):
        current = node
        while current and current.right is not None:
            current = current.right
        return current.price if current else None


# --- Bot Functions ---
def get_ipo_price(symbol):
    """Fetches the opening price of the first day the stock traded."""
    try:
        request_params = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=datetime(1970, 1, 1),
            limit=1, 
            feed='iex'
        )
        bars = data_client.get_stock_bars(request_params)
        ipo_price = bars[symbol][0].open
        print(f"IPO/First Trade Price for {symbol}: ${ipo_price}")
        return ipo_price
    except Exception as e:
        print(f"Could not fetch IPO price: {e}")
        return None

def get_live_prices(symbol):
    """Fetches the most recent price for the symbol."""
    try:
        request_params = StockLatestQuoteRequest(symbol_or_symbols=symbol, feed='iex')
        quote = data_client.get_stock_latest_quote(request_params)
        current_price = quote[symbol].ask_price
        return [current_price]
    except Exception as e:
        print(f"Error fetching live price: {e}")
        return [0]

def execute_trade_logic(symbol, current_price, original_price, price_tree):
    """Analyzes prices using both the baseline IPO price and our tracking tree."""
    print(f"\nAnalyzing {symbol}: Current ${current_price} vs Original ${original_price}")
    
    # Insert the brand new live price into our Binary Search Tree
    price_tree.insert(current_price)
    
    # Query the tree for analysis metrics
    lowest_recorded = price_tree.find_min(price_tree.root)
    highest_recorded = price_tree.find_max(price_tree.root)
    
    print(f"-> Tree Stats for session: Min: ${lowest_recorded} | Max: ${highest_recorded}")
    
    # Future Trading Logic Example:
    # if current_price <= lowest_recorded:
    #     print("Price is at an all-time low for this session. Buy trigger?")

def run_bot():
    print(f"Starting bot for {SYMBOL}...")
    
    # Initialize an empty tree specifically for this session's tracking
    session_tree = StockPriceTree()
    
    try:
        # Fetch data
        prices_list = get_live_prices(SYMBOL)
        live_price = prices_list[-1]
            
        # Run your trade logic, passing our tracking tree into it
        execute_trade_logic(SYMBOL, live_price, ORIGINAL_PRICE, session_tree)
               
    except Exception as e:
        print(f"Main Loop Error: {e}")

if __name__ == "__main__":
    SYMBOL = "AAPL"
    ORIGINAL_PRICE = get_ipo_price(SYMBOL)
    
    if ORIGINAL_PRICE:
        run_bot() 
    else:
        print("Failed to initialize original price. Exiting.")

        # pip install command:  C:/Users/S1855921/AppData/Local/Python/pythoncore-3.14-64/python.exe -m pip install alpaca-trade-api