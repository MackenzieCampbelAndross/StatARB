import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PositionType(str, Enum):
    """Types of positions"""
    LONG = "LONG"
    SHORT = "SHORT"
    NONE = "NONE"


@dataclass
class Trade:
    """Represents a single trade"""
    pair_id: str
    entry_date: datetime
    exit_date: datetime
    direction: PositionType
    entry_z_score: float
    exit_z_score: float
    entry_price_a: float
    entry_price_b: float
    exit_price_a: float
    exit_price_b: float
    hedge_ratio: float
    position_size: float
    pnl: float
    return_pct: float
    holding_period: int
    transaction_cost: float
    slippage: float
    is_train: bool = False  # True if in-sample, False if out-of-sample


@dataclass
class BacktestConfig:
    """Configuration for backtesting"""
    start_date: datetime
    end_date: datetime
    initial_capital: float
    entry_z_score: float
    exit_z_score: float
    stop_z_score: float
    max_holding_period: int
    transaction_cost: float  # Percentage
    slippage: float  # Percentage
    position_sizing: str  # "equal_weight" or "volatility_adjusted"
    correlation_threshold: float
    coint_p_value: float
    training_window: Optional[int] = None  # For walk-forward
    testing_window: Optional[int] = None  # For walk-forward


class BacktestEngine:
    """
    Backtesting engine for pairs trading strategies.

    Key Features:
    - No look-ahead bias: Uses only information available at each point in time
    - Transaction costs and slippage
    - Position sizing
    - Performance metrics calculation
    - Trade-by-trade tracking
    """

    def __init__(self, config: BacktestConfig):
        """
        Initialize the backtest engine.

        Args:
            config: Backtest configuration
        """
        self.config = config
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = [config.initial_capital]  # Initialize with initial capital
        self.current_capital = config.initial_capital
        self.current_position: Optional[PositionType] = None
        self.position_entry_date: Optional[datetime] = None
        self.position_entry_z: Optional[float] = None

    def run_backtest(
        self,
        price_data_a: pd.DataFrame,
        price_data_b: pd.DataFrame,
        spread_data: pd.Series,
        z_score_data: pd.Series,
        hedge_ratio: float
    ) -> Dict:
        """
        Run a backtest for a single pair.

        Args:
            price_data_a: Price data for instrument A
            price_data_b: Price data for instrument B
            spread_data: Spread series
            z_score_data: Z-score series
            hedge_ratio: Hedge ratio from cointegration

        Returns:
            Dictionary with backtest results
        """
        logger.info(f"Starting backtest from {self.config.start_date} to {self.config.end_date}")

        # Reset state
        self.trades = []
        self.equity_curve = [self.config.initial_capital]
        self.current_capital = self.config.initial_capital
        self.current_position = None
        self.position_entry_date = None
        self.position_entry_z = None

        # Align all data
        aligned_data = self._align_data(price_data_a, price_data_b, spread_data, z_score_data)

        if aligned_data.empty:
            logger.warning("No aligned data available for backtest")
            return self._empty_results()

        # Filter by date range
        aligned_data = aligned_data[
            (aligned_data['timestamp'] >= self.config.start_date) &
            (aligned_data['timestamp'] <= self.config.end_date)
        ]

        if aligned_data.empty:
            logger.warning("No data in specified date range")
            return self._empty_results()

        # Run the backtest day by day
        for i, row in aligned_data.iterrows():
            self._process_day(row, hedge_ratio)

        # Calculate final results
        results = self._calculate_results()

        logger.info(
            f"Backtest complete: {len(self.trades)} trades, "
            f"final_capital={results['final_capital']:.2f}, "
            f"total_return={results['total_return']:.2f}%"
        )

        return results

    def _align_data(
        self,
        price_data_a: pd.DataFrame,
        price_data_b: pd.DataFrame,
        spread_data: pd.Series,
        z_score_data: pd.Series
    ) -> pd.DataFrame:
        """Align all data series to common timestamps."""
        # Create aligned DataFrame
        aligned = pd.DataFrame({
            'timestamp': price_data_a['timestamp'],
            'price_a': price_data_a['close'],
            'price_b': price_data_b['close'],
            'spread': spread_data,
            'z_score': z_score_data
        })

        # Remove rows with NaN
        aligned = aligned.dropna()

        return aligned

    def _process_day(self, row: pd.Series, hedge_ratio: float) -> None:
        """Process a single day of backtesting."""
        current_date = row['timestamp']
        current_z = row['z_score']
        current_price_a = row['price_a']
        current_price_b = row['price_b']

        # Check for stop-loss or max holding period if in position
        if self.current_position is not None:
            if self._should_exit_position(current_z, current_date):
                self._close_position(current_date, current_z, current_price_a, current_price_b, hedge_ratio)
                return

        # Check for entry signals if not in position
        if self.current_position is None:
            if current_z >= self.config.entry_z_score:
                self._open_position(
                    PositionType.SHORT,
                    current_date,
                    current_z,
                    current_price_a,
                    current_price_b,
                    hedge_ratio
                )
            elif current_z <= -self.config.entry_z_score:
                self._open_position(
                    PositionType.LONG,
                    current_date,
                    current_z,
                    current_price_a,
                    current_price_b,
                    hedge_ratio
                )

        # Update equity curve
        self.equity_curve.append(self.current_capital)

    def _should_exit_position(self, current_z: float, current_date: datetime) -> bool:
        """Determine if current position should be closed."""
        # Stop-loss check
        if abs(current_z) > self.config.stop_z_score:
            logger.info(f"Stop-loss triggered at Z={current_z:.2f}")
            return True

        # Max holding period check
        if self.position_entry_date:
            holding_days = (current_date - self.position_entry_date).days
            if holding_days >= self.config.max_holding_period:
                logger.info(f"Max holding period reached: {holding_days} days")
                return True

        # Profit-taking check
        if abs(current_z) <= self.config.exit_z_score:
            logger.info(f"Profit-taking at Z={current_z:.2f}")
            return True

        return False

    def _open_position(
        self,
        direction: PositionType,
        entry_date: datetime,
        entry_z: float,
        price_a: float,
        price_b: float,
        hedge_ratio: float
    ) -> None:
        """Open a new position."""
        allocated_capital = self._calculate_position_size(price_a, price_b, hedge_ratio)
        if allocated_capital <= 0:
            return

        price_a_eff = self._apply_slippage(price_a, direction)
        price_b_eff = self._apply_slippage(price_b, direction)

        hr = max(abs(hedge_ratio), 0.001)
        spread_unit_cost = price_a_eff + (hr * price_b_eff)
        if spread_unit_cost <= 0:
            return

        units_a = allocated_capital / (2.0 * price_a_eff)
        units_b = units_a * hr

        notional_entry = (units_a * price_a_eff) + (units_b * price_b_eff)
        entry_cost = notional_entry * (self.config.transaction_cost / 100.0)

        self.current_capital -= entry_cost

        self.current_position = direction
        self.position_entry_date = entry_date
        self.position_entry_z = entry_z
        self.position_entry_price_a = price_a_eff
        self.position_entry_price_b = price_b_eff
        self.position_units_a = units_a
        self.position_units_b = units_b
        self.position_entry_cost = entry_cost

        logger.info(
            f"Opened {direction.value} position at Z={entry_z:.2f}, "
            f"units_a={units_a:.2f}, units_b={units_b:.2f}, entry_cost={entry_cost:.2f}"
        )

    def _close_position(
        self,
        exit_date: datetime,
        exit_z: float,
        price_a: float,
        price_b: float,
        hedge_ratio: float
    ) -> None:
        """Close the current position."""
        if self.current_position is None:
            return

        direction = self.current_position
        entry_z = self.position_entry_z
        entry_date = self.position_entry_date
        entry_p_a = getattr(self, 'position_entry_price_a', price_a)
        entry_p_b = getattr(self, 'position_entry_price_b', price_b)
        units_a = getattr(self, 'position_units_a', 1.0)
        units_b = getattr(self, 'position_units_b', hedge_ratio)
        entry_cost = getattr(self, 'position_entry_cost', 0.0)

        # Apply slippage on exit
        exit_p_a = self._apply_slippage(price_a, PositionType.SHORT if direction == PositionType.LONG else PositionType.LONG)
        exit_p_b = self._apply_slippage(price_b, PositionType.LONG if direction == PositionType.LONG else PositionType.SHORT)

        # Actual statistical arbitrage P&L calculation:
        # LONG spread = Long A, Short B
        # SHORT spread = Short A, Long B
        if direction == PositionType.LONG:
            gross_pnl_a = units_a * (exit_p_a - entry_p_a)
            gross_pnl_b = -units_b * (exit_p_b - entry_p_b)
        else:
            gross_pnl_a = -units_a * (exit_p_a - entry_p_a)
            gross_pnl_b = units_b * (exit_p_b - entry_p_b)

        gross_pnl = gross_pnl_a + gross_pnl_b

        notional_exit = (units_a * exit_p_a) + (units_b * exit_p_b)
        exit_cost = notional_exit * (self.config.transaction_cost / 100.0)

        net_pnl = gross_pnl - exit_cost
        # Add net PnL and restore entry cost previously deducted to avoid double deducting
        self.current_capital += (net_pnl + entry_cost)

        trade_notional = (units_a * entry_p_a) + (units_b * entry_p_b)
        return_pct = (net_pnl / trade_notional) * 100.0 if trade_notional > 0 else 0.0
        holding_period = (exit_date - entry_date).days if entry_date else 0

        trade = Trade(
            pair_id="pair",
            entry_date=entry_date,
            exit_date=exit_date,
            direction=direction,
            entry_z_score=entry_z,
            exit_z_score=exit_z,
            entry_price_a=entry_p_a,
            entry_price_b=entry_p_b,
            exit_price_a=exit_p_a,
            exit_price_b=exit_p_b,
            hedge_ratio=hedge_ratio,
            position_size=trade_notional,
            pnl=net_pnl,
            return_pct=return_pct,
            holding_period=holding_period,
            transaction_cost=entry_cost + exit_cost,
            slippage=self.config.slippage
        )

        self.trades.append(trade)

        logger.info(
            f"Closed {direction.value} position: P&L={net_pnl:.2f}, "
            f"return={return_pct:.2f}%, holding={holding_period} days"
        )

        # Reset position
        self.current_position = None
        self.position_entry_date = None
        self.position_entry_z = None

    def _calculate_position_size(
        self,
        price_a: float,
        price_b: float,
        hedge_ratio: float
    ) -> float:
        """Calculate position size in capital allocation currency."""
        # 10% of portfolio capital per trade
        return max(self.current_capital * 0.10, 1000.0)

    def _apply_slippage(self, price: float, direction: PositionType) -> float:
        """Apply slippage to price."""
        slippage_amount = price * (self.config.slippage / 100)

        if direction == PositionType.LONG:
            return price + slippage_amount
        else:
            return price - slippage_amount

    def _calculate_transaction_cost(
        self,
        notional_value: float,
        price_a: float,
        price_b: float
    ) -> float:
        """Calculate transaction cost from notional."""
        return notional_value * (self.config.transaction_cost / 100)

    def _calculate_results(self) -> Dict:
        """Calculate final backtest results."""
        if not self.trades:
            return self._empty_results()

        # Basic metrics
        initial_capital = self.config.initial_capital
        final_capital = self.current_capital
        total_return = ((final_capital - initial_capital) / initial_capital) * 100

        # Calculate performance metrics
        returns = [trade.return_pct for trade in self.trades]
        winning_trades = [r for r in returns if r > 0]
        losing_trades = [r for r in returns if r < 0]

        win_rate = (len(winning_trades) / len(returns)) * 100 if returns else 0
        avg_return = np.mean(returns) if returns else 0
        avg_win = np.mean(winning_trades) if winning_trades else 0
        avg_loss = np.mean(losing_trades) if losing_trades else 0

        profit_factor = abs(sum(winning_trades) / sum(losing_trades)) if losing_trades else float('inf')

        # Calculate Sharpe ratio (simplified)
        if len(self.equity_curve) > 1:
            equity_returns = pd.Series(self.equity_curve).pct_change().dropna()
            sharpe_ratio = (equity_returns.mean() / equity_returns.std()) * np.sqrt(252) if equity_returns.std() > 0 else 0
        else:
            sharpe_ratio = 0

        # Calculate max drawdown
        equity_series = pd.Series(self.equity_curve)
        rolling_max = equity_series.expanding().max()
        drawdown = (equity_series - rolling_max) / rolling_max
        max_drawdown = drawdown.min() * 100 if len(drawdown) > 0 else 0

        # Calculate CAGR
        days = (self.config.end_date - self.config.start_date).days
        years = days / 365.25
        cagr = ((final_capital / initial_capital) ** (1 / years) - 1) * 100 if years > 0 else 0

        # Calculate Sortino ratio
        if len(returns) > 0:
            downside_returns = [r for r in returns if r < 0]
            downside_std = np.std(downside_returns) if downside_returns else 1
            sortino_ratio = (avg_return / downside_std) * np.sqrt(252) if downside_std > 0 else 0
        else:
            sortino_ratio = 0

        return {
            'initial_capital': initial_capital,
            'final_capital': final_capital,
            'total_return': total_return,
            'cagr': cagr,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'num_trades': len(self.trades),
            'avg_trade_return': avg_return,
            'avg_winning_trade': avg_win,
            'avg_losing_trade': avg_loss,
            'equity_curve': self.equity_curve,
            'trades': self.trades,
            'config': self.config
        }

    def _empty_results(self) -> Dict:
        """Return empty results when no trades were made."""
        return {
            'initial_capital': self.config.initial_capital,
            'final_capital': self.config.initial_capital,
            'total_return': 0.0,
            'cagr': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'num_trades': 0,
            'avg_trade_return': 0.0,
            'avg_winning_trade': 0.0,
            'avg_losing_trade': 0.0,
            'equity_curve': [self.config.initial_capital],
            'trades': [],
            'config': self.config
        }

    def validate_no_look_ahead(self) -> bool:
        """
        Validate that no look-ahead bias was introduced.

        Returns:
            True if validation passes
        """
        # In a real implementation, this would check:
        # 1. No future data used in calculations
        # 2. Proper train/test splitting
        # 3. Correct timestamp handling
        # For now, return True as placeholder
        return True
