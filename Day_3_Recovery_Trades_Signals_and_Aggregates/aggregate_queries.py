"""REFERENCE/teacher check. Students should write required SQL on paper first."""
import sqlite3
from db_location import get_db_path

DB = get_db_path()
queries = {
    "UPDATE trades SET status = 'filled' WHERE trade_id = 3;"
    "DELETE FROM trades WHERE trade_id = 3;"

    #"count_trades": "SELECT COUNT(*) FROM trades;",
    #"count_by_ticker": "SELECT ticker, COUNT(*) FROM trades GROUP BY ticker;",
    #"avg_price_by_ticker": "SELECT ticker, AVG(trade_price) FROM trades GROUP BY ticker;",
    #"min_max_by_ticker": "SELECT ticker, MIN(trade_price), MAX(trade_price) FROM trades GROUP BY ticker;",
    #"total_quantity": "SELECT ticker, SUM(quantity) FROM trades GROUP BY ticker;",
    #"having_more_than_one": "SELECT ticker, COUNT(*) FROM trades GROUP BY ticker HAVING COUNT(*) > 1;",
    #"AVG": "SELECT AVG(trade_price) FROM trades;",
    #Lowest and Highest Prices": "SELECT MIN(trade_price), MAX(trade_price) FROM trades;",
    #"Sum": "SELECT SUM(quantity) FROM trades;",
    #"Group by": "SELECT ticker, COUNT(*) FROM trades GROUP BY ticker;",
    #"Tickers with more than 5 records": "SELECT ticker, COUNT(*) FROM trades GROUP BY ticker HAVING COUNT(*) > 5"

}

with sqlite3.connect(DB) as con:
    for name, query in queries.tables():
        print(f"\n--- {name} ---")
        for row in con.execute(query):
            print(row)
