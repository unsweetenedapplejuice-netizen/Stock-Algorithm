"""Creates a simplified relational version with stocks + relational_prices.
Use this as a learning copy, not necessarily your final production database.
"""
import sqlite3
DB = "trading.db"
con = sqlite3.connect(DB)
con.execute("CREATE TABLE IF NOT EXISTS stocks (stock_id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT UNIQUE NOT NULL, company_name TEXT)")
con.execute("CREATE TABLE IF NOT EXISTS relational_prices (price_id INTEGER PRIMARY KEY AUTOINCREMENT, stock_id INTEGER NOT NULL, trade_date TEXT NOT NULL, close REAL NOT NULL, FOREIGN KEY(stock_id) REFERENCES stocks(stock_id))")
# insert tickers from prices
for (ticker,) in con.execute("SELECT DISTINCT ticker FROM prices"):
    con.execute("INSERT OR IGNORE INTO stocks (ticker) VALUES (?)", (ticker,))
# copy prices with stock_id
for ticker, trade_date, close in con.execute("SELECT ticker, trade_date, close FROM prices"):
    stock_id = con.execute("SELECT stock_id FROM stocks WHERE ticker = ?", (ticker,)).fetchone()[0]
    con.execute("INSERT INTO relational_prices (stock_id, trade_date, close) VALUES (?, ?, ?)", (stock_id, trade_date, close))
con.commit()
con.close()
print("relational copy created")
