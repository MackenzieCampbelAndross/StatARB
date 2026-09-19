from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class BacktestConfig(BaseModel):
    """Backtest configuration matching frontend interface"""
    entry: float = Field(default=2.0, description="Entry Z-score threshold")
    exit: float = Field(default=0.0, description="Exit Z-score threshold")
    stop: float = Field(default=4.0, description="Stop Z-score threshold")
    holding: int = Field(default=30, description="Maximum holding period in days")
    cost: float = Field(default=0.10, description="Transaction cost percentage")
    slippage: float = Field(default=0.05, description="Slippage percentage")
    position: str = Field(default="Volatility Adjusted", description="Position sizing method")
    start: str = Field(default="2020-01-01", description="Start date")
    end: str = Field(default="2025-12-31", description="End date")
    pair_id: Optional[str] = Field(default=None, description="Optional specific pair to backtest")

    model_config = {
        "json_schema_extra": {
            "example": {
                "entry": 2.0,
                "exit": 0.0,
                "stop": 4.0,
                "holding": 30,
                "cost": 0.10,
                "slippage": 0.05,
                "position": "Volatility Adjusted",
                "start": "2020-01-01",
                "end": "2025-12-31",
                "pair_id": "reliance-tataconsum"
            }
        }
    }


class Trade(BaseModel):
    """Individual trade data"""
    id: int
    pair: str
    entryDate: str
    exitDate: str
    direction: str  # "LONG" or "SHORT"
    entryZ: float
    exitZ: float
    holding: int  # Holding period in days
    pnl: float
    return_val: float = Field(alias="return", description="Return percentage")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "pair": "HDFCBANK / ICICIBANK",
                "entryDate": "01 Mar 2020",
                "exitDate": "04 Mar 2020",
                "direction": "LONG",
                "entryZ": -2.1,
                "exitZ": -0.08,
                "holding": 3,
                "pnl": 1200,
                "return": 0.7
            }
        },
        "populate_by_name": True
    }


class BacktestResult(BaseModel):
    """Backtest results matching frontend interface"""
    id: Optional[str] = None
    initial: float
    final: float
    total: float  # Total return percentage
    cagr: float  # Compound annual growth rate
    sharpe: float  # Sharpe ratio
    sortino: float  # Sortino ratio
    drawdown: float  # Maximum drawdown percentage
    winRate: float  # Win rate percentage
    profitFactor: float  # Profit factor
    count: int  # Number of trades
    curve: Optional[List[dict]] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "initial": 1000000,
                "final": 1184200,
                "total": 18.42,
                "cagr": 3.43,
                "sharpe": 1.31,
                "sortino": 1.84,
                "drawdown": -8.21,
                "winRate": 57.4,
                "profitFactor": 1.64,
                "count": 143
            }
        }
    }


class ExperimentResult(BaseModel):
    """Research experiment result"""
    name: str
    date: str
    entry: float
    exit: float
    return_val: float = Field(alias="return", description="Total return percentage")
    sharpe: float
    drawdown: float  # Maximum drawdown percentage

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Baseline mean reversion",
                "date": "16 Sep 2026",
                "entry": 2.0,
                "exit": 0.0,
                "return": 18.42,
                "sharpe": 1.31,
                "drawdown": -8.21
            }
        },
        "populate_by_name": True
    }
