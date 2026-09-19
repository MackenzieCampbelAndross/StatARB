from sqlalchemy import Column, String, DateTime, Float, Integer, Index, ForeignKey, Text
from sqlalchemy.sql import func
from app.database.base import Base


class Backtest(Base):
    """Backtest run configurations and results"""
    __tablename__ = "backtests"

    id = Column(String, primary_key=True)  # Unique backtest ID
    name = Column(String, nullable=True)  # Optional backtest name
    start_date = Column(DateTime, nullable=False)  # Backtest start date
    end_date = Column(DateTime, nullable=False)  # Backtest end date
    initial_capital = Column(Float, nullable=False)  # Starting capital
    final_capital = Column(Float, nullable=True)  # Ending capital
    total_return = Column(Float, nullable=True)  # Total return percentage
    cagr = Column(Float, nullable=True)  # Compound annual growth rate
    sharpe_ratio = Column(Float, nullable=True)  # Sharpe ratio
    sortino_ratio = Column(Float, nullable=True)  # Sortino ratio
    max_drawdown = Column(Float, nullable=True)  # Maximum drawdown percentage
    volatility = Column(Float, nullable=True)  # Portfolio volatility
    win_rate = Column(Float, nullable=True)  # Win rate percentage
    profit_factor = Column(Float, nullable=True)  # Profit factor
    num_trades = Column(Integer, nullable=True)  # Number of trades
    avg_trade_return = Column(Float, nullable=True)  # Average trade return
    avg_holding_period = Column(Float, nullable=True)  # Average holding period (days)
    turnover = Column(Float, nullable=True)  # Portfolio turnover
    gross_pnl = Column(Float, nullable=True)  # Gross P&L
    net_pnl = Column(Float, nullable=True)  # Net P&L (after costs)

    # Configuration parameters
    entry_z_score = Column(Float, nullable=False)  # Entry Z-score threshold
    exit_z_score = Column(Float, nullable=False)  # Exit Z-score threshold
    stop_z_score = Column(Float, nullable=False)  # Stop Z-score threshold
    holding_period = Column(Integer, nullable=False)  # Maximum holding period
    transaction_cost = Column(Float, nullable=False)  # Transaction cost percentage
    slippage = Column(Float, nullable=False)  # Slippage percentage
    position_sizing = Column(String, nullable=True)  # Position sizing method
    correlation_threshold = Column(Float, nullable=True)  # Correlation filter threshold
    coint_p_value = Column(Float, nullable=True)  # Cointegration p-value threshold

    # Walk-forward parameters
    training_window = Column(Integer, nullable=True)  # Training window size (days)
    testing_window = Column(Integer, nullable=True)  # Testing window size (days)

    status = Column(String, default="completed")  # running, completed, failed
    error_message = Column(Text, nullable=True)  # Error message if failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index('idx_backtest_dates', 'start_date', 'end_date'),
        Index('idx_backtest_status', 'status'),
        Index('idx_backtest_created', 'created_at'),
    )


class BacktestTrade(Base):
    """Individual trades from a backtest"""
    __tablename__ = "backtest_trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    backtest_id = Column(String, nullable=False, index=True)  # Reference to backtest
    pair_id = Column(String, nullable=False, index=True)  # Reference to pair
    entry_date = Column(DateTime(timezone=True), nullable=False)
    exit_date = Column(DateTime(timezone=True), nullable=False)
    direction = Column(String, nullable=False)  # LONG or SHORT
    entry_z_score = Column(Float, nullable=False)
    exit_z_score = Column(Float, nullable=False)
    holding_period = Column(Integer, nullable=False)  # Holding period in days
    entry_price_a = Column(Float, nullable=False)
    entry_price_b = Column(Float, nullable=False)
    exit_price_a = Column(Float, nullable=False)
    exit_price_b = Column(Float, nullable=False)
    hedge_ratio = Column(Float, nullable=False)
    position_size = Column(Float, nullable=True)  # Position size
    pnl = Column(Float, nullable=False)  # Profit/Loss
    return_pct = Column(Float, nullable=False)  # Return percentage
    transaction_cost = Column(Float, nullable=True)  # Transaction cost incurred
    slippage = Column(Float, nullable=True)  # Slippage incurred
    is_train = Column(Integer, default=0)  # 1 if in-sample, 0 if out-of-sample
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_backtest_trade_backtest', 'backtest_id'),
        Index('idx_backtest_trade_pair', 'pair_id'),
        Index('idx_backtest_trade_dates', 'entry_date', 'exit_date'),
    )
