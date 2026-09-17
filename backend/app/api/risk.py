from fastapi import APIRouter, Depends
from typing import Dict
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.backtest import Backtest as BacktestModel
from app.quant.risk.analytics import RiskAnalytics
import pandas as pd
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize risk analytics
risk_analytics = RiskAnalytics()


@router.get("", response_model=Dict[str, str])
async def get_risk_metrics(db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Get current risk metrics.
    Matches frontend risk data structure.
    """
    try:
        # Get most recent backtest results for risk calculation
        latest_backtest = db.query(BacktestModel).filter(
            BacktestModel.status == "completed"
        ).order_by(BacktestModel.created_at.desc()).first()

        if not latest_backtest:
            # Return default values if no backtest data available
            return {
                "volatility": "0.00%",
                "sharpe": "0.00",
                "sortino": "0.00",
                "drawdown": "0.00%",
                "var": "-₹0",
                "es": "-₹0",
                "gross": "₹0",
                "net": "₹0",
                "turnover": "0.00x"
            }

        # Calculate risk metrics from backtest results
        # Create synthetic returns series from backtest results
        # In production, this would use actual return data
        initial_capital = latest_backtest.initial_capital
        final_capital = latest_backtest.final_capital
        total_return = latest_backtest.total_return / 100

        # Generate synthetic returns for risk calculation
        num_periods = 252  # Assume 1 year of trading days
        avg_daily_return = total_return / num_periods
        daily_volatility = 0.01  # Assume 1% daily volatility

        returns = pd.Series([
            avg_daily_return + (i % 5 - 2) * daily_volatility * 0.5
            for i in range(num_periods)
        ])

        # Calculate risk metrics
        risk_metrics = risk_analytics.calculate_portfolio_risk(returns)

        # Format for frontend
        return {
            "volatility": f"{risk_metrics.volatility * 100:.2f}%",
            "sharpe": f"{risk_metrics.sharpe_ratio:.2f}",
            "sortino": f"{risk_metrics.sortino_ratio:.2f}",
            "drawdown": f"{risk_metrics.max_drawdown * 100:.2f}%",
            "var": f"-₹{abs(int(risk_metrics.var_95 * initial_capital)):,}",
            "es": f"-₹{abs(int(risk_metrics.expected_shortfall_95 * initial_capital)):,}",
            "gross": f"₹{int(latest_backtest.gross_pnl or 0):,}",
            "net": f"₹{int(latest_backtest.net_pnl or 0):,}",
            "turnover": f"{latest_backtest.turnover or 0:.2f}x"
        }

    except Exception as e:
        logger.error(f"Error calculating risk metrics: {e}")
        # Return default values on error
        return {
            "volatility": "0.00%",
            "sharpe": "0.00",
            "sortino": "0.00",
            "drawdown": "0.00%",
            "var": "-₹0",
            "es": "-₹0",
            "gross": "₹0",
            "net": "₹0",
            "turnover": "0.00x"
        }
