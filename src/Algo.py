# Code created and edited using Gemini, originally based on pseudocode I designed

import os
from datetime import datetime, timedelta
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('ALPACA_API_KEY')
SECRET_KEY = os.getenv('ALPACA_SECRET_KEY')

try:
    data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
    trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)
except ValueError as e:
    print(f"Authentication Error: {e}")
    exit()

# --- Binary Tree Requirement ---
class PriceNode:
    def __init__(self, label, price):
        self.label = label
        self.price = price
        self.left = None
        self.right = None

class StockPriceTree:
    def __init__(self):
        self.root = None

    def insert(self, label, price):
        if not self.root:
            self.root = PriceNode(label, price)
        else:
            self._insert_recursive(self.root, label, price)

    def _insert_recursive(self, current_node, label, price):
        if price < current_node.price:
            if current_node.left is None:
                current_node.left = PriceNode(label, price)
            else:
                self._insert_recursive(current_node.left, label, price)
        else:
            if current_node.right is None:
                current_node.right = PriceNode(label, price)
            else:
                self._insert_recursive(current_node.right, label, price)

    def search_by_label(self, node, target_label):
        if node is None:
            return None
        if node.label == target_label:
            return node.price
        
        left_res = self.search_by_label(node.left, target_label)
        if left_res is not None:
            return left_res
        return self.search_by_label(node.right, target_label)


# --- Data Fetching Functions ---
def get_ipo_price(symbol):
    try:
        request_params = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=datetime(1970, 1, 1),
            limit=1, 
            feed='iex'
        )
        bars = data_client.get_stock_bars(request_params)
        return bars[symbol][0].open
    except Exception as e:
        print(f"Could not fetch IPO price: {e}")
        return None

def get_yesterday_close(symbol):
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=5) 
        request_params = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=start_date,
            end=end_date,
            feed='iex'
        )
        bars = data_client.get_stock_bars(request_params)
        return bars[symbol][-1].close
    except Exception as e:
        print(f"Error fetching yesterday's closing price: {e}")
        return None

def get_live_price(symbol):
    try:
        request_params = StockLatestQuoteRequest(symbol_or_symbols=symbol, feed='iex')
        quote = data_client.get_stock_latest_quote(request_params)
        return quote[symbol].ask_price
    except Exception as e:
        print(f"Error fetching live price: {e}")
        return None

def get_daily_transaction_count():
    try:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        params = GetOrdersRequest(status=QueryOrderStatus.ALL, after=today_start)
        orders = trading_client.get_orders(filter_params=params)
        return len(orders)
    except Exception as e:
        print(f"Error checking daily transaction count: {e}")
        return 999  


# --- Order Execution ---
def execute_market_order(symbol, qty, side_type):
    try:
        order_data = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=side_type,
            time_in_force=TimeInForce.GTC
        )
        trading_client.submit_order(order_data=order_data)
        print(f"SUCCESS: Market {side_type.value.upper()} order placed for {qty} shares of {symbol}.")
    except Exception as e:
        print(f"Failed to execute trade order: {e}")


# --- Core Logic Pipeline ---
def execute_trade_logic(symbol, tree):
    current_price = tree.search_by_label(tree.root, "current")
    original_price = tree.search_by_label(tree.root, "original")
    yesterday_price = tree.search_by_label(tree.root, "yesterday")

    print(f"\n--- Strategy Analysis for {symbol} ---")
    print(f"Current Price:   ${current_price:.2f}")
    print(f"Original Price:  ${original_price:.2f} (Target High: ${original_price + 300:.2f})")
    print(f"Yesterday Close: ${yesterday_price:.2f}")

    # Check daily limit threshold
    trades_today = get_daily_transaction_count()
    print(f"Daily Transactions: {trades_today}/30")
    if trades_today >= 30:
        print("Daily transaction limit reached or exceeded. Skipping trade execution.")
        return

    # --- Market Open/Closed Guard ---
    try:
        clock = trading_client.get_clock()
        if not clock.is_open:
            print(f"MARKET CLOSED: Analysis complete, but no orders placed. Next open: {clock.next_open}")
            return
    except Exception as e:
        print(f"Warning: Could not check market clock via API ({e}). Proceeding anyway...")

    buy_trigger = False
    sell_trigger = False

    if current_price >= (original_price + 300):
        if current_price > yesterday_price:
            buy_trigger = True
        elif current_price < yesterday_price:
            sell_trigger = True
            
    elif current_price < original_price:
        if current_price < yesterday_price:
            sell_trigger = True
        else:
            buy_trigger = True
            
    else:
        buy_trigger = True

    if buy_trigger:
        print("Decision: BUY condition met.")
        execute_market_order(symbol, qty=2, side_type=OrderSide.BUY)
    elif sell_trigger:
        print("Decision: SELL ALL condition met.")
        try:
            position = trading_client.get_open_position(symbol)
            qty_to_sell = int(position.qty)
            if qty_to_sell > 0:
                execute_market_order(symbol, qty=qty_to_sell, side_type=OrderSide.SELL)
            else:
                print("Sell signal triggered, but current paper position size is 0.")
        except Exception:
            print("No open positions found to liquidate for this asset.")
    else:
        print("Decision: HOLD (No strategic criteria triggered).")


def run_bot():
    print(f"Bot session initialized at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    original_price = get_ipo_price(SYMBOL)
    yesterday_price = get_yesterday_close(SYMBOL)
    current_price = get_live_price(SYMBOL)
    
    if not all([original_price, yesterday_price, current_price]):
        print("Error: Missing critical price streams. Terminating runner.")
        return

    price_tree = StockPriceTree()
    price_tree.insert("original", original_price)
    price_tree.insert("yesterday", yesterday_price)
    price_tree.insert("current", current_price)
    
    execute_trade_logic(SYMBOL, price_tree)

if __name__ == "__main__":
    SYMBOL = "AAPL"
    run_bot()
# pip install command:  C:/Users/S1855921/AppData/Local/Python/pythoncore-3.14-64/python.exe -m pip install alpaca-trade-api