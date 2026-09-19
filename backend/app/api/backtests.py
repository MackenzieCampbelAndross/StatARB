import math
from datetime import datetime
from typing import List, Optional
import uuid
import logging
import pandas as pd
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.schemas.backtests import BacktestConfig, BacktestResult, Trade
from app.database.session import get_db
from app.models.pair import Pair as PairModel
from app.models.price import Price
from app.models.backtest import Backtest as BacktestModel, BacktestTrade as BacktestTradeModel
from app.quant.backtesting.engine import BacktestEngine, BacktestConfig as QuantBacktestConfig
from app.quant.spread.calculator import SpreadCalculator

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


@router.post("", response_model=BacktestResult)
async def run_backtest(config: BacktestConfig, db: Session = Depends(get_db)) -> BacktestResult:
    """
    Run a backtest with the given configuration on real historical data.
    """
    try:
        backtest_id = str(uuid.uuid4())

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
            raise HTTPException(status_code=400, detail="No cointegrated pairs available for backtesting")

        prices_a = db.query(Price).filter(
            Price.symbol == pair.symbol_a
        ).order_by(Price.timestamp.asc()).all()

        prices_b = db.query(Price).filter(
            Price.symbol == pair.symbol_b
        ).order_by(Price.timestamp.asc()).all()

        if not prices_a or not prices_b:
            raise HTTPException(status_code=400, detail=f"Insufficient price data for pair {pair.id}")

        df_a = pd.DataFrame([{'timestamp': p.timestamp, 'close_a': p.close} for p in prices_a]).set_index('timestamp')
        df_b = pd.DataFrame([{'timestamp': p.timestamp, 'close_b': p.close} for p in prices_b]).set_index('timestamp')
        df = df_a.join(df_b, how='inner').sort_index()

        if len(df) < 30:
            raise HTTPException(status_code=400, detail=f"Insufficient overlapping price bars for {pair.id} (found {len(df)})")

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

        # Store backtest in database
        backtest = BacktestModel(
            id=backtest_id,
            start_date=quant_config.start_date,
            end_date=quant_config.end_date,
            initial_capital=quant_config.initial_capital,
            final_capital=sanitize_float(results['final_capital'], quant_config.initial_capital),
            total_return=sanitize_float(results['total_return']),
            cagr=sanitize_float(results['cagr']),
            sharpe_ratio=sanitize_float(results['sharpe_ratio']),
            sortino_ratio=sanitize_float(results['sortino_ratio']),
            max_drawdown=sanitize_float(results['max_drawdown']),
            volatility=0.0,
            win_rate=sanitize_float(results['win_rate']),
            profit_factor=sanitize_float(results['profit_factor']),
            num_trades=int(results['num_trades']),
            avg_trade_return=sanitize_float(results['avg_trade_return']),
            avg_holding_period=0.0,
            turnover=0.0,
            gross_pnl=0.0,
            net_pnl=sanitize_float(results['final_capital'] - quant_config.initial_capital),
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
        for trade in results['trades']:
            backtest_trade = BacktestTradeModel(
                backtest_id=backtest_id,
                pair_id=pair.id,
                entry_date=trade.entry_date,
                exit_date=trade.exit_date,
                direction=trade.direction.value,
                entry_z_score=sanitize_float(trade.entry_z_score),
                exit_z_score=sanitize_float(trade.exit_z_score),
                holding_period=int(trade.holding_period or 0),
                entry_price_a=sanitize_float(trade.entry_price_a),
                entry_price_b=sanitize_float(trade.entry_price_b),
                exit_price_a=sanitize_float(trade.exit_price_a),
                exit_price_b=sanitize_float(trade.exit_price_b),
                hedge_ratio=sanitize_float(trade.hedge_ratio, 1.0),
                position_size=sanitize_float(trade.position_size),
                pnl=sanitize_float(trade.pnl),
                return_pct=sanitize_float(trade.return_pct),
                transaction_cost=sanitize_float(trade.transaction_cost),
                slippage=sanitize_float(trade.slippage),
                is_train=0
            )
            db.add(backtest_trade)

        db.commit()

        # Build downsampled equity curve points for visualization
        curve_points = []
        raw_curve = results.get('equity_curve', [])
        if raw_curve:
            step = max(1, len(raw_curve) // 36)
            indices = list(range(0, len(raw_curve), step))
            if indices[-1] != len(raw_curve) - 1:
                indices.append(len(raw_curve) - 1)

            for idx in indices:
                val = raw_curve[idx]
                label_date = f"Point {idx}"
                if idx < len(df):
                    label_date = pd.to_datetime(df.iloc[idx]['timestamp']).strftime("%m/%Y")
                curve_points.append({
                    "label": label_date,
                    "value": round(sanitize_float(val, 1000000.0), 2)
                })

        return BacktestResult(
            id=backtest_id,
            initial=int(sanitize_float(results['initial_capital'], 1000000.0)),
            final=int(sanitize_float(results['final_capital'], 1000000.0)),
            total=round(sanitize_float(results['total_return']), 2),
            cagr=round(sanitize_float(results['cagr']), 2),
            sharpe=round(sanitize_float(results['sharpe_ratio']), 2),
            sortino=round(sanitize_float(results['sortino_ratio']), 2),
            drawdown=round(sanitize_float(results['max_drawdown']), 2),
            winRate=round(sanitize_float(results['win_rate']), 1),
            profitFactor=round(sanitize_float(results['profit_factor']), 2),
            count=int(results['num_trades']),
            curve=curve_points
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running backtest: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{backtest_id}/trades", response_model=List[Trade])
async def get_backtest_trades(backtest_id: str, db: Session = Depends(get_db)) -> List[Trade]:
    """
    Get trades for a specific backtest.
    """
    backtest_trades = db.query(BacktestTradeModel).filter(
        BacktestTradeModel.backtest_id == backtest_id
    ).order_by(BacktestTradeModel.entry_date.desc()).all()

    trades = []
    for i, bt in enumerate(backtest_trades):
        pair = db.query(PairModel).filter(PairModel.id == bt.pair_id).first()
        pair_name = f"{pair.symbol_a} / {pair.symbol_b}" if pair else bt.pair_id.replace('-', ' / ').upper()

        trade = Trade(
            id=bt.id if isinstance(bt.id, int) else (i + 1),
            pair=pair_name,
            entryDate=bt.entry_date.strftime("%d %b %Y"),
            exitDate=bt.exit_date.strftime("%d %b %Y") if bt.exit_date else "Open",
            direction=bt.direction,
            entryZ=round(sanitize_float(bt.entry_z_score), 2),
            exitZ=round(sanitize_float(bt.exit_z_score), 2),
            holding=int(bt.holding_period or 0),
            pnl=round(sanitize_float(bt.pnl), 2),
            return_val=round(sanitize_float(bt.return_pct), 2)
        )
        trades.append(trade)

    return trades


@router.get("/demo/trades", response_model=List[Trade])
async def get_demo_trades(db: Session = Depends(get_db)) -> List[Trade]:
    """
    Get trades from latest completed backtest if available.
    """
    latest_bt = db.query(BacktestModel).filter(
        BacktestModel.status == "completed"
    ).order_by(BacktestModel.created_at.desc()).first()

    if latest_bt:
        return await get_backtest_trades(latest_bt.id, db)
    return []
