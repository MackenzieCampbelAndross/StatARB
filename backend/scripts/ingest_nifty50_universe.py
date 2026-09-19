"""
Ingest actual historical Nifty 50 market prices from Yahoo Finance into SQLite database.
Aligns instruments to exactly the 50 official Nifty 50 constituents.
"""

import os
import sys
import logging
import sqlite3
from datetime import datetime
import pandas as pd
import yfinance as yf

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ingest_nifty50_universe")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "statarb_n50.db")

# Exact official 50 NIFTY 50 constituents
NIFTY_50_CONSTITUENTS = [
    {"id": "ADANIENT", "name": "Adani Enterprises Ltd.", "sector": "Metals & Mining", "yf_symbol": "ADANIENT.NS"},
    {"id": "ADANIPORTS", "name": "Adani Ports and Special Economic Zone Ltd.", "sector": "Infrastructure", "yf_symbol": "ADANIPORTS.NS"},
    {"id": "APOLLOHOSP", "name": "Apollo Hospitals Enterprise Ltd.", "sector": "Healthcare", "yf_symbol": "APOLLOHOSP.NS"},
    {"id": "ASIANPAINT", "name": "Asian Paints Ltd.", "sector": "Consumer Goods", "yf_symbol": "ASIANPAINT.NS"},
    {"id": "AXISBANK", "name": "Axis Bank Ltd.", "sector": "Financial Services", "yf_symbol": "AXISBANK.NS"},
    {"id": "BAJAJ-AUTO", "name": "Bajaj Auto Ltd.", "sector": "Automobile", "yf_symbol": "BAJAJ-AUTO.NS"},
    {"id": "BAJAJFINSV", "name": "Bajaj Finserv Ltd.", "sector": "Financial Services", "yf_symbol": "BAJAJFINSV.NS"},
    {"id": "BAJFINANCE", "name": "Bajaj Finance Ltd.", "sector": "Financial Services", "yf_symbol": "BAJFINANCE.NS"},
    {"id": "BEL", "name": "Bharat Electronics Ltd.", "sector": "Capital Goods", "yf_symbol": "BEL.NS"},
    {"id": "BHARTIARTL", "name": "Bharti Airtel Ltd.", "sector": "Telecommunication", "yf_symbol": "BHARTIARTL.NS"},
    {"id": "BPCL", "name": "Bharat Petroleum Corporation Ltd.", "sector": "Energy", "yf_symbol": "BPCL.NS"},
    {"id": "BRITANNIA", "name": "Britannia Industries Ltd.", "sector": "Consumer Goods", "yf_symbol": "BRITANNIA.NS"},
    {"id": "CIPLA", "name": "Cipla Ltd.", "sector": "Healthcare", "yf_symbol": "CIPLA.NS"},
    {"id": "COALINDIA", "name": "Coal India Ltd.", "sector": "Metals & Mining", "yf_symbol": "COALINDIA.NS"},
    {"id": "DIVISLAB", "name": "Divi's Laboratories Ltd.", "sector": "Healthcare", "yf_symbol": "DIVISLAB.NS"},
    {"id": "DRREDDY", "name": "Dr. Reddy's Laboratories Ltd.", "sector": "Healthcare", "yf_symbol": "DRREDDY.NS"},
    {"id": "EICHERMOT", "name": "Eicher Motors Ltd.", "sector": "Automobile", "yf_symbol": "EICHERMOT.NS"},
    {"id": "GRASIM", "name": "Grasim Industries Ltd.", "sector": "Materials", "yf_symbol": "GRASIM.NS"},
    {"id": "HCLTECH", "name": "HCL Technologies Ltd.", "sector": "Information Technology", "yf_symbol": "HCLTECH.NS"},
    {"id": "HDFCBANK", "name": "HDFC Bank Ltd.", "sector": "Financial Services", "yf_symbol": "HDFCBANK.NS"},
    {"id": "HDFCLIFE", "name": "HDFC Life Insurance Company Ltd.", "sector": "Financial Services", "yf_symbol": "HDFCLIFE.NS"},
    {"id": "HEROMOTOCO", "name": "Hero MotoCorp Ltd.", "sector": "Automobile", "yf_symbol": "HEROMOTOCO.NS"},
    {"id": "HINDALCO", "name": "Hindalco Industries Ltd.", "sector": "Metals & Mining", "yf_symbol": "HINDALCO.NS"},
    {"id": "HINDUNILVR", "name": "Hindustan Unilever Ltd.", "sector": "Consumer Goods", "yf_symbol": "HINDUNILVR.NS"},
    {"id": "ICICIBANK", "name": "ICICI Bank Ltd.", "sector": "Financial Services", "yf_symbol": "ICICIBANK.NS"},
    {"id": "INDUSINDBK", "name": "IndusInd Bank Ltd.", "sector": "Financial Services", "yf_symbol": "INDUSINDBK.NS"},
    {"id": "INFY", "name": "Infosys Ltd.", "sector": "Information Technology", "yf_symbol": "INFY.NS"},
    {"id": "ITC", "name": "ITC Ltd.", "sector": "Consumer Goods", "yf_symbol": "ITC.NS"},
    {"id": "JSWSTEEL", "name": "JSW Steel Ltd.", "sector": "Metals & Mining", "yf_symbol": "JSWSTEEL.NS"},
    {"id": "KOTAKBANK", "name": "Kotak Mahindra Bank Ltd.", "sector": "Financial Services", "yf_symbol": "KOTAKBANK.NS"},
    {"id": "LT", "name": "Larsen & Toubro Ltd.", "sector": "Capital Goods", "yf_symbol": "LT.NS"},
    {"id": "M&M", "name": "Mahindra & Mahindra Ltd.", "sector": "Automobile", "yf_symbol": "M&M.NS"},
    {"id": "MARUTI", "name": "Maruti Suzuki India Ltd.", "sector": "Automobile", "yf_symbol": "MARUTI.NS"},
    {"id": "NESTLEIND", "name": "Nestle India Ltd.", "sector": "Consumer Goods", "yf_symbol": "NESTLEIND.NS"},
    {"id": "NTPC", "name": "NTPC Ltd.", "sector": "Energy", "yf_symbol": "NTPC.NS"},
    {"id": "ONGC", "name": "Oil & Natural Gas Corporation Ltd.", "sector": "Energy", "yf_symbol": "ONGC.NS"},
    {"id": "POWERGRID", "name": "Power Grid Corporation of India Ltd.", "sector": "Energy", "yf_symbol": "POWERGRID.NS"},
    {"id": "RELIANCE", "name": "Reliance Industries Ltd.", "sector": "Energy", "yf_symbol": "RELIANCE.NS"},
    {"id": "SBILIFE", "name": "SBI Life Insurance Company Ltd.", "sector": "Financial Services", "yf_symbol": "SBILIFE.NS"},
    {"id": "SBIN", "name": "State Bank of India", "sector": "Financial Services", "yf_symbol": "SBIN.NS"},
    {"id": "SHRIRAMFIN", "name": "Shriram Finance Ltd.", "sector": "Financial Services", "yf_symbol": "SHRIRAMFIN.NS"},
    {"id": "SUNPHARMA", "name": "Sun Pharmaceutical Industries Ltd.", "sector": "Healthcare", "yf_symbol": "SUNPHARMA.NS"},
    {"id": "TATACONSUM", "name": "Tata Consumer Products Ltd.", "sector": "Consumer Goods", "yf_symbol": "TATACONSUM.NS"},
    {"id": "TATASTEEL", "name": "Tata Steel Ltd.", "sector": "Metals & Mining", "yf_symbol": "TATASTEEL.NS"},
    {"id": "TCS", "name": "Tata Consultancy Services Ltd.", "sector": "Information Technology", "yf_symbol": "TCS.NS"},
    {"id": "TECHM", "name": "Tech Mahindra Ltd.", "sector": "Information Technology", "yf_symbol": "TECHM.NS"},
    {"id": "TITAN", "name": "Titan Company Ltd.", "sector": "Consumer Goods", "yf_symbol": "TITAN.NS"},
    {"id": "TRENT", "name": "Trent Ltd.", "sector": "Consumer Goods", "yf_symbol": "TRENT.NS"},
    {"id": "ULTRACEMCO", "name": "UltraTech Cement Ltd.", "sector": "Materials", "yf_symbol": "ULTRACEMCO.NS"},
    {"id": "WIPRO", "name": "Wipro Ltd.", "sector": "Information Technology", "yf_symbol": "WIPRO.NS"}
]


def ingest():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        valid_ids = [c["id"] for c in NIFTY_50_CONSTITUENTS]
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. Update instruments table: purge legacy non-Nifty-50 stocks
        placeholders = ",".join(["?"] * len(valid_ids))
        cursor.execute(f"DELETE FROM instruments WHERE id NOT IN ({placeholders})", valid_ids)
        cursor.execute(f"DELETE FROM prices WHERE symbol NOT IN ({placeholders})", valid_ids)
        cursor.execute(f"DELETE FROM pairs WHERE symbol_a NOT IN ({placeholders}) OR symbol_b NOT IN ({placeholders})", valid_ids * 2)
        conn.commit()

        # Insert or update the 50 official instruments
        for c in NIFTY_50_CONSTITUENTS:
            cursor.execute("""
                INSERT INTO instruments (id, name, sector, exchange, instrument_type, is_active, created_at, updated_at)
                VALUES (?, ?, ?, 'NSE', 'EQUITY', 1, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    sector = excluded.sector,
                    is_active = 1,
                    updated_at = excluded.updated_at
            """, (c["id"], c["name"], c["sector"], now_str, now_str))
        conn.commit()
        logger.info(f"Updated instruments table: exactly {len(valid_ids)} official Nifty 50 constituents.")

        # 2. Download historical market data
        ticker_map = {c["yf_symbol"]: c["id"] for c in NIFTY_50_CONSTITUENTS}
        yf_tickers = list(ticker_map.keys())

        logger.info(f"Downloading historical daily data from 2023-01-01 to 2026-09-19 for {len(yf_tickers)} symbols...")
        data = yf.download(
            tickers=yf_tickers,
            start="2023-01-01",
            end="2026-09-19",
            interval="1d",
            group_by="ticker",
            progress=True,
            auto_adjust=False
        )

        if data.empty:
            logger.error("No market data returned from Yahoo Finance.")
            return False

        # Clear existing prices for full fresh sync
        cursor.execute("DELETE FROM prices")
        conn.commit()

        rows_to_insert = []
        successful_symbols = []

        for yf_tick, symbol in ticker_map.items():
            try:
                if yf_tick in data.columns.get_level_values(0):
                    sub_df = data[yf_tick].dropna(subset=["Close"])
                else:
                    logger.warning(f"Fetching {yf_tick} individually...")
                    sub_df = yf.download(yf_tick, start="2023-01-01", end="2026-09-19", interval="1d", progress=False)

                if sub_df.empty:
                    logger.warning(f"No price data for {symbol} ({yf_tick})")
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

                    rows_to_insert.append((symbol, ts, o, h, l, c, v, adj_c, now_str))

                successful_symbols.append((symbol, len(sub_df), float(sub_df["Close"].iloc[-1])))

            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")

        logger.info(f"Inserting {len(rows_to_insert):,} historical price bars into database...")
        cursor.executemany("""
            INSERT INTO prices (symbol, timestamp, open, high, low, close, volume, adjusted_close, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows_to_insert)
        conn.commit()

        logger.info("=" * 60)
        logger.info(f"NIFTY 50 UNIVERSE INGESTION COMPLETE")
        logger.info(f"Total Constituents: {len(successful_symbols)} / 50")
        logger.info(f"Total Historical Rows Inserted: {len(rows_to_insert):,}")
        logger.info("=" * 60)

    finally:
        conn.close()


if __name__ == "__main__":
    ingest()
