"""Fit per-stock linear models and make Alpaca paper-trading decisions.

The model predicts the close-price change over the next six stored bars.
Run without --execute to print decisions only. Orders are paper-only and
require the explicit --execute flag.
"""

import argparse
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "Stock_Linear_Regression_Database.db"
SYMBOLS = ("GOOGL", "MSFT", "TSLA")
FEATURES = ["close", "recent_return", "price_range", "volume"]
HORIZON_BARS = 6
MIN_TRAINING_ROWS = 100
HOLDOUT_FRACTION = 0.2
BAR_MINUTES = 5


def load_training_data():
    """Read the local database without modifying it and build labeled rows."""
    if not DB_PATH.is_file():
        raise FileNotFoundError(f"Training database not found: {DB_PATH}")

    database_uri = f"file:{DB_PATH.as_posix()}?mode=ro"
    connection = sqlite3.connect(database_uri, uri=True)
    try:
        frame = pd.read_sql_query(
            """
            SELECT symbol, ts_utc, open, high, low, close, volume
            FROM stock_bars
            ORDER BY symbol, ts_utc
            """,
            connection,
        )
    finally:
        connection.close()

    if frame.empty:
        raise RuntimeError("The stock_bars table contains no rows.")

    frame["ts_utc"] = pd.to_datetime(frame["ts_utc"], utc=True, errors="coerce")
    numeric_columns = ["open", "high", "low", "close", "volume"]
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["symbol", "ts_utc"] + numeric_columns)

    if frame.duplicated(["symbol", "ts_utc"]).any():
        raise RuntimeError("stock_bars contains duplicate symbol/timestamp rows.")

    missing_symbols = sorted(set(SYMBOLS) - set(frame["symbol"].unique()))
    if missing_symbols:
        raise RuntimeError(
            "The training database is missing required symbols: "
            + ", ".join(missing_symbols)
        )

    frame = frame.sort_values(["symbol", "ts_utc"]).copy()
    grouped_close = frame.groupby("symbol", sort=False)["close"]
    frame["recent_return"] = grouped_close.pct_change(
        periods=3, fill_method=None
    )
    frame["price_range"] = frame["high"] - frame["low"]
    frame["future_close"] = grouped_close.shift(-HORIZON_BARS)
    frame["target_change"] = frame["future_close"] - frame["close"]
    frame = frame.replace([float("inf"), float("-inf")], float("nan"))
    frame = frame.dropna(subset=FEATURES + ["target_change"]).copy()

    if frame.empty:
        raise RuntimeError("No complete feature/target rows could be built.")
    return frame


def train_models(frame):
    """Evaluate chronologically, then fit a final model for each stock."""
    models = {}
    for symbol in SYMBOLS:
        rows = frame.loc[frame["symbol"] == symbol].sort_values("ts_utc")
        split_at = int(len(rows) * (1 - HOLDOUT_FRACTION))
        train_end = split_at - HORIZON_BARS
        training_rows = rows.iloc[:train_end]
        validation_rows = rows.iloc[split_at:]

        if len(training_rows) < MIN_TRAINING_ROWS or validation_rows.empty:
            raise RuntimeError(
                f"{symbol} has too few labeled rows for chronological "
                f"training and validation ({len(rows)} rows)."
            )

        validation_model = LinearRegression()
        validation_model.fit(
            training_rows[FEATURES], training_rows["target_change"]
        )
        validation_predictions = validation_model.predict(
            validation_rows[FEATURES]
        )
        validation_mae = mean_absolute_error(
            validation_rows["target_change"], validation_predictions
        )

        model = LinearRegression()
        model.fit(rows[FEATURES], rows["target_change"])
        models[symbol] = model

        terms = " ".join(
            f"{coefficient:+.8g} * {name}"
            for name, coefficient in zip(FEATURES, model.coef_)
        )
        print(
            f"{symbol}: holdout MAE=${validation_mae:.4f}; "
            f"final model uses {len(rows)} labeled rows"
        )
        print(
            f"  predicted_change = {model.intercept_:+.8g} {terms}"
        )

    return models


def get_credentials():
    """Load Alpaca credentials from the project .env or environment."""
    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise SystemExit(
            "Missing python-dotenv. Install project dependencies with "
            "'python -m pip install -r requirements.txt'."
        ) from exc

    load_dotenv(ROOT / ".env")
    key = os.getenv("ALPACA_API_KEY") or os.getenv("APCA_API_KEY_ID")
    secret = os.getenv("ALPACA_SECRET_KEY") or os.getenv("APCA_API_SECRET_KEY")
    if not key or not secret:
        raise RuntimeError(
            "Set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env or the "
            "environment (APCA_API_KEY_ID/APCA_API_SECRET_KEY also work)."
        )
    return key, secret


def make_live_features(bars):
    """Build the same feature columns from completed five-minute Alpaca bars."""
    if not bars:
        return None

    frame = pd.DataFrame(
        {
            "timestamp": [bar.timestamp for bar in bars],
            "close": [float(bar.close) for bar in bars],
            "high": [float(bar.high) for bar in bars],
            "low": [float(bar.low) for bar in bars],
            "volume": [float(bar.volume) for bar in bars],
        }
    )
    frame["timestamp"] = pd.to_datetime(
        frame["timestamp"], utc=True, errors="coerce"
    )
    frame = frame.dropna(subset=["timestamp"])
    now = pd.Timestamp.now(tz="UTC")
    completed = frame["timestamp"] + pd.Timedelta(minutes=BAR_MINUTES) <= now
    frame = frame.loc[completed].sort_values("timestamp").copy()
    if len(frame) < 4:
        return None

    frame["recent_return"] = frame["close"].pct_change(
        periods=3, fill_method=None
    )
    frame["price_range"] = frame["high"] - frame["low"]
    frame = frame.replace([float("inf"), float("-inf")], float("nan"))
    feature_rows = frame.dropna(subset=FEATURES)
    if feature_rows.empty:
        return None
    return feature_rows[FEATURES].tail(1)


def fetch_latest_bars(data_client, symbol):
    """Fetch recent five-minute bars from the same IEX feed used by the draft."""
    try:
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
    except ImportError as exc:
        raise SystemExit(
            "Missing alpaca-py. Install project dependencies with "
            "'python -m pip install -r requirements.txt'."
        ) from exc

    now = datetime.now(timezone.utc)
    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame(BAR_MINUTES, TimeFrameUnit.Minute),
        start=now - timedelta(days=5),
        end=now,
        limit=10000,
        feed="iex",
    )
    return data_client.get_stock_bars(request).data.get(symbol, [])


def get_decision(prediction, buy_threshold, sell_threshold):
    if prediction > buy_threshold:
        return "BUY"
    if prediction < sell_threshold:
        return "SELL"
    return "HOLD"


def submit_paper_orders(trading_client, decisions, order_notional):
    """Submit conservative paper orders; never connects to a live account."""
    from alpaca.trading.enums import OrderSide, TimeInForce
    from alpaca.trading.requests import MarketOrderRequest

    clock = trading_client.get_clock()
    if not clock.is_open:
        print(f"Market is closed; no orders submitted. Next open: {clock.next_open}")
        return

    positions = {
        position.symbol: position
        for position in trading_client.get_all_positions()
    }
    for symbol, decision in decisions.items():
        position = positions.get(symbol)
        if decision["signal"] == "BUY":
            if position is not None:
                print(f"{symbol}: paper BUY skipped; a position already exists.")
                continue
            request = MarketOrderRequest(
                symbol=symbol,
                notional=order_notional,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY,
            )
            trading_client.submit_order(order_data=request)
            print(f"{symbol}: PAPER BUY submitted (notional=${order_notional:.2f}).")
        elif decision["signal"] == "SELL":
            if position is None:
                print(f"{symbol}: paper SELL skipped; no position to close.")
                continue
            quantity = float(position.qty)
            if quantity <= 0:
                print(f"{symbol}: paper SELL skipped; position is not long.")
                continue
            request = MarketOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY,
            )
            trading_client.submit_order(order_data=request)
            print(f"{symbol}: PAPER SELL submitted (qty={quantity:g}).")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Submit orders to the Alpaca PAPER account. Default: decisions only.",
    )
    parser.add_argument(
        "--buy-threshold",
        type=float,
        default=0.25,
        help="Minimum predicted six-bar increase, in dollars, to signal a buy.",
    )
    parser.add_argument(
        "--sell-threshold",
        type=float,
        default=-0.25,
        help="Predicted six-bar decrease, in dollars, to signal a sell.",
    )
    parser.add_argument(
        "--order-notional",
        type=float,
        default=10.0,
        help="Dollar value per paper buy order (default: $10).",
    )
    args = parser.parse_args()
    if args.buy_threshold <= 0:
        parser.error("--buy-threshold must be greater than zero.")
    if args.sell_threshold >= 0:
        parser.error("--sell-threshold must be less than zero.")
    if args.order_notional <= 0:
        parser.error("--order-notional must be greater than zero.")
    return args


def main():
    args = parse_args()
    training_data = load_training_data()
    models = train_models(training_data)
    print(
        "Training targets are changes over six subsequent stored observations; "
        "gaps in historical bars mean that is not always exactly 30 minutes."
    )

    key, secret = get_credentials()
    try:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.trading.client import TradingClient
    except ImportError as exc:
        raise SystemExit(
            "Missing alpaca-py. Install project dependencies with "
            "'python -m pip install -r requirements.txt'."
        ) from exc

    data_client = StockHistoricalDataClient(key, secret)
    trading_client = TradingClient(key, secret, paper=True) if args.execute else None
    decisions = {}

    for symbol in SYMBOLS:
        bars = fetch_latest_bars(data_client, symbol)
        live_features = make_live_features(bars)
        if live_features is None:
            print(f"{symbol}: skipped; not enough completed bars for features.")
            continue

        prediction = float(models[symbol].predict(live_features)[0])
        live_price = float(live_features["close"].iloc[0])
        signal = get_decision(
            prediction, args.buy_threshold, args.sell_threshold
        )
        decisions[symbol] = {
            "prediction": prediction,
            "live_price": live_price,
            "signal": signal,
        }
        print(
            f"{symbol}: latest close=${live_price:.2f}, "
            f"predicted six-bar change=${prediction:+.4f} -> {signal}"
        )

    if args.execute:
        submit_paper_orders(trading_client, decisions, args.order_notional)
    else:
        print("Decision-only mode; pass --execute to submit PAPER orders.")


if __name__ == "__main__":
    main()