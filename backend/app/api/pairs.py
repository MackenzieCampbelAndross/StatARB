from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from sqlalchemy.orm import Session
from app.schemas.pairs import Pair, PairFilter, Signal
from app.database.session import get_db
from app.models.pair import Pair as PairModel
from app.models.price import Price
from app.quant.signals.engine import SignalEngine, SignalType
from app.quant.spread.calculator import SpreadCalculator
from datetime import datetime, timedelta
import math
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize quantitative engines
signal_engine = SignalEngine()
spread_calculator = SpreadCalculator()


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


@router.get("", response_model=List[Pair])
async def get_pairs(
    minCorrelation: Optional[float] = 0.70,
    maxP: Optional[float] = 0.05,
    maxHalfLife: Optional[float] = 30,
    signal: Optional[str] = "ALL",
    query: Optional[str] = None,
    db: Session = Depends(get_db)
) -> List[Pair]:
    """
    Get all pairs with optional filtering.
    Matches frontend getPairs() function.
    """
    # Query pairs from database
    query_obj = db.query(PairModel)

    # Apply filters
    if minCorrelation is not None:
        query_obj = query_obj.filter(PairModel.correlation >= minCorrelation)
    if maxP is not None:
        query_obj = query_obj.filter(PairModel.coint_p_value <= maxP)
    if maxHalfLife is not None:
        query_obj = query_obj.filter(PairModel.half_life <= maxHalfLife)
    if signal and signal != "ALL":
        # Need to calculate current signal - for now, filter by active status
        if signal in ["LONG SPREAD", "SHORT SPREAD"]:
            query_obj = query_obj.filter(PairModel.is_active == 1)
        elif signal == "EXIT":
            query_obj = query_obj.filter(PairModel.is_active == 0)
    if query:
        query_obj = query_obj.filter(
            (PairModel.symbol_a.ilike(f"%{query}%")) |
            (PairModel.symbol_b.ilike(f"%{query}%"))
        )

    pairs = query_obj.all()

    # Convert to response format
    result = []
    for pair in pairs:
        # Calculate current Z-score and signal
        current_z, current_signal = await _calculate_current_signal(pair, db)

        result.append(Pair(
            id=pair.id,
            pair=f"{pair.symbol_a} / {pair.symbol_b}",
            a=pair.symbol_a,
            b=pair.symbol_b,
            sector=pair.sector or "N/A",
            correlation=round(sanitize_float(pair.correlation), 3),
            cointP=round(sanitize_float(pair.coint_p_value), 4),
            hedgeRatio=round(sanitize_float(pair.hedge_ratio, 1.0), 3),
            halfLife=round(sanitize_float(pair.half_life), 1),
            adfP=round(sanitize_float(pair.adf_p_value), 4),
            z=round(sanitize_float(current_z), 2),
            signal=current_signal
        ))

    return result


@router.get("/{pair_id}", response_model=Pair)
async def get_pair(pair_id: str, db: Session = Depends(get_db)) -> Pair:
    """
    Get a specific pair by ID.
    Matches frontend getPair() function.
    """
    pair = db.query(PairModel).filter(PairModel.id == pair_id).first()

    if not pair:
        raise HTTPException(status_code=404, detail="Pair not found")

    # Calculate current Z-score and signal
    current_z, current_signal = await _calculate_current_signal(pair, db)

    return Pair(
        id=pair.id,
        pair=f"{pair.symbol_a} / {pair.symbol_b}",
        a=pair.symbol_a,
        b=pair.symbol_b,
        sector=pair.sector or "N/A",
        correlation=round(sanitize_float(pair.correlation), 3),
        cointP=round(sanitize_float(pair.coint_p_value), 4),
        hedgeRatio=round(sanitize_float(pair.hedge_ratio, 1.0), 3),
        halfLife=round(sanitize_float(pair.half_life), 1),
        adfP=round(sanitize_float(pair.adf_p_value), 4),
        z=round(sanitize_float(current_z), 2),
        signal=current_signal
    )


async def _calculate_current_signal(pair: PairModel, db: Session) -> tuple:
    """
    Calculate current Z-score and signal for a pair.
    This is a simplified version - in production, use real-time data.
    """
    try:
        # Get recent prices for both symbols
        prices_a = db.query(Price).filter(
            Price.symbol == pair.symbol_a
        ).order_by(Price.timestamp.desc()).limit(60).all()

        prices_b = db.query(Price).filter(
            Price.symbol == pair.symbol_b
        ).order_by(Price.timestamp.desc()).limit(60).all()

        if not prices_a or not prices_b or len(prices_a) < 20 or len(prices_b) < 20:
            # Not enough data - return default values
            return 0.0, "WATCH"

        prices_a = list(reversed(prices_a))
        prices_b = list(reversed(prices_b))

        # Create price series
        import pandas as pd
        series_a = pd.Series([p.close for p in prices_a])
        series_b = pd.Series([p.close for p in prices_b])

        # Calculate spread and Z-score
        hedge_ratio = sanitize_float(pair.hedge_ratio, 1.0)
        spread = spread_calculator.calculate_spread(series_a, series_b, hedge_ratio)
        rolling_stats = spread_calculator.calculate_rolling_statistics(spread, window=20)
        z_score = spread_calculator.calculate_z_score(
            spread,
            rolling_stats['rolling_mean'],
            rolling_stats['rolling_std'],
            window=20
        )

        current_z = 0.0
        if len(z_score) > 0:
            val = z_score.iloc[-1]
            if not pd.isna(val):
                current_z = float(val)
        current_z = sanitize_float(current_z)

        # Generate signal
        signal_info = signal_engine.generate_signal(current_z)
        current_signal = signal_info['signal']

        return current_z, current_signal

    except Exception as e:
        logger.error(f"Error calculating current signal for pair {pair.id}: {e}")
        return 0.0, "WATCH"


@router.get("/{pair_id}/series")
async def get_pair_series(
    pair_id: str,
    range: str = "1M",
    mode: str = "spread",
    db: Session = Depends(get_db)
):
    """
    Get historical spread and price series for a specific pair over a time range.
    Matches frontend LineChartPanel series requirements.
    """
    pair = db.query(PairModel).filter(PairModel.id == pair_id).first()
    if not pair:
        raise HTTPException(status_code=404, detail="Pair not found")

    days_map = {
        "1D": 5,
        "1W": 10,
        "1M": 30,
        "3M": 90,
        "6M": 180,
        "1Y": 365,
    }
    limit_bars = days_map.get(range, 30)

    # Fetch price history (with extra bars for 20-day rolling calculation)
    prices_a = db.query(Price).filter(
        Price.symbol == pair.symbol_a
    ).order_by(Price.timestamp.desc()).limit(limit_bars + 30).all()

    prices_b = db.query(Price).filter(
        Price.symbol == pair.symbol_b
    ).order_by(Price.timestamp.desc()).limit(limit_bars + 30).all()

    if not prices_a or not prices_b:
        return []

    import pandas as pd
    df_a = pd.DataFrame([{"timestamp": p.timestamp, "close_a": p.close} for p in prices_a]).set_index("timestamp")
    df_b = pd.DataFrame([{"timestamp": p.timestamp, "close_b": p.close} for p in prices_b]).set_index("timestamp")
    df = df_a.join(df_b, how="inner").sort_index()

    if df.empty:
        return []

    hedge_ratio = sanitize_float(pair.hedge_ratio, 1.0)
    df["spread"] = df["close_a"] - hedge_ratio * df["close_b"]
    df["rolling_mean"] = df["spread"].rolling(window=20).mean()
    df["rolling_std"] = df["spread"].rolling(window=20).std()
    df["z_score"] = (df["spread"] - df["rolling_mean"]) / df["rolling_std"].replace(0, 1.0)

    # Slice to requested range
    df_slice = df.tail(limit_bars)

    result = []
    for ts, row in df_slice.iterrows():
        date_str = pd.to_datetime(ts).strftime("%d %b")
        spread_val = round(sanitize_float(row["spread"]), 2)
        price_a = round(sanitize_float(row["close_a"]), 2)
        price_b = round(sanitize_float(row["close_b"]), 2)
        mean_val = round(sanitize_float(row["rolling_mean"]), 2)
        z_val = round(sanitize_float(row["z_score"]), 2)

        result.append({
            "label": date_str,
            "spread": spread_val,
            "mean": mean_val,
            "z": z_val,
            "a": price_a,
            "b": price_b
        })

    return result
