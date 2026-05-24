# Code created and edited using Gemini, originally based on pseudocode I designed

import os
from datetime import datetime, timedelta
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest, StockLatestBarRequest, StockSnapshotRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.common.enums import Sort
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

    def inorder_traversal(self, node, result_list=None):
        if result_list is None:
            result_list = []
        if node:
            self.inorder_traversal(node.left, result_list)
            result_list.append((node.label, node.price))
            self.inorder_traversal(node.right, result_list)
        return result_list


# --- Data Fetching Functions ---
def get_stock_baselines(symbol):
    """Fetches all three required prices for the BST in a single, weekend-proof call."""
    try:
        request_params = StockSnapshotRequest(symbol_or_symbols=symbol, feed='iex')
        snapshot = data_client.get_stock_snapshot(request_params)
        
        if symbol in snapshot and snapshot[symbol]:
            snap = snapshot[symbol]
            
            # 1. Live Price (Uses last known ask price)
            current_price = snap.latest_quote.ask_price if snap.latest_quote else None
            
            # 2. Yesterday Close (Uses Friday's closing price)
            yesterday_price = snap.daily_bar.close if snap.daily_bar else None
            
            # 3. Original Anchor (Uses Friday's opening price as a stable baseline)
            original_price = snap.daily_bar.open if snap.daily_bar else None
            
            # If IEX is missing the daily bar details for Ford, use the quote as a fallback
            if not original_price and current_price:
                original_price = current_price
            if not yesterday_price and current_price:
                yesterday_price = current_price

            return original_price, yesterday_price, current_price
            
    except Exception as e:
        print(f"Error fetching snapshot baseline for {symbol}: {e}")
        
    return None, None, None

def get_daily_transaction_count():
    try:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        params = GetOrdersRequest(status=QueryOrderStatus.ALL, after=today_start)
        orders = trading_client.get_orders(filter=params)
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
        print(f"Failed to execute trade order for {symbol}: {e}")


# --- Core Logic Pipeline ---
def execute_trade_logic(symbol, price_tree, global_trade_count):
    print(f"\n--- Strategy Analysis via BST for {symbol} ---")
    
    # Check global limits before running the calculations
    if global_trade_count >= 30:
        print(f"Daily transaction limit (30) reached. Skipping strategy for {symbol}.")
        return global_trade_count

    # Flatten the specific stock's tree into ordered tracking data
    ordered_prices = price_tree.inorder_traversal(price_tree.root)
    prices = {label: price for label, price in ordered_prices}
    
    current_price = prices["current"]
    original_price = prices["original"]
    yesterday_price = prices["yesterday"]

    print(f"Current Price:   ${current_price:.2f}")
    print(f"Original Price:  ${original_price:.2f} (Target High: ${original_price + 300:.2f})")
    print(f"Yesterday Close: ${yesterday_price:.2f}")

    buy_trigger = False
    sell_trigger = False

    # Main logic execution
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

    # Execution blocks (Updates trade counter if action is taken)
    if buy_trigger:
        print("Decision: BUY condition met.")
        execute_market_order(symbol, qty=2, side_type=OrderSide.BUY)
        global_trade_count += 1
    elif sell_trigger:
        print("Decision: SELL ALL condition met.")
        try:
            position = trading_client.get_open_position(symbol)
            qty_to_sell = int(position.qty)
            if qty_to_sell > 0:
                execute_market_order(symbol, qty=qty_to_sell, side_type=OrderSide.SELL)
                global_trade_count += 1
            else:
                print("Sell signal triggered, but current paper position size is 0.")
        except Exception:
            print(f"No open positions found to liquidate for {symbol}.")
    else:
        print("Decision: HOLD (No strategic criteria triggered).")
        
    return global_trade_count


def run_bot(watchlist):
    print(f"Bot session initialized at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check how many orders have already happened today via API
    total_trades_today = get_daily_transaction_count()
    print(f"Initial Account Trade Count for Today: {total_trades_today}/30")
    
    if total_trades_today >= 30:
        print("Daily account limit already maximized. Exiting runner script.")
        return

    # --- DICTIONARY IMPLEMENTATION ---
    # Key: Ticker String | Value: Custom StockPriceTree Instance
    portfolio_registry = {}

    # Step 1: Gather and isolate data structures into the dictionary
    for symbol in watchlist:
        print(f"Fetching market baselines for {symbol}...")
        
        # Call the new unified snapshot function
        original_price, yesterday_price, current_price = get_stock_baselines(symbol)
        
        if not all([original_price, yesterday_price, current_price]):
            print(f"Skipping {symbol} due to missing data streams.")
            continue

        # Build this asset's isolated tree structure
        price_tree = StockPriceTree()
        price_tree.insert("original", original_price)
        price_tree.insert("yesterday", yesterday_price)
        price_tree.insert("current", current_price)
        
        portfolio_registry[symbol] = price_tree

    # --- MARKET OPEN GUARD ---
    try:
        clock = trading_client.get_clock()
        if not clock.is_open:
            print(f"\nMARKET CLOSED. Analysis complete for {list(portfolio_registry.keys())}. No orders sent. Next open: {clock.next_open}")
            return
    except Exception as e:
        print(f"Warning: Clock API offline ({e}). Proceeding...")

    # Step 2: Loop through the dictionary values to run calculations
    for symbol, tree in portfolio_registry.items():
        total_trades_today = execute_trade_logic(symbol, tree, total_trades_today)


if __name__ == "__main__":
    # Your brand new, multi-asset automated portfolio selection list!
    MY_WATCHLIST = ["AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "TSLA", "NFLX", "F", "META"]
    run_bot(MY_WATCHLIST)


# pip install command:  C:/Users/S1855921/AppData/Local/Python/pythoncore-3.14-64/python.exe -m pip install alpaca-trade-api