import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

from .engine import BacktestEngine, BacktestConfig, Trade

logger = logging.getLogger(__name__)


@dataclass
class WalkForwardWindow:
    """Represents a single walk-forward window"""
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    window_number: int


@dataclass
class WalkForwardResult:
    """Results from walk-forward validation"""
    in_sample_results: Dict
    out_of_sample_results: Dict
    window: WalkForwardWindow
    parameters: Dict


class WalkForwardValidator:
    """
    Implements walk-forward validation to avoid look-ahead bias.

    Concept:
    1. Training period: Calculate parameters (hedge ratio, etc.)
    2. Testing period: Apply parameters to unseen data
    3. Move window forward
    4. Repeat

    This ensures that parameters are never calculated using future data.
    """

    def __init__(
        self,
        training_window_days: int = 252,  # ~1 year of trading days
        testing_window_days: int = 63,    # ~3 months of trading days
        step_size_days: int = 63          # Move forward by 3 months
    ):
        """
        Initialize the walk-forward validator.

        Args:
            training_window_days: Size of training window in days
            testing_window_days: Size of testing window in days
            step_size_days: Step size for moving window
        """
        self.training_window_days = training_window_days
        self.testing_window_days = testing_window_days
        self.step_size_days = step_size_days

    def generate_windows(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[WalkForwardWindow]:
        """
        Generate walk-forward windows for the specified date range.

        Args:
            start_date: Overall start date
            end_date: Overall end date

        Returns:
            List of walk-forward windows
        """
        windows = []
        current_date = start_date
        window_number = 0

        while True:
            # Calculate training window
            train_start = current_date
            train_end = train_start + timedelta(days=self.training_window_days)

            # Calculate testing window
            test_start = train_end
            test_end = test_start + timedelta(days=self.testing_window_days)

            # Check if we've exceeded the end date
            if test_end > end_date:
                # Adjust final window to fit within end date
                if test_start >= end_date:
                    break
                test_end = end_date

            # Create window
            window = WalkForwardWindow(
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                window_number=window_number
            )
            windows.append(window)

            logger.info(
                f"Window {window_number}: Train {train_start.date()} to {train_end.date()}, "
                f"Test {test_start.date()} to {test_end.date()}"
            )

            # Move forward
            current_date = test_start + timedelta(days=self.step_size_days)
            window_number += 1

            # Stop if we can't create another full window
            if current_date + timedelta(days=self.training_window_days + self.testing_window_days) > end_date:
                break

        logger.info(f"Generated {len(windows)} walk-forward windows")
        return windows

    def run_walk_forward(
        self,
        price_data_a: pd.DataFrame,
        price_data_b: pd.DataFrame,
        spread_data: pd.Series,
        z_score_data: pd.Series,
        base_config: BacktestConfig,
        windows: Optional[List[WalkForwardWindow]] = None
    ) -> Dict:
        """
        Run walk-forward validation.

        Args:
            price_data_a: Price data for instrument A
            price_data_b: Price data for instrument B
            spread_data: Spread series
            z_score_data: Z-score series
            base_config: Base backtest configuration
            windows: Optional pre-generated windows

        Returns:
            Dictionary with walk-forward results
        """
        if windows is None:
            windows = self.generate_windows(base_config.start_date, base_config.end_date)

        if not windows:
            logger.warning("No walk-forward windows generated")
            return self._empty_walk_forward_results()

        all_results = []
        all_trades = []

        for window in windows:
            logger.info(f"Processing window {window.window_number}")

            # Split data into training and testing periods
            train_data = self._get_window_data(
                price_data_a, price_data_b, spread_data, z_score_data,
                window.train_start, window.train_end
            )

            test_data = self._get_window_data(
                price_data_a, price_data_b, spread_data, z_score_data,
                window.test_start, window.test_end
            )

            if train_data.empty or test_data.empty:
                logger.warning(f"Insufficient data for window {window.window_number}")
                continue

            # Calculate parameters on training data
            parameters = self._calculate_parameters(train_data)

            # Run in-sample backtest (for validation)
            train_config = self._create_window_config(base_config, window.train_start, window.train_end)
            train_engine = BacktestEngine(train_config)
            in_sample_results = train_engine.run_backtest(
                train_data['price_a'], train_data['price_b'],
                train_data['spread'], train_data['z_score'],
                parameters['hedge_ratio']
            )

            # Run out-of-sample backtest (real test)
            test_config = self._create_window_config(base_config, window.test_start, window.test_end)
            test_engine = BacktestEngine(test_config)
            out_of_sample_results = test_engine.run_backtest(
                test_data['price_a'], test_data['price_b'],
                test_data['spread'], test_data['z_score'],
                parameters['hedge_ratio']
            )

            # Store results
            window_result = WalkForwardResult(
                in_sample_results=in_sample_results,
                out_of_sample_results=out_of_sample_results,
                window=window,
                parameters=parameters
            )
            all_results.append(window_result)

            # Collect trades
            for trade in test_engine.trades:
                trade.is_train = False  # Mark as out-of-sample
                all_trades.append(trade)

        # Aggregate results
        aggregated_results = self._aggregate_results(all_results, all_trades)

        logger.info(
            f"Walk-forward complete: {len(all_results)} windows, "
            f"total trades: {len(all_trades)}"
        )

        return aggregated_results

    def _get_window_data(
        self,
        price_data_a: pd.DataFrame,
        price_data_b: pd.DataFrame,
        spread_data: pd.Series,
        z_score_data: pd.Series,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """Get data for a specific time window."""
        # Create aligned DataFrame
        aligned = pd.DataFrame({
            'timestamp': price_data_a['timestamp'],
            'price_a': price_data_a['close'],
            'price_b': price_data_b['close'],
            'spread': spread_data,
            'z_score': z_score_data
        })

        # Filter by date range
        window_data = aligned[
            (aligned['timestamp'] >= start_date) &
            (aligned['timestamp'] <= end_date)
        ].copy()

        return {
            'price_a': window_data[['timestamp', 'close']].rename(columns={'close': 'price'}),
            'price_b': window_data[['timestamp', 'close']].rename(columns={'close': 'price'}),
            'spread': window_data['spread'],
            'z_score': window_data['z_score']
        }

    def _calculate_parameters(self, train_data: Dict) -> Dict:
        """
        Calculate parameters using training data only.

        This prevents look-ahead bias.
        """
        # Calculate hedge ratio from training data
        # Simplified - in production, use proper cointegration analysis
        price_a = train_data['price_a']['price']
        price_b = train_data['price_b']['price']

        # Simple hedge ratio calculation (would use cointegration in production)
        hedge_ratio = np.cov(price_a, price_b)[0, 1] / np.var(price_b)

        # Calculate other statistics
        spread_mean = train_data['spread'].mean()
        spread_std = train_data['spread'].std()

        return {
            'hedge_ratio': hedge_ratio,
            'spread_mean': spread_mean,
            'spread_std': spread_std,
            'training_observations': len(train_data['spread'])
        }

    def _create_window_config(
        self,
        base_config: BacktestConfig,
        start_date: datetime,
        end_date: datetime
    ) -> BacktestConfig:
        """Create configuration for a specific window."""
        return BacktestConfig(
            start_date=start_date,
            end_date=end_date,
            initial_capital=base_config.initial_capital,
            entry_z_score=base_config.entry_z_score,
            exit_z_score=base_config.exit_z_score,
            stop_z_score=base_config.stop_z_score,
            max_holding_period=base_config.max_holding_period,
            transaction_cost=base_config.transaction_cost,
            slippage=base_config.slippage,
            position_sizing=base_config.position_sizing,
            correlation_threshold=base_config.correlation_threshold,
            coint_p_value=base_config.coint_p_value,
            training_window=base_config.training_window,
            testing_window=base_config.testing_window
        )

    def _aggregate_results(
        self,
        window_results: List[WalkForwardResult],
        all_trades: List[Trade]
    ) -> Dict:
        """Aggregate results from all windows."""
        if not window_results:
            return self._empty_walk_forward_results()

        # Separate in-sample and out-of-sample results
        in_sample_returns = [r.in_sample_results['total_return'] for r in window_results]
        out_of_sample_returns = [r.out_of_sample_results['total_return'] for r in window_results]

        in_sample_sharpe = [r.in_sample_results['sharpe_ratio'] for r in window_results]
        out_of_sample_sharpe = [r.out_of_sample_results['sharpe_ratio'] for r in window_results]

        # Calculate aggregate statistics
        total_in_sample_return = np.mean(in_sample_returns)
        total_out_of_sample_return = np.mean(out_of_sample_returns)

        avg_in_sample_sharpe = np.mean(in_sample_sharpe)
        avg_out_of_sample_sharpe = np.mean(out_of_sample_sharpe)

        # Calculate consistency (how many windows were profitable)
        profitable_in_sample = sum(1 for r in in_sample_returns if r > 0)
        profitable_out_of_sample = sum(1 for r in out_of_sample_returns if r > 0)

        consistency_in_sample = (profitable_in_sample / len(in_sample_returns)) * 100
        consistency_out_of_sample = (profitable_out_of_sample / len(out_of_sample_returns)) * 100

        # Calculate total P&L from all trades
        total_pnl = sum(trade.pnl for trade in all_trades)
        total_trades_count = len(all_trades)

        return {
            'num_windows': len(window_results),
            'total_trades': total_trades_count,
            'total_pnl': total_pnl,

            # In-sample metrics
            'in_sample_avg_return': total_in_sample_return,
            'in_sample_avg_sharpe': avg_in_sample_sharpe,
            'in_sample_consistency': consistency_in_sample,
            'in_sample_returns': in_sample_returns,

            # Out-of-sample metrics (these are the important ones)
            'out_of_sample_avg_return': total_out_of_sample_return,
            'out_of_sample_avg_sharpe': avg_out_of_sample_sharpe,
            'out_of_sample_consistency': consistency_out_of_sample,
            'out_of_sample_returns': out_of_sample_returns,

            # Window-by-window results
            'window_results': window_results,
            'all_trades': all_trades,

            # Validation metrics
            'overfitting_indicator': total_in_sample_return - total_out_of_sample_return,
            'stability_score': np.std(out_of_sample_returns) if out_of_sample_returns else 0
        }

    def _empty_walk_forward_results(self) -> Dict:
        """Return empty results when no windows were processed."""
        return {
            'num_windows': 0,
            'total_trades': 0,
            'total_pnl': 0,
            'in_sample_avg_return': 0,
            'in_sample_avg_sharpe': 0,
            'in_sample_consistency': 0,
            'in_sample_returns': [],
            'out_of_sample_avg_return': 0,
            'out_of_sample_avg_sharpe': 0,
            'out_of_sample_consistency': 0,
            'out_of_sample_returns': [],
            'window_results': [],
            'all_trades': [],
            'overfitting_indicator': 0,
            'stability_score': 0
        }

    def validate_walk_forward_setup(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """
        Validate the walk-forward setup before running.

        Args:
            start_date: Overall start date
            end_date: Overall end date

        Returns:
            Dictionary with validation results
        """
        issues = []
        warnings = []

        total_days = (end_date - start_date).days
        required_days = self.training_window_days + self.testing_window_days

        if total_days < required_days:
            issues.append(
                f"Insufficient data: {total_days} days available, "
                f"required {required_days} days for one window"
            )

        if total_days < required_days * 2:
            warnings.append(
                f"Limited data for walk-forward: only {total_days // required_days} windows possible"
            )

        # Check window sizes
        if self.training_window_days < 100:
            warnings.append("Training window < 100 days may be insufficient for stable parameters")

        if self.testing_window_days < 20:
            warnings.append("Testing window < 20 days may not provide reliable results")

        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'total_days': total_days,
            'required_days_per_window': required_days,
            'estimated_windows': max(0, (total_days - required_days) // self.step_size_days)
        }
