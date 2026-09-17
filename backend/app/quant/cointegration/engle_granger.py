import pandas as pd
import numpy as np
from typing import Tuple, Dict, Optional
from scipy import stats
from statsmodels.tsa.stattools import coint, adfuller
import statsmodels.api as sm
import logging

logger = logging.getLogger(__name__)


class EngleGrangerCointegration:
    """
    Implements the Engle-Granger two-step cointegration test.

    Methodology:
    1. Step 1: Estimate the long-run equilibrium relationship: Y_t = α + βX_t + ε_t
    2. Step 2: Test the residuals ε_t for stationarity using ADF test

    If residuals are stationary, the series are cointegrated.
    """

    def __init__(self, significance_level: float = 0.05):
        """
        Initialize the Engle-Granger cointegration test.

        Args:
            significance_level: P-value threshold for cointegration decision
        """
        self.significance_level = significance_level

    def test_cointegration(
        self,
        series_y: pd.Series,
        series_x: pd.Series,
        method: str = "engle-granger"
    ) -> Dict:
        """
        Perform cointegration test between two series.

        Args:
            series_y: Dependent variable (Y)
            series_x: Independent variable (X)
            method: Method to use ('engle-granger' or 'coint')

        Returns:
            Dictionary with test results
        """
        # Ensure series are aligned
        if len(series_y) != len(series_x):
            raise ValueError("Series must have the same length")

        # Remove NaN values
        valid_indices = ~(series_y.isna() | series_x.isna())
        series_y = series_y[valid_indices]
        series_x = series_x[valid_indices]

        if len(series_y) < 10:
            logger.warning("Too few observations for reliable cointegration test")
            return self._insufficient_data_result()

        if method == "engle-granger":
            return self._engle_granger_test(series_y, series_x)
        elif method == "coint":
            return self._statsmodels_coint(series_y, series_x)
        else:
            raise ValueError(f"Unknown method: {method}")

    def _engle_granger_test(self, series_y: pd.Series, series_x: pd.Series) -> Dict:
        """
        Manual implementation of Engle-Granger two-step procedure.

        Step 1: Estimate long-run relationship: Y = α + βX + ε
        Step 2: Test residuals for stationarity using ADF test
        """
        # Step 1: Estimate the long-run relationship
        X = sm.add_constant(series_x)  # Add constant for intercept
        model = sm.OLS(series_y, X).fit()

        alpha = model.params[0]  # Intercept
        beta = model.params[1]   # Slope (hedge ratio)
        residuals = model.resid

        # Step 2: Test residuals for stationarity
        adf_result = adfuller(residuals, maxlag=1)

        is_cointegrated = adf_result[1] < self.significance_level

        result = {
            'method': 'engle-granger',
            'is_cointegrated': is_cointegrated,
            'alpha': alpha,
            'hedge_ratio': beta,
            'adf_statistic': adf_result[0],
            'adf_p_value': adf_result[1],
            'critical_values': adf_result[4],
            'significance_level': self.significance_level,
            'observations': len(series_y),
            'residuals_mean': residuals.mean(),
            'residuals_std': residuals.std()
        }

        logger.info(
            f"Engle-Granger test: is_cointegrated={is_cointegrated}, "
            f"adf_p_value={adf_result[1]:.4f}, hedge_ratio={beta:.4f}"
        )

        return result

    def _statsmodels_coint(self, series_y: pd.Series, series_x: pd.Series) -> Dict:
        """
        Use statsmodels built-in coint function.
        """
        try:
            coint_t, pvalue, crit_value = coint(series_y, series_x)

            is_cointegrated = pvalue < self.significance_level

            # Calculate hedge ratio using OLS
            X = sm.add_constant(series_x)
            model = sm.OLS(series_y, X).fit()
            hedge_ratio = model.params[1]
            alpha = model.params[0]

            result = {
                'method': 'statsmodels-coint',
                'is_cointegrated': is_cointegrated,
                'alpha': alpha,
                'hedge_ratio': hedge_ratio,
                'coint_t_statistic': coint_t,
                'coint_p_value': pvalue,
                'critical_values': crit_value,
                'significance_level': self.significance_level,
                'observations': len(series_y)
            }

            logger.info(
                f"Statsmodels coint test: is_cointegrated={is_cointegrated}, "
                f"p_value={pvalue:.4f}, hedge_ratio={hedge_ratio:.4f}"
            )

            return result

        except Exception as e:
            logger.error(f"Error in statsmodels coint test: {e}")
            return self._error_result(str(e))

    def _insufficient_data_result(self) -> Dict:
        """Return result for insufficient data case."""
        return {
            'method': 'engle-granger',
            'is_cointegrated': False,
            'error': 'Insufficient data for cointegration test',
            'observations': 0
        }

    def _error_result(self, error_message: str) -> Dict:
        """Return result for error case."""
        return {
            'method': 'engle-granger',
            'is_cointegrated': False,
            'error': error_message
        }


class CorrelationCalculator:
    """
    Calculates correlation coefficients between time series.
    Used as a pre-filter before expensive cointegration testing.
    """

    def __init__(self, min_periods: int = 30):
        """
        Initialize the correlation calculator.

        Args:
            min_periods: Minimum number of observations required
        """
        self.min_periods = min_periods

    def calculate_pearson_correlation(
        self,
        series_a: pd.Series,
        series_b: pd.Series,
        lookback: Optional[int] = None
    ) -> Dict:
        """
        Calculate Pearson correlation coefficient.

        Args:
            series_a: First time series
            series_b: Second time series
            lookback: Number of recent periods to use (None = all available)

        Returns:
            Dictionary with correlation results
        """
        # Align series
        aligned_a, aligned_b = series_a.align(series_b, join='inner')

        # Remove NaN values
        valid_mask = ~(aligned_a.isna() | aligned_b.isna())
        aligned_a = aligned_a[valid_mask]
        aligned_b = aligned_b[valid_mask]

        # Apply lookback if specified
        if lookback is not None and lookback < len(aligned_a):
            aligned_a = aligned_a.tail(lookback)
            aligned_b = aligned_b.tail(lookback)

        # Check minimum periods
        if len(aligned_a) < self.min_periods:
            logger.warning(
                f"Insufficient data for correlation: {len(aligned_a)} < {self.min_periods}"
            )
            return {
                'correlation': np.nan,
                'p_value': np.nan,
                'observations': len(aligned_a),
                'error': 'Insufficient data'
            }

        # Calculate correlation
        correlation, p_value = stats.pearsonr(aligned_a, aligned_b)

        result = {
            'correlation': correlation,
            'p_value': p_value,
            'observations': len(aligned_a),
            'lookback': lookback or len(aligned_a),
            'method': 'pearson'
        }

        logger.info(f"Pearson correlation: {correlation:.4f} (p={p_value:.4f})")

        return result

    def calculate_rolling_correlation(
        self,
        series_a: pd.Series,
        series_b: pd.Series,
        window: int = 30
    ) -> pd.Series:
        """
        Calculate rolling correlation coefficient.

        Args:
            series_a: First time series
            series_b: Second time series
            window: Rolling window size

        Returns:
            Series of rolling correlations
        """
        # Align series
        aligned_a, aligned_b = series_a.align(series_b, join='inner')

        # Calculate rolling correlation
        rolling_corr = aligned_a.rolling(window=window).corr(aligned_b)

        return rolling_corr

    def filter_by_correlation(
        self,
        correlation: float,
        threshold: float
    ) -> bool:
        """
        Filter pairs based on correlation threshold.

        Args:
            correlation: Correlation coefficient
            threshold: Minimum correlation threshold

        Returns:
            True if correlation meets threshold
        """
        return abs(correlation) >= threshold


class CointegrationEngine:
    """
    Complete cointegration analysis engine combining correlation filtering
    and Engle-Granger cointegration testing.
    """

    def __init__(
        self,
        correlation_threshold: float = 0.70,
        coint_significance: float = 0.05,
        min_observations: int = 30
    ):
        """
        Initialize the cointegration engine.

        Args:
            correlation_threshold: Minimum correlation for cointegration test
            coint_significance: P-value threshold for cointegration
            min_observations: Minimum observations required
        """
        self.correlation_threshold = correlation_threshold
        self.coint_significance = coint_significance
        self.min_observations = min_observations

        self.correlation_calc = CorrelationCalculator(min_observations)
        self.coint_test = EngleGrangerCointegration(coint_significance)

    def analyze_pair(
        self,
        series_a: pd.Series,
        series_b: pd.Series,
        lookback: Optional[int] = None
    ) -> Dict:
        """
        Complete analysis of a pair: correlation filter + cointegration test.

        Args:
            series_a: First time series
            series_b: Second time series
            lookback: Lookback period for correlation

        Returns:
            Dictionary with complete analysis results
        """
        result = {
            'correlation_passed': False,
            'is_cointegrated': False,
            'correlation': None,
            'hedge_ratio': None,
            'coint_p_value': None,
            'error': None
        }

        try:
            # Step 1: Calculate correlation
            corr_result = self.correlation_calc.calculate_pearson_correlation(
                series_a, series_b, lookback
            )

            result['correlation'] = corr_result['correlation']
            result['correlation_p_value'] = corr_result['p_value']
            result['observations'] = corr_result['observations']

            # Step 2: Apply correlation filter
            if not self.correlation_calc.filter_by_correlation(
                corr_result['correlation'], self.correlation_threshold
            ):
                result['error'] = f"Correlation {corr_result['correlation']:.4f} below threshold {self.correlation_threshold}"
                logger.info(result['error'])
                return result

            result['correlation_passed'] = True

            # Step 3: Perform cointegration test
            coint_result = self.coint_test.test_cointegration(series_a, series_b)

            result['is_cointegrated'] = coint_result['is_cointegrated']
            result['hedge_ratio'] = coint_result.get('hedge_ratio')
            result['coint_p_value'] = coint_result.get('adf_p_value') or coint_result.get('coint_p_value')
            result['coint_statistic'] = coint_result.get('adf_statistic') or coint_result.get('coint_t_statistic')
            result['coint_method'] = coint_result['method']

            if coint_result.get('error'):
                result['error'] = coint_result['error']

            logger.info(
                f"Pair analysis: correlation={corr_result['correlation']:.4f}, "
                f"cointegrated={result['is_cointegrated']}, "
                f"hedge_ratio={result['hedge_ratio']:.4f if result['hedge_ratio'] else None}"
            )

        except Exception as e:
            logger.error(f"Error in pair analysis: {e}")
            result['error'] = str(e)

        return result
