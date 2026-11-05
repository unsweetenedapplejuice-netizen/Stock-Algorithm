import sqlite3

from pathlib import Path

DB_PATH = Path(r"\\192.168.1.95\CS-CLASSROOM\intraday_5m.sqlite")
DB_URI = "file:////192.168.1.95/CS-CLASSROOM/intraday_5m.sqlite?mode=ro&immutable=1"

def text_value(value):
    return value.value if hasattr(value, "value") else str(value)

def show_rows(title, columns, rows):
    print(f"\n=== {title} ===")
    print(" | ".join(columns))
    for row in rows:
        print(" | ".join(str(value) for value in row))

def query(conn, title, sql, params=()):
    cursor = conn.execute(sql, params)
    columns = [item[0] for item in cursor.description]
    rows = cursor.fetchall()
    show_rows(title, columns, rows)
    return rows

def import_Database_Stuff():

    DB = DB_PATH
    imported = updated = skipped = 0
    with sqlite3.connect(DB) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                alpaca_order_id TEXT UNIQUE,
                ticker TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                trade_price REAL NOT NULL,
                status TEXT
            )
        """)

        for order in orders:
            filled_at = getattr(order, "filled_at", None)
            filled_qty = getattr(order, "filled_qty", None)
            if filled_at is None or filled_qty in (None, "0", 0):
                skipped += 1
                continue

            order_id = str(order.id)
            ticker = str(order.symbol).upper()
            trade_date = filled_at.date().isoformat() if hasattr(filled_at, "date") else str(filled_at)[:10]
            side = text_value(order.side).upper()
            quantity = float(filled_qty)
            trade_price = float(getattr(order, "filled_avg_price", 0) or 0)
            status = text_value(order.status)

            existing = con.execute(
                "SELECT trade_id FROM trades WHERE alpaca_order_id = ?", (order_id,)
            ).fetchone()
            if existing:
                con.execute("""
                    UPDATE trades
                    SET ticker=?, trade_date=?, side=?, quantity=?, trade_price=?, status=?
                    WHERE alpaca_order_id=?
                """, (ticker, trade_date, side, quantity, trade_price, status, order_id))
                updated += 1
            else:
                con.execute("""
                    INSERT INTO trades
                    (alpaca_order_id, ticker, trade_date, side, quantity, trade_price, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (order_id, ticker, trade_date, side, quantity, trade_price, status))
                imported += 1

    print(f"Database: {DB}")
    print(f"Filled Alpaca orders imported: {imported}; updated: {updated}; non-filled closed orders skipped: {skipped}")
    if imported + updated == 0:
        print("No filled order history was available. Use fallback_trades.py ONLY so you can continue SQL practice today.")

