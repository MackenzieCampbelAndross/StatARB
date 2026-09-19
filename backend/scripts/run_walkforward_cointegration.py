"""
Temporally correct / walk-forward cointegration screening across official 50 Nifty 50 constituents.
Estimates cointegration parameters strictly on the in-sample formation period (2023-01-02 to 2024-06-30)
to eliminate look-ahead bias, then stores parameters for out-of-sample trading and validation.
"""

import os
import sys
import logging
import sqlite3
from datetime import datetime
import itertools
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, coint
import statsmodels.api as sm

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("walkforward_coint")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "statarb_n50.db")

# In-sample formation window: Jan 2, 2023 to June 30, 2024 (~370 trading sessions)
IN_SAMPLE_START = "2023-01-01 00:00:00"
IN_SAMPLE_END = "2024-06-30 23:59:59"


def compute_half_life(spread: pd.Series) -> float:
    """Calculate Ornstein-Uhlenbeck half-life using AR(1) model."""
    spread_clean = spread.dropna()
    if len(spread_clean) < 30:
        return 999.0

    spread_lag = spread_clean.shift(1).dropna()
    spread_diff = spread_clean.diff().dropna()

    df_reg = pd.DataFrame({"diff": spread_diff, "lag": spread_lag}).dropna()
    if df_reg.empty or len(df_reg) < 20:
        return 999.0

    X = sm.add_constant(df_reg["lag"])
    y = df_reg["diff"]

    try:
        model = sm.OLS(y, X).fit()
        lambda_param = model.params.iloc[1]
        if lambda_param < 0:
            hl = -np.log(2) / lambda_param
            return float(hl) if not np.isnan(hl) and not np.isinf(hl) else 999.0
        return 999.0
    except Exception:
        return 999.0


def run_walkforward_screening():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. Load active instruments
        cursor.execute("SELECT id, name, sector FROM instruments WHERE is_active = 1")
        instruments = cursor.fetchall()
        sector_map = {inst[0]: inst[2] for inst in instruments}
        symbols = [inst[0] for inst in instruments]

        logger.info(f"Loaded {len(symbols)} official Nifty 50 instruments.")

        # 2. Load in-sample prices
        logger.info(f"Loading in-sample formation prices ({IN_SAMPLE_START[:10]} to {IN_SAMPLE_END[:10]})...")
        query = """
            SELECT symbol, timestamp, close 
            FROM prices 
            WHERE timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp ASC
        """
        price_df = pd.read_sql_query(query, conn, params=(IN_SAMPLE_START, IN_SAMPLE_END))

        if price_df.empty:
            logger.error("No in-sample price data found.")
            return

        # Pivot prices by symbol
        price_matrix = price_df.pivot(index="timestamp", columns="symbol", values="close").dropna()
        logger.info(f"Synchronized in-sample formation matrix shape: {price_matrix.shape} (Dates x Constituents)")

        candidate_pairs = list(itertools.combinations(symbols, 2))
        total_pairs = len(candidate_pairs)
        logger.info(f"Screening {total_pairs} candidate pairs for in-sample cointegration...")

        # Clear existing pairs table
        cursor.execute("DELETE FROM pairs")
        conn.commit()

        pairs_to_insert = []
        cointegrated_count = 0
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for sym_a, sym_b in candidate_pairs:
            if sym_a not in price_matrix.columns or sym_b not in price_matrix.columns:
                continue

            series_a = price_matrix[sym_a]
            series_b = price_matrix[sym_b]

            # 1. Pearson Correlation
            corr = float(series_a.corr(series_b))
            if np.isnan(corr):
                continue

            # 2. Engle-Granger Two-Step Cointegration
            # OLS: Series_A = alpha + beta * Series_B + epsilon
            X = sm.add_constant(series_b)
            y = series_a

            try:
                ols_model = sm.OLS(y, X).fit()
                beta = float(ols_model.params.iloc[1])
                residuals = ols_model.resid

                # Augmented Dickey-Fuller test on residuals
                adf_result = adfuller(residuals, maxlag=1, autolag=None)
                adf_stat = float(adf_result[0])
                coint_p = float(adf_result[1])

                # Ornstein-Uhlenbeck Half-life
                hl = compute_half_life(residuals)

                # Qualification criteria for statistically cointegrated pair:
                # p-value <= 0.05, correlation >= 0.40, half-life between 1 and 60 days
                is_coint = 1 if (coint_p <= 0.05 and corr >= 0.40 and 1.0 <= hl <= 60.0) else 0
                if is_coint:
                    cointegrated_count += 1

                pair_id = f"{sym_a.lower()}-{sym_b.lower()}"
                sector_a = sector_map.get(sym_a, "General")
                sector_b = sector_map.get(sym_b, "General")
                pair_sector = sector_a if sector_a == sector_b else f"{sector_a}/{sector_b}"

                pairs_to_insert.append((
                    pair_id,
                    sym_a,
                    sym_b,
                    pair_sector,
                    round(corr, 4),
                    len(price_matrix),
                    now_str,
                    round(coint_p, 6),
                    round(beta, 6),
                    round(hl, 2),
                    round(coint_p, 6),
                    round(adf_stat, 4),
                    is_coint,
                    now_str,
                    now_str
                ))

            except Exception:
                continue

        # Insert pairs into SQLite
        insert_sql = """
            INSERT INTO pairs (
                id, symbol_a, symbol_b, sector, correlation, correlation_lookback,
                correlation_period, coint_p_value, hedge_ratio, half_life,
                adf_p_value, adf_statistic, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor.executemany(insert_sql, pairs_to_insert)
        conn.commit()

        logger.info("=" * 60)
        logger.info("WALK-FORWARD IN-SAMPLE COINTEGRATION SCREENING COMPLETE")
        logger.info(f"Total Evaluated Pairs: {len(pairs_to_insert):,} / {total_pairs}")
        logger.info(f"Statistically Cointegrated Pairs Found (p <= 0.05, HL <= 60D): {cointegrated_count}")
        logger.info("-" * 60)

        # Print top 10 cointegrated pairs
        cursor.execute("""
            SELECT symbol_a, symbol_b, correlation, coint_p_value, hedge_ratio, half_life
            FROM pairs
            WHERE is_active = 1
            ORDER BY coint_p_value ASC, correlation DESC
            LIMIT 10
        """)
        top_pairs = cursor.fetchall()
        logger.info("Top 10 Cointegrated Pairs (In-Sample Estimated):")
        for a, b, c, p, hr, hld in top_pairs:
            logger.info(f"  {a:12} / {b:12} | Corr: {c:.2f} | p-val: {p:.4f} | Beta: {hr:.3f} | Half-Life: {hld:.1f}D")
        logger.info("=" * 60)

    finally:
        conn.close()


if __name__ == "__main__":
    run_walkforward_screening()
