import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from scipy import stats
import logging

logger = logging.getLogger(__name__)


class SpreadCalculator:
    """
    Calculates spread, Z-scores, and half-life of mean reversion for cointegrated pairs.

    Spread Formula:
    S_t = A_t - β * B_t

    Where:
    - A_t: Price of instrument A at time t
    - B_t: Price of instrument B at time t
    - β: Hedge ratio from cointegration analysis
    """

    def __init__(self, min_observations: int = 20):
        """
        Initialize the spread calculator.

        Args:
            min_observations: Minimum observations required for calculations
        """
        self.min_observations = min_observations

    def calculate_spread(
        self,
        series_a: pd.Series,
        series_b: pd.Series,
        hedge_ratio: float
    ) -> pd.Series:
        """
        Calculate the spread between two series using the hedge ratio.

        Args:
            series_a: Price series of instrument A
            series_b: Price series of instrument B
            hedge_ratio: Hedge ratio (β) from cointegration analysis

        Returns:
            Series of spread values
        """
        # Align series
        aligned_a, aligned_b = series_a.align(series_b, join='inner')

        # Calculate spread: S_t = A_t - β * B_t
        spread = aligned_a - hedge_ratio * aligned_b

        logger.info(
            f"Calculated spread: mean={spread.mean():.4f}, "
            f"std={spread.std():.4f}, hedge_ratio={hedge_ratio:.4f}"
        )

        return spread

    def calculate_rolling_statistics(
        self,
        spread: pd.Series,
        window: int = 20
    ) -> pd.DataFrame:
        """
        Calculate rolling statistics for the spread.

        Args:
            spread: Spread series
            window: Rolling window size

        Returns:
            DataFrame with rolling statistics
        """
        if len(spread) < window:
            logger.warning(f"Spread length {len(spread)} < window {window}")
            window = len(spread)

        rolling_stats = pd.DataFrame({
            'spread': spread,
            'rolling_mean': spread.rolling(window=window).mean(),
            'rolling_std': spread.rolling(window=window).std(),
            'rolling_mean_50': spread.rolling(window=50).mean() if len(spread) >= 50 else np.nan,
            'rolling_std_50': spread.rolling(window=50).std() if len(spread) >= 50 else np.nan
        })

        return rolling_stats

    def calculate_z_score(
        self,
        spread: pd.Series,
        rolling_mean: Optional[pd.Series] = None,
        rolling_std: Optional[pd.Series] = None,
        window: int = 20
    ) -> pd.Series:
        """
        Calculate Z-score of the spread.

        Z-score Formula:
        Z_t = (S_t - μ_t) / σ_t

        Where:
        - S_t: Current spread
        - μ_t: Rolling mean of spread
        - σ_t: Rolling standard deviation of spread

        Args:
            spread: Spread series
            rolling_mean: Pre-calculated rolling mean (optional)
            rolling_std: Pre-calculated rolling std (optional)
            window: Window size if rolling stats not provided

        Returns:
            Series of Z-scores
        """
        if rolling_mean is None:
            rolling_mean = spread.rolling(window=window).mean()

        if rolling_std is None:
            rolling_std = spread.rolling(window=window).std()

        # Avoid division by zero
        rolling_std = rolling_std.replace(0, np.nan)

        # Calculate Z-score
        z_score = (spread - rolling_mean) / rolling_std

        # Handle NaN/Infinity
        z_score = z_score.replace([np.inf, -np.inf], np.nan)

        logger.info(
            f"Calculated Z-score: mean={z_score.mean():.4f}, "
            f"std={z_score.std():.4f}, current={z_score.iloc[-1] if len(z_score) > 0 else np.nan:.4f}"
        )

        return z_score

    def calculate_half_life(
        self,
        spread: pd.Series,
        method: str = "ornstein_uhlenbeck"
    ) -> Dict:
        """
        Calculate the half-life of mean reversion.

        Method 1: Ornstein-Uhlenbeck Process
        The spread follows: dS_t = -λ(S_t - μ)dt + σdW_t
        Half-life = ln(2) / λ

        Method 2: Regression on lagged spread
        S_t - S_{t-1} = λ(μ - S_{t-1}) + ε_t
        Half-life = ln(2) / λ

        Args:
            spread: Spread series
            method: Method to use ('ornstein_uhlenbeck' or 'regression')

        Returns:
            Dictionary with half-life results
        """
        if len(spread) < self.min_observations:
            logger.warning(f"Insufficient data for half-life calculation: {len(spread)} < {self.min_observations}")
            return {
                'half_life': np.nan,
                'lambda': np.nan,
                'method': method,
                'error': 'Insufficient data'
            }

        # Remove NaN values
        spread_clean = spread.dropna()

        if len(spread_clean) < self.min_observations:
            return {
                'half_life': np.nan,
                'lambda': np.nan,
                'method': method,
                'error': 'Insufficient clean data'
            }

        try:
            if method == "ornstein_uhlenbeck":
                return self._half_life_ou(spread_clean)
            elif method == "regression":
                return self._half_life_regression(spread_clean)
            else:
                raise ValueError(f"Unknown method: {method}")

        except Exception as e:
            logger.error(f"Error calculating half-life: {e}")
            return {
                'half_life': np.nan,
                'lambda': np.nan,
                'method': method,
                'error': str(e)
            }

    def _half_life_ou(self, spread: pd.Series) -> Dict:
        """
        Calculate half-life using Ornstein-Uhlenbeck process estimation.

        ΔS_t = -λ(S_{t-1} - μ) + ε_t
        """
        # Calculate lagged spread
        spread_lag = spread.shift(1).dropna()
        spread_change = spread.diff().dropna()

        # Align
        aligned_spread = spread_lag.align(spread_change, join='inner')

        if len(aligned_spread[0]) < self.min_observations:
            return {
                'half_life': np.nan,
                'lambda': np.nan,
                'method': 'ornstein_uhlenbeck',
                'error': 'Insufficient aligned data'
            }

        X = aligned_spread[0].values.reshape(-1, 1)
        y = aligned_spread[1].values

        # Add constant for mean reversion level
        X_with_const = np.column_stack([np.ones(len(X)), X])

        # Regression: ΔS = α + β*S_{t-1} + ε
        # λ = -β
        from sklearn.linear_model import LinearRegression
        model = LinearRegression()
        model.fit(X_with_const, y)

        beta = model.coef_[1]  # Coefficient on lagged spread
        lambda_param = -beta

        # Calculate half-life
        if lambda_param > 0:
            half_life = np.log(2) / lambda_param
        else:
            # Negative lambda means no mean reversion
            half_life = np.inf
            lambda_param = 0

        logger.info(
            f"OU half-life: {half_life:.2f} periods, lambda={lambda_param:.4f}"
        )

        return {
            'half_life': half_life,
            'lambda': lambda_param,
            'method': 'ornstein_uhlenbeck',
            'intercept': model.intercept_,
            'observations': len(X)
        }

    def _half_life_regression(self, spread: pd.Series) -> Dict:
        """
        Calculate half-life using simple regression on lagged spread.

        S_t - S_{t-1} = λ(μ - S_{t-1}) + ε_t
        """
        spread_lag = spread.shift(1).dropna()
        spread_change = spread.diff().dropna()

        # Align
        aligned_spread = spread_lag.align(spread_change, join='inner')

        if len(aligned_spread[0]) < self.min_observations:
            return {
                'half_life': np.nan,
                'lambda': np.nan,
                'method': 'regression',
                'error': 'Insufficient aligned data'
            }

        X = aligned_spread[0].values.reshape(-1, 1)
        y = aligned_spread[1].values

        # Regression: ΔS = -λ*S_{t-1} + ε
        from sklearn.linear_model import LinearRegression
        model = LinearRegression(fit_intercept=False)
        model.fit(X, y)

        lambda_param = -model.coef_[0]

        # Calculate half-life
        if lambda_param > 0:
            half_life = np.log(2) / lambda_param
        else:
            half_life = np.inf
            lambda_param = 0

        logger.info(
            f"Regression half-life: {half_life:.2f} periods, lambda={lambda_param:.4f}"
        )

        return {
            'half_life': half_life,
            'lambda': lambda_param,
            'method': 'regression',
            'observations': len(X)
        }

    def calculate_all_metrics(
        self,
        series_a: pd.Series,
        series_b: pd.Series,
        hedge_ratio: float,
        window: int = 20
    ) -> Dict:
        """
        Calculate all spread-related metrics.

        Args:
            series_a: Price series of instrument A
            series_b: Price series of instrument B
            hedge_ratio: Hedge ratio from cointegration
            window: Rolling window size

        Returns:
            Dictionary with all metrics
        """
        # Calculate spread
        spread = self.calculate_spread(series_a, series_b, hedge_ratio)

        # Calculate rolling statistics
        rolling_stats = self.calculate_rolling_statistics(spread, window)

        # Calculate Z-score
        z_score = self.calculate_z_score(
            spread,
            rolling_stats['rolling_mean'],
            rolling_stats['rolling_std'],
            window
        )

        # Calculate half-life
        half_life_result = self.calculate_half_life(spread)

        return {
            'spread': spread,
            'rolling_mean': rolling_stats['rolling_mean'],
            'rolling_std': rolling_stats['rolling_std'],
            'z_score': z_score,
            'current_spread': spread.iloc[-1] if len(spread) > 0 else np.nan,
            'current_z_score': z_score.iloc[-1] if len(z_score) > 0 else np.nan,
            'current_mean': rolling_stats['rolling_mean'].iloc[-1] if len(rolling_stats['rolling_mean']) > 0 else np.nan,
            'current_std': rolling_stats['rolling_std'].iloc[-1] if len(rolling_stats['rolling_std']) > 0 else np.nan,
            'half_life': half_life_result['half_life'],
            'lambda': half_life_result.get('lambda'),
            'half_life_method': half_life_result['method'],
            'hedge_ratio': hedge_ratio,
            'observations': len(spread)
        }

    def validate_spread_quality(self, spread: pd.Series) -> Dict:
        """
        Validate the quality of spread calculations.

        Args:
            spread: Spread series

        Returns:
            Dictionary with validation results
        """
        result = {
            'is_valid': True,
            'warnings': [],
            'errors': []
        }

        # Check for NaN values
        nan_count = spread.isna().sum()
        if nan_count > 0:
            result['warnings'].append(f"{nan_count} NaN values in spread")

        # Check for infinite values
        inf_count = np.isinf(spread).sum()
        if inf_count > 0:
            result['errors'].append(f"{inf_count} infinite values in spread")
            result['is_valid'] = False

        # Check for zero variance
        if spread.std() == 0:
            result['errors'].append("Zero variance in spread")
            result['is_valid'] = False

        # Check for sufficient observations
        if len(spread) < self.min_observations:
            result['errors'].append(f"Insufficient observations: {len(spread)} < {self.min_observations}")
            result['is_valid'] = False

        # Check for extreme values
        if len(spread) > 0:
            z_scores = np.abs((spread - spread.mean()) / (spread.std() + 1e-10))
            extreme_count = (z_scores > 5).sum()
            if extreme_count > 0:
                result['warnings'].append(f"{extreme_count} extreme values (|Z| > 5) in spread")

        return result
