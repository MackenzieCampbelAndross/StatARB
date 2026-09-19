import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.quant.cointegration.engle_granger import EngleGrangerCointegration, CorrelationCalculator, CointegrationEngine
from app.quant.spread.calculator import SpreadCalculator
from app.quant.signals.engine import SignalEngine, SignalType
from app.quant.backtesting.engine import BacktestEngine, BacktestConfig
from app.quant.risk.analytics import RiskAnalytics


class TestCorrelationCalculator:
    """Test correlation calculation with deterministic data."""

    def test_perfect_correlation(self):
        """Test perfect positive correlation."""
        series_a = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])
        series_b = pd.Series([2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30])  # Perfectly correlated (2x)

        calc = CorrelationCalculator(min_periods=5)
        result = calc.calculate_pearson_correlation(series_a, series_b)

        assert result['correlation'] == pytest.approx(1.0, rel=1e-5)
        assert result['p_value'] == pytest.approx(0.0, abs=1e-5)
        assert result['observations'] == 15

    def test_negative_correlation(self):
        """Test perfect negative correlation."""
        series_a = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])
        series_b = pd.Series([15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1])  # Perfectly negatively correlated

        calc = CorrelationCalculator(min_periods=5)
        result = calc.calculate_pearson_correlation(series_a, series_b)

        assert result['correlation'] == pytest.approx(-1.0, rel=1e-5)
        assert result['observations'] == 15

    def test_no_correlation(self):
        """Test no correlation."""
        series_a = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])
        series_b = pd.Series([1, -1, 1, -1, 1, -1, 1, -1, 1, -1, 1, -1, 1, -1, 1])  # No clear correlation

        calc = CorrelationCalculator(min_periods=5)
        result = calc.calculate_pearson_correlation(series_a, series_b)

        assert abs(result['correlation']) < 0.5  # Should be low correlation
        assert result['observations'] == 15

    def test_correlation_filter(self):
        """Test correlation threshold filtering."""
        calc = CorrelationCalculator()

        # Should pass
        assert calc.filter_by_correlation(0.8, 0.7) == True
        # Should fail
        assert calc.filter_by_correlation(0.5, 0.7) == False


class TestSpreadCalculator:
    """Test spread calculation with deterministic data."""

    def test_basic_spread(self):
        """Test basic spread calculation."""
        series_a = pd.Series([100, 105, 110, 115, 120])
        series_b = pd.Series([50, 52, 54, 56, 58])
        hedge_ratio = 2.0

        calc = SpreadCalculator()
        spread = calc.calculate_spread(series_a, series_b, hedge_ratio)

        # Expected: [100-2*50, 105-2*52, 110-2*54, 115-2*56, 120-2*58]
        # Expected: [0, 1, 2, 3, 4]
        expected = pd.Series([0, 1, 2, 3, 4])

        assert len(spread) == len(expected)
        for i in range(len(spread)):
            assert spread.iloc[i] == pytest.approx(expected.iloc[i], rel=1e-5)

    def test_rolling_statistics(self):
        """Test rolling statistics calculation."""
        spread = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

        calc = SpreadCalculator()
        rolling_stats = calc.calculate_rolling_statistics(spread, window=3)

        assert 'rolling_mean' in rolling_stats.columns
        assert 'rolling_std' in rolling_stats.columns
        assert len(rolling_stats) == len(spread)

        # Check that first values are NaN (insufficient data)
        assert pd.isna(rolling_stats['rolling_mean'].iloc[0])
        assert pd.isna(rolling_stats['rolling_mean'].iloc[1])

        # Check that later values are calculated
        assert not pd.isna(rolling_stats['rolling_mean'].iloc[2])

    def test_z_score_calculation(self):
        """Test Z-score calculation."""
        spread = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

        calc = SpreadCalculator()
        rolling_stats = calc.calculate_rolling_statistics(spread, window=5)
        z_score = calc.calculate_z_score(
            spread,
            rolling_stats['rolling_mean'],
            rolling_stats['rolling_std'],
            window=5
        )

        assert len(z_score) == len(spread)
        # Z-score should be around 0 for mean-centered data
        assert not pd.isna(z_score.iloc[5])  # Should have data after window

    def test_half_life_calculation(self):
        """Test half-life calculation."""
        # Create mean-reverting series
        np.random.seed(42)
        spread = pd.Series(np.random.randn(100))

        calc = SpreadCalculator()
        result = calc.calculate_half_life(spread, method="regression")

        assert 'half_life' in result
        assert 'lambda' in result
        assert result['half_life'] > 0  # Should be positive for mean-reverting series
        assert result['lambda'] > 0


class TestSignalEngine:
    """Test signal generation with deterministic scenarios."""

    def test_long_signal_generation(self):
        """Test LONG SPREAD signal generation."""
        engine = SignalEngine(entry_z_score=2.0, exit_z_score=0.0)

        # Z-score below entry threshold should trigger LONG SPREAD
        signal = engine.generate_signal(-2.5)

        assert signal['signal'] == SignalType.LONG_SPREAD.value
        assert signal['direction'] == "LONG"
        assert signal['entry_reason'] is not None
        assert signal['confidence'] > 0

    def test_short_signal_generation(self):
        """Test SHORT SPREAD signal generation."""
        engine = SignalEngine(entry_z_score=2.0, exit_z_score=0.0)

        # Z-score above entry threshold should trigger SHORT SPREAD
        signal = engine.generate_signal(2.5)

        assert signal['signal'] == SignalType.SHORT_SPREAD.value
        assert signal['direction'] == "SHORT"
        assert signal['entry_reason'] is not None
        assert signal['confidence'] > 0

    def test_exit_signal_generation(self):
        """Test EXIT signal generation."""
        engine = SignalEngine(entry_z_score=2.0, exit_z_score=0.0)

        # Z-score near zero should trigger EXIT when in position
        signal = engine.generate_signal(0.1, previous_z_score=2.0, current_position="LONG")

        assert signal['signal'] == SignalType.EXIT.value
        assert signal['exit_reason'] is not None

    def test_stop_loss_signal(self):
        """Test stop-loss signal generation."""
        engine = SignalEngine(entry_z_score=2.0, exit_z_score=0.0, stop_z_score=4.0)

        # Z-score beyond stop threshold should trigger EXIT
        signal = engine.generate_signal(4.5, current_position="LONG")

        assert signal['signal'] == SignalType.EXIT.value
        assert "stop-loss" in signal['exit_reason'].lower()

    def test_max_holding_period(self):
        """Test maximum holding period signal."""
        engine = SignalEngine(entry_z_score=2.0, exit_z_score=0.0, max_holding_period=10)

        # Exceeding max holding period should trigger EXIT
        signal = engine.generate_signal(
            1.5,
            current_position="LONG",
            holding_period=10
        )

        assert signal['signal'] == SignalType.EXIT.value
        assert "max holding period" in signal['exit_reason'].lower()

    def test_watch_signal(self):
        """Test WATCH signal when no threshold is met."""
        engine = SignalEngine(entry_z_score=2.0, exit_z_score=0.0)

        # Z-score within thresholds should result in WATCH
        signal = engine.generate_signal(0.5)

        assert signal['signal'] == SignalType.WATCH.value
        assert signal['direction'] == "NONE"


class TestBacktestEngine:
    """Test backtesting engine with deterministic scenarios."""

    def test_backtest_initialization(self):
        """Test backtest engine initialization."""
        config = BacktestConfig(
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2020, 12, 31),
            initial_capital=1000000.0,
            entry_z_score=2.0,
            exit_z_score=0.0,
            stop_z_score=4.0,
            max_holding_period=30,
            transaction_cost=0.1,
            slippage=0.05,
            position_sizing="equal_weight",
            correlation_threshold=0.7,
            coint_p_value=0.05
        )

        engine = BacktestEngine(config)

        assert engine.config.initial_capital == 1000000.0
        assert engine.config.entry_z_score == 2.0
        assert len(engine.trades) == 0
        assert len(engine.equity_curve) == 1  # Initial capital
        assert engine.current_capital == 1000000.0

    def test_position_sizing(self):
        """Test position sizing calculation."""
        config = BacktestConfig(
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2020, 12, 31),
            initial_capital=1000000.0,
            entry_z_score=2.0,
            exit_z_score=0.0,
            stop_z_score=4.0,
            max_holding_period=30,
            transaction_cost=0.1,
            slippage=0.05,
            position_sizing="equal_weight",
            correlation_threshold=0.7,
            coint_p_value=0.05
        )

        engine = BacktestEngine(config)

        # Equal weight should be 10% of capital
        size = engine._calculate_position_size(100.0, 50.0, 2.0)
        assert size == pytest.approx(100000.0, rel=1e-5)  # 10% of 1M

    def test_transaction_cost_calculation(self):
        """Test transaction cost calculation."""
        config = BacktestConfig(
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2020, 12, 31),
            initial_capital=1000000.0,
            entry_z_score=2.0,
            exit_z_score=0.0,
            stop_z_score=4.0,
            max_holding_period=30,
            transaction_cost=0.1,  # 0.1%
            slippage=0.05,
            position_sizing="equal_weight",
            correlation_threshold=0.7,
            coint_p_value=0.05
        )

        engine = BacktestEngine(config)

        # Cost should be 0.1% of notional value
        cost = engine._calculate_transaction_cost(100000.0, 100.0, 50.0)
        expected_cost = (100.0 + 50.0) * 100000.0 * 0.001  # Sum of prices * position size * 0.1%
        assert cost == pytest.approx(expected_cost, rel=1e-5)

    def test_slippage_application(self):
        """Test slippage application."""
        config = BacktestConfig(
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2020, 12, 31),
            initial_capital=1000000.0,
            entry_z_score=2.0,
            exit_z_score=0.0,
            stop_z_score=4.0,
            max_holding_period=30,
            transaction_cost=0.1,
            slippage=0.05,  # 0.05%
            position_sizing="equal_weight",
            correlation_threshold=0.7,
            coint_p_value=0.05
        )

        engine = BacktestEngine(config)

        # Slippage should add to price for LONG
        price_with_slippage = engine._apply_slippage(100.0, "LONG")
        expected = 100.0 * 1.0005  # 100 + 0.05%
        assert price_with_slippage == pytest.approx(expected, rel=1e-5)

        # Slippage should subtract from price for SHORT
        price_with_slippage = engine._apply_slippage(100.0, "SHORT")
        expected = 100.0 * 0.9995  # 100 - 0.05%
        assert price_with_slippage == pytest.approx(expected, rel=1e-5)


class TestRiskAnalytics:
    """Test risk analytics calculations."""

    def test_portfolio_risk_calculation(self):
        """Test portfolio risk metrics calculation."""
        # Create deterministic returns
        returns = pd.Series([0.01, 0.02, -0.01, 0.03, -0.02, 0.01, 0.02, -0.01, 0.03, -0.02])

        risk = RiskAnalytics()
        metrics = risk.calculate_portfolio_risk(returns)

        assert metrics.volatility > 0
        assert metrics.sharpe_ratio is not None
        assert metrics.max_drawdown <= 0  # Drawdown should be negative
        assert metrics.var_95 is not None
        assert metrics.var_99 is not None

    def test_max_drawdown_calculation(self):
        """Test maximum drawdown calculation."""
        # Create series with known drawdown
        returns = pd.Series([0.1, 0.05, -0.15, 0.02, 0.01])  # -15% drawdown

        risk = RiskAnalytics()
        max_dd = risk._calculate_max_drawdown(returns)

        assert max_dd <= 0
        assert max_dd == pytest.approx(-0.15, rel=1e-5)

    def test_var_calculation(self):
        """Test Value at Risk calculation."""
        returns = pd.Series([0.01, 0.02, -0.05, -0.10, -0.15, 0.03, 0.01])

        risk = RiskAnalytics()
        var_95 = risk._calculate_var(returns, 0.95)
        var_99 = risk._calculate_var(returns, 0.99)

        # VaR should be negative (loss)
        assert var_95 < 0
        assert var_99 < 0
        # 99% VaR should be more extreme than 95% VaR
        assert var_99 < var_95

    def test_concentration_risk(self):
        """Test concentration risk calculation."""
        positions = {
            "stock_a": 500000.0,
            "stock_b": 300000.0,
            "stock_c": 200000.0
        }
        total_capital = 1000000.0

        risk = RiskAnalytics()
        concentration = risk.calculate_concentration_risk(positions, total_capital)

        assert concentration['num_positions'] == 3
        assert concentration['max_position_weight'] == 0.5  # 50% in stock_a
        assert concentration['herfindahl_index'] > 0
        assert concentration['herfindahl_index'] < 1

    def test_risk_limit_validation(self):
        """Test risk limit validation."""
        returns = pd.Series([0.01, 0.02, -0.01, 0.03, -0.02])

        risk = RiskAnalytics()
        risk_report = risk.generate_risk_report(returns)

        limits = {
            'max_volatility': 0.5,  # 50% annual volatility
            'max_drawdown': 0.2,  # 20% max drawdown
            'min_sharpe': 0.5  # Minimum Sharpe of 0.5
        }

        validation = risk.validate_risk_limits(risk_report, limits)

        assert 'is_compliant' in validation
        assert 'violations' in validation
        assert 'warnings' in validation


class TestLookAheadBias:
    """Test for look-ahead bias prevention."""

    def test_no_future_data_in_correlation(self):
        """Ensure correlation doesn't use future data."""
        # Create time series with known future pattern
        series_a = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        series_b = pd.Series([2, 4, 6, 8, 10, 12, 14, 16, 18, 20])

        calc = CorrelationCalculator()

        # Calculate correlation with lookback of 5
        result = calc.calculate_pearson_correlation(series_a, series_b, lookback=5)

        # Should only use last 5 observations
        assert result['observations'] == 5  # Should have 5 observations with lookback

    def test_walk_forward_window_separation(self):
        """Ensure walk-forward windows don't overlap improperly."""
        from app.quant.backtesting.walk_forward import WalkForwardValidator

        validator = WalkForwardValidator(
            training_window_days=100,
            testing_window_days=50,
            step_size_days=50
        )

        start_date = datetime(2020, 1, 1)
        end_date = datetime(2020, 12, 31)

        windows = validator.generate_windows(start_date, end_date)

        # Check that windows don't overlap incorrectly
        for i in range(len(windows) - 1):
            current_window = windows[i]
            next_window = windows[i + 1]

            # Training period should not overlap with next testing period
            assert current_window.train_end <= next_window.test_start

    def test_signal_generation_uses_historical_data_only(self):
        """Ensure signal generation only uses historical data."""
        engine = SignalEngine(entry_z_score=2.0, exit_z_score=0.0)

        # Generate signal with only current Z-score
        signal = engine.generate_signal(2.5)

        # Signal should be based solely on current Z-score
        assert signal['z_score'] == 2.5
        assert signal['signal'] is not None


def test_no_duplicate_pairs():
    """Test that pair generation doesn't create duplicates."""
    from app.quant.pairs.generator import PairGenerator

    class MockDB:
        def query(self, model):
            return self

        def all(self):
            return []

        def filter(self, *args):
            return self

    generator = PairGenerator(MockDB())

    # Generate pairs from list of symbols
    symbols = ["A", "B", "C"]
    pairs = generator.generate_all_pairs([
        type('MockInstrument', (), {'id': s}) for s in symbols
    ])

    # Should generate N*(N-1)/2 = 3*2/2 = 3 pairs
    assert len(pairs) == 3

    # Check no duplicates (A/B and B/A should not both exist)
    pair_ids = [generator.generate_pair_id(a, b) for a, b in pairs]
    assert len(pair_ids) == len(set(pair_ids))  # All IDs should be unique


def test_date_alignment():
    """Test that date alignment prevents using future data."""
    from app.data.preprocessing import DataPreprocessor

    preprocessor = DataPreprocessor()

    # Create series with different timestamps
    dates_a = pd.date_range('2020-01-01', periods=10, freq='D')
    dates_b = pd.date_range('2020-01-03', periods=10, freq='D')  # Starts 2 days later

    # Create DataFrames as expected by the preprocessor
    df_a = pd.DataFrame({'timestamp': dates_a, 'value': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]})
    df_b = pd.DataFrame({'timestamp': dates_b, 'value': [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]})

    # Align series
    aligned_a, aligned_b = preprocessor.align_trading_days(df_a, df_b)

    # Aligned series should have same length
    assert len(aligned_a) == len(aligned_b)

    # Aligned series should only have common dates
    common_dates = set(dates_a).intersection(set(dates_b))
    assert len(aligned_a) == len(common_dates)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])