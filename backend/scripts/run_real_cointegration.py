"""
Script to compute real Engle-Granger cointegration metrics, hedge ratios,
and Ornstein-Uhlenbeck half-lives on actual Nifty 50 historical market prices.
Updates the `pairs` table in SQLite.
"""

import os
import sys
import math
import logging
import sqlite3
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller
import statsmodels.api as sm

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("real_cointegration")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "statarb_n50.db")


def sanitize_float(val, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (ValueError, TypeError):
        return default


def compute_half_life(residuals: pd.Series) -> float:
    """Calculate Ornstein-Uhlenbeck half-life of mean reversion."""
    try:
        lag = residuals.shift(1).dropna()
        delta = residuals.diff().dropna()
        if len(lag) < 20 or len(delta) < 20:
            return 30.0
        df_ou = pd.DataFrame({"delta": delta, "lag": lag}).dropna()
        res = sm.OLS(df_ou["delta"], sm.add_constant(df_ou["lag"])).fit()
        theta = -res.params.iloc[1]
        if theta <= 0:
            return 99.0
        hl = np.log(2.0) / theta
        if hl <= 0 or math.isnan(hl) or math.isinf(hl):
            return 99.0
        return min(max(hl, 0.5), 180.0)
    except Exception:
        return 30.0


def run_cointegration_pipeline():
    logger.info(f"Connecting to database at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Load historical price matrix
    logger.info("Loading historical closing prices...")
    df_prices = pd.read_sql("SELECT symbol, timestamp, close FROM prices ORDER BY timestamp", conn)
    if df_prices.empty:
        logger.error("No prices found in database. Run ingest_real_market_data.py first.")
        conn.close()
        return False

    price_matrix = df_prices.pivot(index="timestamp", columns="symbol", values="close").dropna(how="all")
    # Forward fill small holidays/gaps then drop columns with too many NaNs
    price_matrix = price_matrix.ffill().bfill()
    symbols_with_data = set(price_matrix.columns)
    logger.info(f"Price matrix loaded: {price_matrix.shape[0]} dates x {len(symbols_with_data)} symbols")

    # 2. Fetch all pairs from database
    cursor.execute("SELECT id, symbol_a, symbol_b, sector FROM pairs")
    pairs = cursor.fetchall()
    logger.info(f"Analyzing {len(pairs)} pairs using real historical market data...")

    updates = []
    cointegrated_pairs = []

    for pair_id, sym_a, sym_b, sector in pairs:
        if sym_a not in symbols_with_data or sym_b not in symbols_with_data:
            continue

        series_a = price_matrix[sym_a].dropna()
        series_b = price_matrix[sym_b].dropna()

        # Align series
        aligned_a, aligned_b = series_a.align(series_b, join="inner")
        if len(aligned_a) < 60:
            continue

        # 1. Pearson Correlation
        corr = float(aligned_a.corr(aligned_b))
        if math.isnan(corr) or math.isinf(corr):
            corr = 0.0

        # 2. Engle-Granger OLS Regression for Hedge Ratio
        try:
            X = sm.add_constant(aligned_b)
            model = sm.OLS(aligned_a, X).fit()
            hedge_ratio = float(model.params.iloc[1])
            residuals = model.resid

            # 3. Augmented Dickey-Fuller Test on Residuals
            adf_result = adfuller(residuals, maxlag=1)
            adf_stat = float(adf_result[0])
            coint_p = float(adf_result[1])

            # 4. Ornstein-Uhlenbeck Half-Life
            half_life = compute_half_life(residuals)

        except Exception as e:
            hedge_ratio = 1.0
            adf_stat = 0.0
            coint_p = 1.0
            half_life = 30.0

        # Sanitize values
        corr = sanitize_float(corr)
        hedge_ratio = sanitize_float(hedge_ratio, 1.0)
        coint_p = sanitize_float(coint_p, 1.0)
        half_life = sanitize_float(half_life, 30.0)
        adf_stat = sanitize_float(adf_stat)

        # Determine active status based on cointegration quality
        is_active = 1 if (coint_p <= 0.05 and corr >= 0.50 and half_life <= 60.0) else 0

        updates.append((
            round(corr, 4),
            round(coint_p, 4),
            round(hedge_ratio, 4),
            round(half_life, 2),
            round(coint_p, 4),
            round(adf_stat, 4),
            is_active,
            pair_id
        ))

        if is_active == 1:
            cointegrated_pairs.append((
                f"{sym_a} / {sym_b}",
                sector or "N/A",
                corr,
                coint_p,
                hedge_ratio,
                half_life
            ))

    logger.info(f"Updating {len(updates)} pairs in SQLite database...")
    update_sql = """
    UPDATE pairs
    SET correlation = ?,
        coint_p_value = ?,
        hedge_ratio = ?,
        half_life = ?,
        adf_p_value = ?,
        adf_statistic = ?,
        is_active = ?,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """
    cursor.executemany(update_sql, updates)
    conn.commit()

    # Sort cointegrated pairs by p-value
    cointegrated_pairs.sort(key=lambda x: (x[3], -x[2]))

    logger.info("=" * 75)
    logger.info(f"REAL COINTEGRATION ANALYSIS COMPLETE")
    logger.info(f"Total Pairs Evaluated: {len(updates)}")
    logger.info(f"Active Cointegrated Pairs Found (p <= 0.05, Corr >= 0.50, HL <= 60D): {len(cointegrated_pairs)}")
    logger.info("-" * 75)
    logger.info(f"{'Pair':<26} | {'Sector':<14} | {'Corr':<6} | {'P-Val':<6} | {'Hedge':<7} | {'HalfLife'}")
    logger.info("-" * 75)
    for p in cointegrated_pairs[:20]:
        logger.info(f"{p[0]:<26} | {p[1]:<14} | {p[2]:.3f}  | {p[3]:.4f} | {p[4]:.3f}   | {p[5]:.1f}D")
    logger.info("=" * 75)

    conn.close()
    return True


if __name__ == "__main__":
    run_cointegration_pipeline()
