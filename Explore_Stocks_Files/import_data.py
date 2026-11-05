#Got help from Romo
import sqlite3

from pathlib import Path

DB_URI = "file:////192.168.1.95/CS-CLASSROOM/intraday_5m.sqlite?mode=ro&immutable=1"
MY_DB = "Stock_Linear_Regression_Database.db"

STOCK_SYMBOLS = ["MSFT", "TSLA", "GOOGL"]
START_DATE = "2025-01-01"
END_DATE = ""

nas_conn = sqlite3.connect(DB_URI, uri=True)
local_conn = sqlite3.connect(MY_DB)

local_conn.execute("""
    CREATE TABLE IF NOT EXISTS stock_bars? (
        symbol TEXT,
        ts_utc TEXT,
        open REAL,
        high REAL.
        low REAL,
        close REAL,
        volume REAL,
        PRIMARY KEY (symbol, ts_utc)
    )
""")

for symbol in STOCK_SYMBOLS:
    sql = """
        SELECT symbol, ts_utc, open, high
    """