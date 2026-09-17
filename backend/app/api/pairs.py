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
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize quantitative engines
signal_engine = SignalEngine()
spread_calculator = SpreadCalculator()


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
            sector=pair.sector,
            correlation=pair.correlation or 0.0,
            cointP=pair.coint_p_value or 0.0,
            hedgeRatio=pair.hedge_ratio or 0.0,
            halfLife=pair.half_life or 0.0,
            adfP=pair.adf_p_value or 0.0,
            z=current_z,
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
        sector=pair.sector,
        correlation=pair.correlation or 0.0,
        cointP=pair.coint_p_value or 0.0,
        hedgeRatio=pair.hedge_ratio or 0.0,
        halfLife=pair.half_life or 0.0,
        adfP=pair.adf_p_value or 0.0,
        z=current_z,
        signal=current_signal
    )


async def _calculate_current_signal(pair: PairModel, db: Session) -> tuple:
    """
    Calculate current Z-score and signal for a pair.
    This is a simplified version - in production, use real-time data.
    """
    try:
        # Get recent prices for both symbols
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
            # Not enough data - return default values
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
        logger.error(f"Error calculating current signal for pair {pair.id}: {e}")
        return 0.0, "WATCH"
