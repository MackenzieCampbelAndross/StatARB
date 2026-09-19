"""
Create sample data for testing with real market structure.
This creates minimal test data with real Nifty 50 symbols.
"""

import sqlite3
import sys
from datetime import datetime, timedelta
import random
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "statarb_n50.db")

# Sample Nifty 50 stocks for testing
SAMPLE_STOCKS = [
    {"id": "RELIANCE", "name": "Reliance Industries Ltd.", "sector": "Energy"},
    {"id": "HDFCBANK", "name": "HDFC Bank Ltd.", "sector": "Financial Services"},
    {"id": "ICICIBANK", "name": "ICICI Bank Ltd.", "sector": "Financial Services"},
    {"id": "INFY", "name": "Infosys Ltd.", "sector": "Information Technology"},
    {"id": "TCS", "name": "Tata Consultancy Services Ltd.", "sector": "Information Technology"},
    {"id": "ITC", "name": "ITC Ltd.", "sector": "Consumer Goods"},
    {"id": "SBIN", "name": "State Bank of India", "sector": "Financial Services"},
    {"id": "BHARTIARTL", "name": "Bharti Airtel Ltd.", "sector": "Telecommunication"},
    {"id": "KOTAKBANK", "name": "Kotak Mahindra Bank Ltd.", "sector": "Financial Services"},
    {"id": "LT", "name": "Larsen & Toubro Ltd.", "sector": "Capital Goods"},
]

def create_sample_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create tables if they don't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS instruments (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                sector TEXT,
                exchange TEXT,
                instrument_type TEXT,
                is_active INTEGER,
                listed_date DATETIME,
                delisted_date DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL,
                adjusted_close REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pairs (
                id TEXT PRIMARY KEY,
                symbol_a TEXT NOT NULL,
                symbol_b TEXT NOT NULL,
                sector TEXT,
                correlation REAL,
                correlation_lookback INTEGER,
                correlation_period DATETIME,
                coint_p_value REAL,
                hedge_ratio REAL,
                half_life REAL,
                adf_p_value REAL,
                adf_statistic REAL,
                is_active INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME
            )
        """)
        
        # Insert sample instruments
        for stock in SAMPLE_STOCKS:
            cursor.execute("""
                INSERT OR REPLACE INTO instruments (id, name, sector, exchange, instrument_type, is_active, created_at, updated_at)
                VALUES (?, ?, ?, 'NSE', 'EQUITY', 1, ?, ?)
            """, (stock["id"], stock["name"], stock["sector"], now_str, now_str))
        
        # Generate sample price data for the last 90 days
        base_date = datetime.now() - timedelta(days=90)
        
        for stock in SAMPLE_STOCKS:
            base_price = random.uniform(1000, 3000)
            for i in range(90):
                date = base_date + timedelta(days=i)
                # Skip weekends
                if date.weekday() >= 5:
                    continue
                    
                # Generate realistic price movement
                change_percent = random.uniform(-0.02, 0.02)
                open_price = base_price * (1 + change_percent)
                close_price = open_price * (1 + random.uniform(-0.01, 0.01))
                high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.01))
                low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.01))
                volume = random.uniform(1000000, 10000000)
                
                cursor.execute("""
                    INSERT INTO prices (symbol, timestamp, open, high, low, close, volume, adjusted_close, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (stock["id"], date.strftime("%Y-%m-%d %H:%M:%S"), 
                      round(open_price, 2), round(high_price, 2), round(low_price, 2), 
                      round(close_price, 2), round(volume, 2), round(close_price, 2), now_str))
                
                base_price = close_price
        
        # Create some sample pairs
        sample_pairs = [
            ("RELIANCE-ICICIBANK", "RELIANCE", "ICICIBANK", "Energy", 0.85, 0.03, 1.2, 8.5, 0.02, -3.5),
            ("HDFCBANK-ICICIBANK", "HDFCBANK", "ICICIBANK", "Financial Services", 0.92, 0.01, 0.95, 5.2, 0.015, -2.8),
            ("INFY-TCS", "INFY", "TCS", "Information Technology", 0.88, 0.02, 1.05, 12.3, 0.025, 1.5),
            ("SBIN-KOTAKBANK", "SBIN", "KOTAKBANK", "Financial Services", 0.90, 0.018, 0.85, 7.8, 0.022, -1.2),
            ("LT-BHARTIARTL", "LT", "BHARTIARTL", "Capital Goods", 0.78, 0.04, 1.3, 15.6, 0.035, 0.8),
        ]
        
        for pair_data in sample_pairs:
            pair_id, symbol_a, symbol_b, sector, correlation, coint_p, hedge_ratio, half_life, adf_p, adf_stat = pair_data
            cursor.execute("""
                INSERT OR REPLACE INTO pairs (id, symbol_a, symbol_b, sector, correlation, coint_p_value, hedge_ratio, half_life, adf_p_value, adf_statistic, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """, (pair_id, symbol_a, symbol_b, sector, correlation, coint_p, hedge_ratio, half_life, adf_p, adf_stat, now_str, now_str))
        
        conn.commit()
        
        print("Sample data created successfully!")
        print(f"- {len(SAMPLE_STOCKS)} instruments")
        print(f"- {90 * len(SAMPLE_STOCKS) * 5 // 7} price records (approximately)")
        print(f"- {len(sample_pairs)} pairs")
        
    except Exception as e:
        print(f"Error creating sample data: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    create_sample_data()