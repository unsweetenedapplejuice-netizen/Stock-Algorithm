DAY 3 - RECOVERY + REAL ALPACA TRADE HISTORY + AGGREGATES

This zip is self-contained. It does NOT refer to missing recovery files.
Put/extract these files into the SAME stock-project folder as trading.db and run from that folder.

PART A - RECOVERY
1) Run day3_recovery_check.py.
2) GREEN: keep your current prices; do not redo the import.
3) YELLOW/RED: run recovery_import_prices.py. This connects directly to Alpaca historical market data.

PART B - TRADE HISTORY
4) Run create_trades_table.py.
5) Run import_alpaca_trade_history.py to connect to the student's Alpaca PAPER account and import filled orders.
6) Only if there are no usable filled orders, run fallback_trades.py so the SQL lesson can continue.

PART C - SQL
7) Complete paper-first COUNT/AVG/MIN/MAX/SUM/GROUP BY/HAVING work. aggregate_queries.py is reference/check code, not a replacement for the paper attempt.
8) Annotate JOIN first, then run join_preview.py.
9) Run make_dml_practice_copy.py before UPDATE/DELETE practice.

Install once if needed: pip install alpaca-py

Support files alpaca_credentials.py and db_location.py should normally not be edited.
