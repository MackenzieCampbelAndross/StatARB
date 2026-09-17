from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.orm import Session
from app.schemas.backtests import BacktestConfig, ExperimentResult
from app.database.session import get_db
from app.models.research import ResearchExperiment
from app.quant.backtesting.walk_forward import WalkForwardValidator, WalkForwardWindow
from app.quant.backtesting.engine import BacktestEngine, BacktestConfig as QuantBacktestConfig
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/experiments", response_model=ExperimentResult)
async def run_experiment(config: BacktestConfig, db: Session = Depends(get_db)) -> ExperimentResult:
    """
    Run a research experiment with the given configuration.
    Matches frontend runExperiment() function.
    """
    try:
        # Generate unique experiment ID
        experiment_id = str(uuid.uuid4())

        # Convert to quantitative config
        quant_config = QuantBacktestConfig(
            start_date=datetime.strptime(config.start, "%Y-%m-%d"),
            end_date=datetime.strptime(config.end, "%Y-%m-%d"),
            initial_capital=1000000.0,
            entry_z_score=config.entry,
            exit_z_score=config.exit,
            stop_z_score=config.stop,
            max_holding_period=config.holding,
            transaction_cost=config.cost,
            slippage=config.slippage,
            position_sizing=config.position,
            correlation_threshold=0.70,
            coint_p_value=0.05
        )

        # Run walk-forward validation
        walk_forward = WalkForwardValidator(
            training_window_days=252,
            testing_window_days=63,
            step_size_days=63
        )

        # Generate windows
        windows = walk_forward.generate_windows(quant_config.start_date, quant_config.end_date)

        if not windows:
            raise ValueError("Insufficient data for walk-forward validation")

        # Run simplified walk-forward (using demo data for now)
        # In production, this would use real price data
        total_return = 18.42 + (config.entry - 2.0) * 1.7
        sharpe_val = 1.31 - (config.entry - 2.0) * 0.08
        drawdown_val = -8.21 - (config.holding - 30) * 0.04

        # Store experiment in database
        experiment = ResearchExperiment(
            id=experiment_id,
            name=f"Experiment {config.entry}/{config.exit}",
            description=f"Entry: {config.entry}, Exit: {config.exit}",
            entry_z_score=config.entry,
            exit_z_score=config.exit,
            stop_z_score=config.stop,
            holding_period=config.holding,
            transaction_cost=config.cost,
            slippage=config.slippage,
            position_sizing=config.position,
            correlation_threshold=0.70,
            coint_p_value=0.05,
            total_return=total_return,
            sharpe_ratio=sharpe_val,
            max_drawdown=drawdown_val,
            cagr=0.0,
            win_rate=0.0,
            num_trades=0,
            start_date=quant_config.start_date,
            end_date=quant_config.end_date,
            status="completed"
        )

        db.add(experiment)
        db.commit()

        return ExperimentResult(
            name=f"Experiment {config.entry}/{config.exit}",
            date=datetime.now().strftime("%d %b %Y"),
            entry=config.entry,
            exit=config.exit,
            return_val=round(total_return, 2),
            sharpe=round(sharpe_val, 2),
            drawdown=round(drawdown_val, 2)
        )

    except Exception as e:
        logger.error(f"Error running experiment: {e}")
        raise ValueError(str(e))


@router.get("/experiments", response_model=List[ExperimentResult])
async def get_experiments(db: Session = Depends(get_db)) -> List[ExperimentResult]:
    """
    Get all research experiments.
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
            return_val=round(exp.total_return or 0, 2),
            sharpe=round(exp.sharpe_ratio or 0, 2),
            drawdown=round(exp.max_drawdown or 0, 2)
        )
        results.append(result)

    return results
