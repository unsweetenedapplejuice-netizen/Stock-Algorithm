# Code created and edited using Gemini, originally based on pseudocode I designed
#from alpaca.trading.client import TradingClient
#from alpaca.trading.requests import MarketOrderRequest, GetOrdersRequest
#from alpaca.trading.enums import OrderSide, TimeInForce
#from datetime import datetime

## --- Configuration ---
#API_KEY = 'YOUR_PAPER_API_KEY'
#SECRET_KEY = 'YOUR_PAPER_SECRET_KEY'
#PAPER = True # Set to False for live trading

## The new SDK uses TradingClient
#trading_client = TradingClient(API_KEY, SECRET_KEY, paper=PAPER)

## Persistent state
#internal_date = datetime.now().date()
#transaction_count = 0

#def execute_trade_logic(symbol, prices_list, original_price):
#    global transaction_count, internal_date
    
#    # 1. Date Reset
#    current_date = datetime.now().date()
#    if current_date != internal_date:
#        transaction_count = 0
#        internal_date = current_date

#    # 2. Extract Prices
#    price = prices_list[-1]
#    yesterdays_price = prices_list[-2]
    
#    buy = False
#    sell = False
#    transaction_occurred = False

#    # 3. Strategy Logic
#    if transaction_count < 30:
#        if price >= (original_price + 300):
#            if price > yesterdays_price:
#                buy = True
#            elif price < yesterdays_price:
#                sell = True
#        elif price < original_price:
#            if price < yesterdays_price:
#                sell = True
#            else:
#                buy = True

#    # 4. Execution with alpaca-py
#    try:
#        if buy:
#            # Create a MarketOrderRequest object
#            market_order_data = MarketOrderRequest(
#                symbol=symbol,
#                qty=2,
#                side=OrderSide.BUY,
#                time_in_force=TimeInForce.GTC
#            )
#            trading_client.submit_order(order_data=market_order_data)
#            print(f"Bought 2 shares of {symbol}")
#            transaction_occurred = True
            
#        elif sell:
#            # New SDK has a dedicated method to close an entire position
#            try:
#                trading_client.close_position(symbol)
#                print(f"Sold all shares of {symbol}")
#                transaction_occurred = True
#            except Exception:
#                print("No active position to sell.")

#        # 5. Counter update
#        if transaction_occurred:
#            transaction_count += 1
            
#    except Exception as e:
#        print(f"Error: {e}")

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

if __name__ == "__main__":
    # Get the IPO price once when the bot starts
    ORIGINAL_PRICE = get_ipo_price(SYMBOL)
    
    if ORIGINAL_PRICE:
        run_bot() # Start your loop
    else:
        print("Failed to initialize original price. Exiting.")

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
    run_bot()