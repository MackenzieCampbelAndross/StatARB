from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.orm import Session
from app.schemas.pairs import Signal
from app.database.session import get_db
from app.models.pair import Pair as PairModel
from app.models.price import Price
from app.quant.signals.engine import SignalEngine
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


@router.get("", response_model=List[Signal])
async def get_signals(
    filter: str = "ALL",
    db: Session = Depends(get_db)
) -> List[Signal]:
    """
    Get all current signals with optional filtering.
    Matches frontend getSignals() function.
    """
    # Get active pairs from database
    query_obj = db.query(PairModel).filter(PairModel.is_active == 1)

    pairs = query_obj.all()

    # Calculate signals for each pair
    signals = []
    current_time = datetime.now().strftime("%H:%M:%S IST")

    for pair in pairs:
        try:
            # Get current prices
            latest_price_a = db.query(Price).filter(
                Price.symbol == pair.symbol_a
            ).order_by(Price.timestamp.desc()).first()

            latest_price_b = db.query(Price).filter(
                Price.symbol == pair.symbol_b
            ).order_by(Price.timestamp.desc()).first()

            if not latest_price_a or not latest_price_b:
                continue

            # Calculate current Z-score and spread
            current_z, current_signal = await _calculate_current_metrics(pair, db)

            # Calculate spread
            hedge_ratio = sanitize_float(pair.hedge_ratio, 1.0)
            spread = latest_price_a.close - hedge_ratio * latest_price_b.close
            spread = sanitize_float(spread)

            signal_data = Signal(
                id=pair.id,
                pair=f"{pair.symbol_a} / {pair.symbol_b}",
                a=pair.symbol_a,
                b=pair.symbol_b,
                sector=pair.sector or "N/A",
                correlation=round(sanitize_float(pair.correlation), 3),
                cointP=round(sanitize_float(pair.coint_p_value), 4),
                hedgeRatio=round(hedge_ratio, 3),
                halfLife=round(sanitize_float(pair.half_life), 1),
                adfP=round(sanitize_float(pair.adf_p_value), 4),
                z=round(sanitize_float(current_z), 2),
                signal=current_signal,
                priceA=round(sanitize_float(latest_price_a.close), 2),
                priceB=round(sanitize_float(latest_price_b.close), 2),
                spread=round(spread, 2),
                updated=current_time
            )

            # Apply filter
            if filter == "ALL" or current_signal == filter:
                signals.append(signal_data)

        except Exception as e:
            logger.error(f"Error calculating signal for pair {pair.id}: {e}")
            continue

    return signals


async def _calculate_current_metrics(pair: PairModel, db: Session) -> tuple:
    """
    Calculate current Z-score and signal for a pair.
    """
    try:
        # Get recent prices
        prices_a = db.query(Price).filter(
            Price.symbol == pair.symbol_a
        ).order_by(Price.timestamp.desc()).limit(60).all()

        prices_b = db.query(Price).filter(
            Price.symbol == pair.symbol_b
        ).order_by(Price.timestamp.desc()).limit(60).all()

        if not prices_a or not prices_b or len(prices_a) < 20 or len(prices_b) < 20:
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
        logger.error(f"Error calculating current metrics for pair {pair.id}: {e}")
        return 0.0, "WATCH"
