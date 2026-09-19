from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.orm import Session
from app.schemas.backtests import BacktestConfig, BacktestResult, Trade
from app.database.session import get_db
from app.models.pair import Pair as PairModel
from app.models.price import Price
from app.models.backtest import Backtest as BacktestModel, BacktestTrade as BacktestTradeModel
from app.quant.backtesting.engine import BacktestEngine, BacktestConfig as QuantBacktestConfig
from app.quant.spread.calculator import SpreadCalculator
from datetime import datetime
import pandas as pd
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize quantitative engines
spread_calculator = SpreadCalculator()


@router.post("", response_model=BacktestResult)
async def run_backtest(config: BacktestConfig, db: Session = Depends(get_db)) -> BacktestResult:
    """
    Run a backtest with the given configuration.
    Matches frontend runBacktest() function.
    """
    try:
        # Generate unique backtest ID
        backtest_id = str(uuid.uuid4())

        # Convert to quantitative config
        quant_config = QuantBacktestConfig(
            start_date=datetime.strptime(config.start, "%Y-%m-%d"),
            end_date=datetime.strptime(config.end, "%Y-%m-%d"),
            initial_capital=1000000.0,  # Default capital
            entry_z_score=config.entry,
            exit_z_score=config.exit,
            stop_z_score=config.stop,
            max_holding_period=config.holding,
            transaction_cost=config.cost,
            slippage=config.slippage,
            position_sizing=config.position,
            correlation_threshold=0.70,  # Default
            coint_p_value=0.05  # Default
        )

        # Get cointegrated pairs for backtesting
        pairs = db.query(PairModel).filter(
            PairModel.is_active == 1,
            PairModel.coint_p_value <= 0.05
        ).limit(10).all()  # Limit to top 10 pairs for demo

        if not pairs:
            raise HTTPException(status_code=400, detail="No cointegrated pairs available for backtesting")

        # Run backtest on first pair (simplified - in production, run on all)
        pair = pairs[0]

        # Get price data
        prices_a = db.query(Price).filter(
            Price.symbol == pair.symbol_a,
            Price.timestamp >= quant_config.start_date,
            Price.timestamp <= quant_config.end_date
        ).order_by(Price.timestamp).all()

        prices_b = db.query(Price).filter(
            Price.symbol == pair.symbol_b,
            Price.timestamp >= quant_config.start_date,
            Price.timestamp <= quant_config.end_date
        ).order_by(Price.timestamp).all()

        if not prices_a or not prices_b:
            raise HTTPException(status_code=400, detail="Insufficient price data for backtesting")

        # Create DataFrames
        df_a = pd.DataFrame([{
            'timestamp': p.timestamp,
            'close': p.close
        } for p in prices_a])

        df_b = pd.DataFrame([{
            'timestamp': p.timestamp,
            'close': p.close
        } for p in prices_b])

        # Calculate spread and Z-score
        hedge_ratio = pair.hedge_ratio or 1.0
        series_a = df_a['close']
        series_b = df_b['close']

        spread = spread_calculator.calculate_spread(series_a, series_b, hedge_ratio)
        rolling_stats = spread_calculator.calculate_rolling_statistics(spread, window=20)
        z_score = spread_calculator.calculate_z_score(
            spread,
            rolling_stats['rolling_mean'],
            rolling_stats['rolling_std'],
            window=20
        )

        # Run backtest
        engine = BacktestEngine(quant_config)
        results = engine.run_backtest(df_a, df_b, spread, z_score, hedge_ratio)

        # Store backtest in database
        backtest = BacktestModel(
            id=backtest_id,
            start_date=quant_config.start_date,
            end_date=quant_config.end_date,
            initial_capital=quant_config.initial_capital,
            final_capital=results['final_capital'],
            total_return=results['total_return'],
            cagr=results['cagr'],
            sharpe_ratio=results['sharpe_ratio'],
            sortino_ratio=results['sortino_ratio'],
            max_drawdown=results['max_drawdown'],
            volatility=0.0,  # Would calculate from returns
            win_rate=results['win_rate'],
            profit_factor=results['profit_factor'],
            num_trades=results['num_trades'],
            avg_trade_return=results['avg_trade_return'],
            avg_holding_period=0.0,  # Would calculate from trades
            turnover=0.0,
            gross_pnl=0.0,
            net_pnl=results['final_capital'] - quant_config.initial_capital,
            entry_z_score=quant_config.entry_z_score,
            exit_z_score=quant_config.exit_z_score,
            stop_z_score=quant_config.stop_z_score,
            holding_period=quant_config.max_holding_period,
            transaction_cost=quant_config.transaction_cost,
            slippage=quant_config.slippage,
            position_sizing=quant_config.position_sizing,
            correlation_threshold=quant_config.correlation_threshold,
            coint_p_value=quant_config.coint_p_value,
            status="completed"
        )

        db.add(backtest)

        # Store trades
        for i, trade in enumerate(results['trades']):
            backtest_trade = BacktestTradeModel(
                backtest_id=backtest_id,
                pair_id=pair.id,
                entry_date=trade.entry_date,
                exit_date=trade.exit_date,
                direction=trade.direction.value,
                entry_z_score=trade.entry_z_score,
                exit_z_score=trade.exit_z_score,
                holding_period=trade.holding_period,
                entry_price_a=trade.entry_price_a,
                entry_price_b=trade.entry_price_b,
                exit_price_a=trade.exit_price_a,
                exit_price_b=trade.exit_price_b,
                hedge_ratio=trade.hedge_ratio,
                position_size=trade.position_size,
                pnl=trade.pnl,
                return_pct=trade.return_pct,
                transaction_cost=trade.transaction_cost,
                slippage=trade.slippage,
                is_train=0
            )
            db.add(backtest_trade)

        db.commit()

        # Return results in frontend format
        return BacktestResult(
            initial=int(results['initial_capital']),
            final=int(results['final_capital']),
            total=round(results['total_return'], 2),
            cagr=round(results['cagr'], 2),
            sharpe=round(results['sharpe_ratio'], 2),
            sortino=round(results['sortino_ratio'], 2),
            drawdown=round(results['max_drawdown'], 2),
            winRate=round(results['win_rate'], 1),
            profitFactor=round(results['profit_factor'], 2),
            count=results['num_trades']
        )

    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{backtest_id}/trades", response_model=List[Trade])
async def get_backtest_trades(backtest_id: str, db: Session = Depends(get_db)) -> List[Trade]:
    """
    Get trades for a specific backtest.
    """
    backtest_trades = db.query(BacktestTradeModel).filter(
        BacktestTradeModel.backtest_id == backtest_id
    ).all()

    trades = []
    for bt in backtest_trades:
        # Get pair information
        pair = db.query(PairModel).filter(PairModel.id == bt.pair_id).first()
        pair_name = f"{pair.symbol_a} / {pair.symbol_b}" if pair else "Unknown"

        trade = Trade(
            id=bt.id,
            pair=pair_name,
            entryDate=bt.entry_date.strftime("%d %b %Y"),
            exitDate=bt.exit_date.strftime("%d %b %Y"),
            direction=bt.direction,
            entryZ=round(bt.entry_z_score, 2),
            exitZ=round(bt.exit_z_score, 2),
            holding=bt.holding_period,
            pnl=round(bt.pnl, 2),
            return_val=round(bt.return_pct, 2)
        )
        trades.append(trade)

    return trades


@router.get("/demo/trades", response_model=List[Trade])
async def get_demo_trades() -> List[Trade]:
    """
    Get demo trades for development.
    """
    # Return empty list for now - real trades will come from backtest runs
    return []
