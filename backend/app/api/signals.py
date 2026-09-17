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
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize quantitative engines
signal_engine = SignalEngine()
spread_calculator = SpreadCalculator()


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

    # Apply signal filter if specified
    if filter and filter != "ALL":
        # For now, we'll calculate signals and filter afterwards
        pass

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
            hedge_ratio = pair.hedge_ratio or 1.0
            spread = latest_price_a.close - hedge_ratio * latest_price_b.close

            signal_data = Signal(
                id=pair.id,
                pair=f"{pair.symbol_a} / {pair.symbol_b}",
                a=pair.symbol_a,
                b=pair.symbol_b,
                sector=pair.sector,
                correlation=pair.correlation or 0.0,
                cointP=pair.coint_p_value or 0.0,
                hedgeRatio=hedge_ratio,
                halfLife=pair.half_life or 0.0,
                adfP=pair.adf_p_value or 0.0,
                z=current_z,
                signal=current_signal,
                priceA=latest_price_a.close,
                priceB=latest_price_b.close,
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
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        prices_a = db.query(Price).filter(
            Price.symbol == pair.symbol_a,
            Price.timestamp >= start_date,
            Price.timestamp <= end_date
        ).order_by(Price.timestamp).all()

        prices_b = db.query(Price).filter(
            Price.symbol == pair.symbol_b,
            Price.timestamp >= start_date,
            Price.timestamp <= end_date
        ).order_by(Price.timestamp).all()

        if not prices_a or not prices_b or len(prices_a) < 20 or len(prices_b) < 20:
            return 0.0, "WATCH"

        # Create price series
        import pandas as pd
        series_a = pd.Series([p.close for p in prices_a])
        series_b = pd.Series([p.close for p in prices_b])

        # Calculate spread and Z-score
        hedge_ratio = pair.hedge_ratio or 1.0
        spread = spread_calculator.calculate_spread(series_a, series_b, hedge_ratio)
        rolling_stats = spread_calculator.calculate_rolling_statistics(spread, window=20)
        z_score = spread_calculator.calculate_z_score(
            spread,
            rolling_stats['rolling_mean'],
            rolling_stats['rolling_std'],
            window=20
        )

        current_z = z_score.iloc[-1] if len(z_score) > 0 else 0.0

        # Generate signal
        signal_info = signal_engine.generate_signal(current_z)
        current_signal = signal_info['signal']

        return current_z, current_signal

    except Exception as e:
        logger.error(f"Error calculating current metrics for pair {pair.id}: {e}")
        return 0.0, "WATCH"
