import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class DataPreprocessor:
    """
    Handles data preprocessing, cleaning, and validation for market data.
    Ensures data quality before quantitative analysis.
    """

    @staticmethod
    def normalize_timestamps(df: pd.DataFrame, timezone: str = 'Asia/Kolkata') -> pd.DataFrame:
        """
        Normalize timestamps to a consistent timezone and format.

        Args:
            df: DataFrame with timestamp column
            timezone: Target timezone

        Returns:
            DataFrame with normalized timestamps
        """
        if 'timestamp' not in df.columns:
            raise ValueError("DataFrame must have 'timestamp' column")

        df = df.copy()

        # Convert to datetime if not already
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Localize if naive, then convert to target timezone
        if df['timestamp'].dt.tz is None:
            df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')
        df['timestamp'] = df['timestamp'].dt.tz_convert(timezone)

        # Remove timezone info for storage (keep as naive datetime in target timezone)
        df['timestamp'] = df['timestamp'].dt.tz_localize(None)

        return df

    @staticmethod
    def align_trading_days(df_a: pd.DataFrame, df_b: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Align two time series to the same trading days.
        Ensures both series have the same observation dates for pair analysis.

        Args:
            df_a: First time series
            df_b: Second time series

        Returns:
            Tuple of aligned DataFrames
        """
        # Get common timestamps
        common_dates = pd.Index(df_a['timestamp']).intersection(pd.Index(df_b['timestamp']))

        if len(common_dates) == 0:
            logger.warning("No common trading days found between the two series")
            return pd.DataFrame(), pd.DataFrame()

        # Filter to common dates
        df_a_aligned = df_a[df_a['timestamp'].isin(common_dates)].copy()
        df_b_aligned = df_b[df_b['timestamp'].isin(common_dates)].copy()

        # Sort by timestamp
        df_a_aligned = df_a_aligned.sort_values('timestamp').reset_index(drop=True)
        df_b_aligned = df_b_aligned.sort_values('timestamp').reset_index(drop=True)

        logger.info(f"Aligned {len(common_dates)} trading days between series")

        return df_a_aligned, df_b_aligned

    @staticmethod
    def handle_missing_values(df: pd.DataFrame, method: str = 'forward_fill') -> pd.DataFrame:
        """
        Handle missing values in price data.

        Args:
            df: DataFrame with price data
            method: Method to handle missing values ('forward_fill', 'backward_fill', 'drop', 'interpolate')

        Returns:
            DataFrame with missing values handled
        """
        df = df.copy()

        # Check for missing values
        missing_count = df.isnull().sum().sum()
        if missing_count > 0:
            logger.info(f"Found {missing_count} missing values, handling with method: {method}")

        if method == 'forward_fill':
            df = df.fillna(method='ffill')
        elif method == 'backward_fill':
            df = df.fillna(method='bfill')
        elif method == 'drop':
            df = df.dropna()
        elif method == 'interpolate':
            df = df.interpolate(method='time')
        else:
            raise ValueError(f"Unknown missing value method: {method}")

        return df

    @staticmethod
    def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove duplicate rows based on timestamp.

        Args:
            df: DataFrame with timestamp column

        Returns:
            DataFrame with duplicates removed
        """
        if 'timestamp' not in df.columns:
            raise ValueError("DataFrame must have 'timestamp' column")

        initial_count = len(df)
        df = df.drop_duplicates(subset=['timestamp'], keep='last')
        removed_count = initial_count - len(df)

        if removed_count > 0:
            logger.info(f"Removed {removed_count} duplicate rows")

        return df.sort_values('timestamp').reset_index(drop=True)

    @staticmethod
    def validate_ohlcv(df: pd.DataFrame) -> Tuple[bool, list]:
        """
        Validate OHLCV data for consistency and correctness.

        Args:
            df: DataFrame with OHLCV columns

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in df.columns:
                errors.append(f"Missing required column: {col}")

        if errors:
            return False, errors

        # Check for negative prices
        price_cols = ['open', 'high', 'low', 'close']
        for col in price_cols:
            if (df[col] < 0).any():
                errors.append(f"Negative values found in {col}")

        # Check high >= low
        if (df['high'] < df['low']).any():
            errors.append("High price is less than low price in some rows")

        # Check close within high-low range
        if ((df['close'] > df['high']) | (df['close'] < df['low'])).any():
            errors.append("Close price outside high-low range in some rows")

        # Check for zero prices
        for col in price_cols:
            if (df[col] == 0).any():
                errors.append(f"Zero values found in {col}")

        # Check for missing timestamps
        if df['timestamp'].isnull().any():
            errors.append("Missing timestamps found")

        return len(errors) == 0, errors

    @staticmethod
    def detect_outliers(df: pd.DataFrame, column: str = 'close', method: str = 'iqr', threshold: float = 3.0) -> pd.DataFrame:
        """
        Detect outliers in price data.

        Args:
            df: DataFrame with price data
            column: Column to check for outliers
            method: Method to detect outliers ('iqr', 'zscore')
            threshold: Threshold for outlier detection

        Returns:
            DataFrame with outlier flags
        """
        df = df.copy()

        if column not in df.columns:
            raise ValueError(f"Column {column} not found in DataFrame")

        if method == 'iqr':
            Q1 = df[column].quantile(0.25)
            Q3 = df[column].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - threshold * IQR
            upper_bound = Q3 + threshold * IQR
            df['is_outlier'] = (df[column] < lower_bound) | (df[column] > upper_bound)

        elif method == 'zscore':
            mean = df[column].mean()
            std = df[column].std()
            df['zscore'] = (df[column] - mean) / std
            df['is_outlier'] = np.abs(df['zscore']) > threshold

        else:
            raise ValueError(f"Unknown outlier detection method: {method}")

        outlier_count = df['is_outlier'].sum()
        if outlier_count > 0:
            logger.info(f"Detected {outlier_count} outliers in {column} using {method} method")

        return df

    @staticmethod
    def apply_corporate_actions(df: pd.DataFrame, splits: dict = None, dividends: dict = None) -> pd.DataFrame:
        """
        Apply corporate action adjustments to price data.

        Args:
            df: DataFrame with price data
            splits: Dictionary of stock splits {date: ratio}
            dividends: Dictionary of dividends {date: amount}

        Returns:
            DataFrame with adjusted prices
        """
        df = df.copy()

        # Apply stock splits
        if splits:
            for split_date, split_ratio in splits.items():
                split_date = pd.to_datetime(split_date)
                mask = df['timestamp'] >= split_date
                df.loc[mask, ['open', 'high', 'low', 'close']] = df.loc[mask, ['open', 'high', 'low', 'close']] / split_ratio
                logger.info(f"Applied {split_ratio}:1 stock split on {split_date}")

        # Apply dividends (simplified - would need more sophisticated handling in production)
        if dividends:
            for div_date, div_amount in dividends.items():
                div_date = pd.to_datetime(div_date)
                mask = df['timestamp'] >= div_date
                # Simplified adjustment - in production, use total return calculations
                df.loc[mask, 'adjusted_close'] = df.loc[mask, 'close'] - div_amount
                logger.info(f"Applied dividend adjustment on {div_date}")

        return df

    @staticmethod
    def resample_data(df: pd.DataFrame, interval: str = '1D') -> pd.DataFrame:
        """
        Resample data to a different interval.

        Args:
            df: DataFrame with timestamp index
            interval: Target interval (1D, 1H, 1W, etc.)

        Returns:
            Resampled DataFrame
        """
        if 'timestamp' not in df.columns:
            raise ValueError("DataFrame must have 'timestamp' column")

        df = df.copy()
        df = df.set_index('timestamp')

        # Define aggregation functions
        agg_dict = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }

        if 'adjusted_close' in df.columns:
            agg_dict['adjusted_close'] = 'last'

        resampled = df.resample(interval).agg(agg_dict)

        # Remove rows with NaN (periods with no data)
        resampled = resampled.dropna()

        return resampled.reset_index()

    @staticmethod
    def clean_price_data(df: pd.DataFrame) -> pd.DataFrame:
        """
        Complete cleaning pipeline for price data.

        Args:
            df: Raw price data

        Returns:
            Cleaned price data
        """
        logger.info("Starting price data cleaning pipeline")

        # Step 1: Normalize timestamps
        df = DataPreprocessor.normalize_timestamps(df)

        # Step 2: Remove duplicates
        df = DataPreprocessor.remove_duplicates(df)

        # Step 3: Validate OHLCV
        is_valid, errors = DataPreprocessor.validate_ohlcv(df)
        if not is_valid:
            logger.warning(f"OHLCV validation failed: {errors}")
            # Continue with cleaning but log errors

        # Step 4: Handle missing values
        df = DataPreprocessor.handle_missing_values(df, method='forward_fill')

        # Step 5: Sort by timestamp
        df = df.sort_values('timestamp').reset_index(drop=True)

        logger.info(f"Cleaning complete. {len(df)} rows remaining")

        return df
