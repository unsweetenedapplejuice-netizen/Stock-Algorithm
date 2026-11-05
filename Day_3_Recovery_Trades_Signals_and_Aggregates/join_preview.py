"""JOIN preview. Students should annotate the clauses before running it."""
import sqlite3
from db_location import get_db_path

DB = get_db_path()
query = """
SELECT prices.ticker,
       prices.trade_date,
       prices.close, 
       trades.side,
       trades.quantity,
       trades.trade_price
FROM prices
JOIN trades
  ON prices.ticker = trades.ticker
 AND prices.trade_date = trades.trade_date
ORDER BY prices.trade_date;
"""
# SELECT picks the values from both prices and trades to be displayed, and then the JOIN is used to display values from the prices table that correspond to prices.ticker 
# and prices.trade_date. This sets up the table so that it displays both the 
# Honestly I kind of don't understand this
# For some reason the prices table is missing - it brought up an error when I ran the code
with sqlite3.connect(DB) as con:
    rows = con.execute(query).fetchall()
print(f"JOIN returned {len(rows)} rows")
for row in rows:
    print(row)
