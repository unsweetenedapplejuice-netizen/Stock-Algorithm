#Got help from Romo and copied some of his code
import sqlite3
import pandas as pd
from pathlib import Path

DB_URI = "file:////192.168.1.95/CS-CLASSROOM/intraday_5m.sqlite?mode=ro&immutable=1"
MY_DB = "Stock_Linear_Regression_Database.db"

STOCK_SYMBOLS = ["MSFT", "TSLA", "GOOGL"]
START_DATE = "2025-01-01"
END_DATE = "2025-02-01"

print("Copying stock data into local database...")

nas_conn = sqlite3.connect(DB_URI, uri=True)
cursor = nas_conn.cursor()
local_conn = sqlite3.connect(MY_DB)

local_conn.execute("""
    CREATE TABLE IF NOT EXISTS stock_bars (
        symbol TEXT,
        ts_utc TEXT,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume REAL,
        PRIMARY KEY (symbol, ts_utc)
    )
""")

for symbol in STOCK_SYMBOLS:
    sql = """
        SELECT symbol, ts_utc, open, high, low, close, volume
        FROM bars_5m
        WHERE symbol = ?
            AND ts_utc >= ?
            AND ts_utc < ?
        ORDER BY ts_utc
    """

    rows = nas_conn.execute(
        sql, (symbol, START_DATE, END_DATE)
    ).fetchall()

    local_conn.executemany(
        "INSERT OR IGNORE INTO stock_bars VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows
    )

    print(symbol, "rows found:", len(rows))

local_conn.commit()
nas_conn.close()

df = pd.read_sql_query(
    "SELECT * FROM stock_bars ORDER BY symbol, ts_utc",
    local_conn
)

local_conn.close()

if df.empty:
    print("No data was copied.")
    raise SystemExit

df["recent_return"] = df.groupby("symbol")["close"].pct_change(3)
df["price_range"] = df["high"] - df["low"]

df["future_close"] = df.groupby("symbol")["close"].shift(-6)
df["future_ts"] = df.groupby("symbol")["ts_utc"].shift(-6)

df["target_change"] = df["future_close"] - df["close"]

df = df.dropna().copy()

features = ["close", "recent_return", "price_range", "volume"]

X = df[features]
y = df["target_change"]
print("done")