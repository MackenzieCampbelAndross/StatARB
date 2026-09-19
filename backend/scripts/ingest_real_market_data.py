"""
Script to ingest actual historical Nifty 50 market prices from Yahoo Finance into SQLite database.
Replaces synthetic demo prices with real daily OHLCV market data.
"""

import os
import sys
import logging
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ingest_market_data")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "statarb_n50.db")

# Symbol mapping for Yahoo Finance NSE tickers
SYMBOL_MAPPING = {
    "MAHINDRA": "M&M.NS",
}


def to_yf_ticker(symbol: str) -> str:
    if symbol in SYMBOL_MAPPING:
        return SYMBOL_MAPPING[symbol]
    if symbol.endswith(".NS") or symbol.endswith(".BO"):
        return symbol
    return f"{symbol}.NS"


def from_yf_ticker(ticker: str) -> str:
    # Reverse lookup
    for sym, yf_tick in SYMBOL_MAPPING.items():
        if yf_tick == ticker:
            return sym
    return ticker.replace(".NS", "").replace(".BO", "")


def ingest_real_market_data(start_date: str = "2023-01-01", end_date: str = None):
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"Connecting to database at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Fetch active instruments
    cursor.execute("SELECT id, name, sector FROM instruments WHERE is_active = 1")
    instruments = cursor.fetchall()
    logger.info(f"Found {len(instruments)} active instruments in database")

    ticker_map = {to_yf_ticker(inst[0]): inst[0] for inst in instruments}
    yf_tickers = list(ticker_map.keys())

    logger.info(f"Downloading historical market data for {len(yf_tickers)} tickers from {start_date} to {end_date}...")
    
    # Download in bulk for speed
    data = yf.download(
        yf_tickers,
        start=start_date,
        end=end_date,
        interval="1d",
        group_by="ticker",
        progress=True,
        auto_adjust=False
    )

    if data.empty:
        logger.error("No data returned from Yahoo Finance")
        return False

    # 2. Clear out old synthetic demo prices
    logger.info("Clearing old synthetic demo prices from 'prices' table...")
    cursor.execute("DELETE FROM prices")
    conn.commit()

    rows_to_insert = []
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    successful_symbols = []

    for yf_tick, symbol in ticker_map.items():
        try:
            if yf_tick not in data.columns.get_level_values(0):
                logger.warning(f"Ticker {yf_tick} not found in downloaded data")
                continue

            sub_df = data[yf_tick].dropna(subset=["Close"])
            if sub_df.empty:
                logger.warning(f"Ticker {yf_tick} has no valid close price data")
                continue

            sub_df = sub_df.reset_index()

            for _, row in sub_df.iterrows():
                ts = pd.to_datetime(row["Date"]).strftime("%Y-%m-%d %H:%M:%S")
                o = round(float(row["Open"]), 2) if not pd.isna(row["Open"]) else round(float(row["Close"]), 2)
                h = round(float(row["High"]), 2) if not pd.isna(row["High"]) else round(float(row["Close"]), 2)
                l = round(float(row["Low"]), 2) if not pd.isna(row["Low"]) else round(float(row["Close"]), 2)
                c = round(float(row["Close"]), 2)
                v = float(row["Volume"]) if not pd.isna(row["Volume"]) else 0.0
                adj_c = round(float(row.get("Adj Close", c)), 2) if not pd.isna(row.get("Adj Close")) else c

                rows_to_insert.append((
                    symbol,
                    ts,
                    o,
                    h,
                    l,
                    c,
                    v,
                    adj_c,
                    now_str
                ))

            successful_symbols.append((symbol, len(sub_df), float(sub_df["Close"].iloc[-1])))

        except Exception as e:
            logger.error(f"Error processing ticker {yf_tick} ({symbol}): {e}")

    # 3. Batch insert into SQLite
    logger.info(f"Inserting {len(rows_to_insert):,} historical price bars into database...")
    insert_sql = """
    INSERT INTO prices (symbol, timestamp, open, high, low, close, volume, adjusted_close, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    cursor.executemany(insert_sql, rows_to_insert)
    conn.commit()

    logger.info("=" * 60)
    logger.info(f"REAL MARKET DATA INGESTION COMPLETE")
    logger.info(f"Total Symbols Ingested: {len(successful_symbols)} / {len(instruments)}")
    logger.info(f"Total Historical Rows Inserted: {len(rows_to_insert):,}")
    logger.info("-" * 60)
    logger.info("Sample Latest Market Closing Prices:")
    for sym, count, latest_c in successful_symbols[:10]:
        logger.info(f"  {sym:12} | Bars: {count:4} | Latest Close: ₹{latest_c:,.2f}")
    logger.info("=" * 60)

    conn.close()
    return True


if __name__ == "__main__":
    ingest_real_market_data()
