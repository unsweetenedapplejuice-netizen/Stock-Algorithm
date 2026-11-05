import sqlite3
DB = "trading.db"
con = sqlite3.connect(DB)
query = """
SELECT stocks.ticker,
       relational_prices.trade_date,
       relational_prices.close
FROM stocks
JOIN relational_prices
ON stocks.stock_id = relational_prices.stock_id
ORDER BY relational_prices.trade_date;
"""
for row in con.execute(query):
    print(row)
con.close()
