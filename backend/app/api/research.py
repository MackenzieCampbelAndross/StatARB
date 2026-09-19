import math
import uuid
import logging
from datetime import datetime
from typing import List

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.research import ResearchExperiment
from app.models.pair import Pair as PairModel
from app.models.price import Price
from app.quant.backtesting.engine import BacktestEngine, BacktestConfig as QuantBacktestConfig
from app.quant.spread.calculator import SpreadCalculator
from app.schemas.backtests import BacktestConfig, ExperimentResult

logger = logging.getLogger(__name__)

router = APIRouter()
spread_calculator = SpreadCalculator()


def sanitize_float(val, default=0.0):
    if val is None:
        return default
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (ValueError, TypeError):
        return default


@router.post("/experiments", response_model=ExperimentResult)
async def run_experiment(config: BacktestConfig, db: Session = Depends(get_db)) -> ExperimentResult:
    """
    Run a research experiment with the given configuration using actual historical data.
    """
    try:
        experiment_id = str(uuid.uuid4())

        try:
            start_dt = pd.to_datetime(config.start).to_pydatetime()
        except Exception:
            start_dt = datetime(2023, 1, 1)

        try:
            end_dt = pd.to_datetime(config.end).to_pydatetime()
        except Exception:
            end_dt = datetime.now()

        quant_config = QuantBacktestConfig(
            start_date=start_dt,
            end_date=end_dt,
            initial_capital=1000000.0,
            entry_z_score=config.entry,
            exit_z_score=config.exit,
            stop_z_score=config.stop,
            max_holding_period=config.holding,
            transaction_cost=config.cost,
            slippage=config.slippage,
            position_sizing=config.position,
            correlation_threshold=0.50,
            coint_p_value=0.05
        )

        pair = None
        if config.pair_id:
            pair = db.query(PairModel).filter(PairModel.id == config.pair_id).first()
        if not pair:
            pair = db.query(PairModel).filter(
                PairModel.is_active == 1,
                PairModel.coint_p_value <= 0.05
            ).order_by(PairModel.coint_p_value.asc(), PairModel.correlation.desc()).first()

        if not pair:
            raise HTTPException(status_code=400, detail="No cointegrated pair available for experiment")

        prices_a = db.query(Price).filter(Price.symbol == pair.symbol_a).order_by(Price.timestamp.asc()).all()
        prices_b = db.query(Price).filter(Price.symbol == pair.symbol_b).order_by(Price.timestamp.asc()).all()

        if not prices_a or not prices_b:
            raise HTTPException(status_code=400, detail="Insufficient price data for experiment")

        df_a = pd.DataFrame([{'timestamp': p.timestamp, 'close_a': p.close} for p in prices_a]).set_index('timestamp')
        df_b = pd.DataFrame([{'timestamp': p.timestamp, 'close_b': p.close} for p in prices_b]).set_index('timestamp')
        df = df_a.join(df_b, how='inner').sort_index()

        if len(df) < 30:
            raise HTTPException(status_code=400, detail="Insufficient overlapping price bars for experiment")

        df = df.reset_index()
        hedge_ratio = sanitize_float(pair.hedge_ratio, 1.0)
        spread = spread_calculator.calculate_spread(df['close_a'], df['close_b'], hedge_ratio)
        rolling_stats = spread_calculator.calculate_rolling_statistics(spread, window=20)
        z_score = spread_calculator.calculate_z_score(
            spread,
            rolling_stats['rolling_mean'],
            rolling_stats['rolling_std'],
            window=20
        )

        df_a_in = pd.DataFrame({'timestamp': df['timestamp'], 'close': df['close_a']})
        df_b_in = pd.DataFrame({'timestamp': df['timestamp'], 'close': df['close_b']})

        engine = BacktestEngine(quant_config)
        results = engine.run_backtest(df_a_in, df_b_in, spread, z_score, hedge_ratio)

        total_return = round(sanitize_float(results['total_return']), 2)
        sharpe_val = round(sanitize_float(results['sharpe_ratio']), 2)
        drawdown_val = round(sanitize_float(results['max_drawdown']), 2)
        cagr_val = round(sanitize_float(results['cagr']), 2)
        win_rate_val = round(sanitize_float(results['win_rate']), 1)
        num_trades = int(results['num_trades'])

        experiment_name = f"Z-Score {config.entry}/{config.exit} ({pair.symbol_a}/{pair.symbol_b})"

        experiment = ResearchExperiment(
            id=experiment_id,
            name=experiment_name,
            description=f"Entry Z={config.entry}, Exit Z={config.exit}, Stop Z={config.stop}, Max Holding={config.holding}D",
            entry_z_score=config.entry,
            exit_z_score=config.exit,
            stop_z_score=config.stop,
            holding_period=config.holding,
            transaction_cost=config.cost,
            slippage=config.slippage,
            position_sizing=config.position,
            correlation_threshold=0.50,
            coint_p_value=0.05,
            total_return=total_return,
            sharpe_ratio=sharpe_val,
            max_drawdown=drawdown_val,
            cagr=cagr_val,
            win_rate=win_rate_val,
            num_trades=num_trades,
            start_date=quant_config.start_date,
            end_date=quant_config.end_date,
            status="completed"
        )

        db.add(experiment)
        db.commit()

        return ExperimentResult(
            name=experiment_name,
            date=datetime.now().strftime("%d %b %Y"),
            entry=config.entry,
            exit=config.exit,
            return_val=total_return,
            sharpe=sharpe_val,
            drawdown=drawdown_val
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running experiment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/experiments", response_model=List[ExperimentResult])
async def get_experiments(db: Session = Depends(get_db)) -> List[ExperimentResult]:
    """
    Get all research experiments ordered by creation date.
    """
    experiments = db.query(ResearchExperiment).order_by(
        ResearchExperiment.created_at.desc()
    ).limit(20).all()

    results = []
    for exp in experiments:
        result = ExperimentResult(
            name=exp.name,
            date=exp.created_at.strftime("%d %b %Y"),
            entry=exp.entry_z_score,
            exit=exp.exit_z_score,
            return_val=round(sanitize_float(exp.total_return), 2),
            sharpe=round(sanitize_float(exp.sharpe_ratio), 2),
            drawdown=round(sanitize_float(exp.max_drawdown), 2)
        )
        results.append(result)

    return results

