from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import pandas as pd


class MarketDataProvider(ABC):
    """
    Abstract base class for market data providers.
    All providers must implement these methods to ensure consistent interface.
    """

    @abstractmethod
    def get_historical_ohlcv(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Get historical OHLCV data for a symbol.

        Args:
            symbol: Stock symbol (e.g., "HDFCBANK.NS")
            start_date: Start date for data
            end_date: End date for data
            interval: Data interval (1d, 1h, etc.)

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume, adjusted_close
        """
        pass

    @abstractmethod
    def get_latest_price(self, symbol: str) -> Dict[str, Any]:
        """
        Get the latest price for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Dict with: symbol, price, timestamp, volume
        """
        pass

    @abstractmethod
    def get_multiple_symbols(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> Dict[str, pd.DataFrame]:
        """
        Get historical data for multiple symbols.

        Args:
            symbols: List of stock symbols
            start_date: Start date for data
            end_date: End date for data
            interval: Data interval

        Returns:
            Dict mapping symbol to DataFrame
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if the provider is connected and operational.

        Returns:
            bool: True if connected, False otherwise
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the name of the provider.

        Returns:
            str: Provider name
        """
        pass


class DemoDataProvider(MarketDataProvider):
    """
    Demo data provider for development and testing.
    Uses deterministic data generation rather than random values.
    """

    def __init__(self):
        self._connected = True

    def get_historical_ohlcv(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Generate deterministic demo OHLCV data.
        This is for development only - will be replaced with real data.
        """
        # Generate date range
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        # Filter to trading days (exclude weekends)
        dates = dates[dates.dayofweek < 5]

        # Generate deterministic price data based on symbol
        # Use hash of symbol to generate consistent "random" values
        symbol_hash = hash(symbol) % 10000
        base_price = 1000 + (symbol_hash % 2000)

        data = []
        for i, date in enumerate(dates):
            # Deterministic price movement using sine waves
            price_change = (i * 0.01) + (symbol_hash * 0.001) + (i % 7) * 0.5
            open_price = base_price + price_change
            close_price = open_price + (i % 3 - 1) * 10
            high_price = max(open_price, close_price) + abs((i % 5) * 5)
            low_price = min(open_price, close_price) - abs((i % 4) * 3)
            volume = 1000000 + (symbol_hash % 500000) + (i * 1000)

            data.append({
                'timestamp': date,
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': volume,
                'adjusted_close': round(close_price, 2)
            })

        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df

    def get_latest_price(self, symbol: str) -> Dict[str, Any]:
        """
        Get latest demo price.
        """
        symbol_hash = hash(symbol) % 10000
        base_price = 1000 + (symbol_hash % 2000)
        price = base_price + (symbol_hash * 0.01)

        return {
            'symbol': symbol,
            'price': round(price, 2),
            'timestamp': datetime.now(),
            'volume': 1000000 + (symbol_hash % 500000)
        }

    def get_multiple_symbols(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> Dict[str, pd.DataFrame]:
        """
        Get demo data for multiple symbols.
        """
        result = {}
        for symbol in symbols:
            result[symbol] = self.get_historical_ohlcv(symbol, start_date, end_date, interval)
        return result

    def is_connected(self) -> bool:
        return self._connected

    def get_provider_name(self) -> str:
        return "DemoDataProvider"


class YahooFinanceProvider(MarketDataProvider):
    """
    Yahoo Finance data provider using yfinance.
    Requires yfinance to be installed.
    """

    def __init__(self):
        try:
            import yfinance as yf
            self.yf = yf
            self._connected = True
        except ImportError:
            self._connected = False
            self.yf = None

    def get_historical_ohlcv(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Get historical data from Yahoo Finance.
        """
        if not self._connected:
            raise ConnectionError("Yahoo Finance provider not available. Install yfinance.")

        # Convert to Yahoo Finance symbol format if needed
        yf_symbol = self._convert_symbol(symbol)

        # Download data
        data = self.yf.download(
            yf_symbol,
            start=start_date,
            end=end_date,
            interval=interval,
            progress=False
        )

        if data.empty:
            return pd.DataFrame()

        # Normalize column names
        data.columns = [col.lower() for col in data.columns]
        data.reset_index(inplace=True)
        data.rename(columns={'date': 'timestamp'}, inplace=True)

        # Ensure required columns exist
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in data.columns:
                data[col] = None

        # Add adjusted_close if not present
        if 'adj close' in data.columns:
            data['adjusted_close'] = data['adj close']
        else:
            data['adjusted_close'] = data['close']

        return data[required_cols + ['adjusted_close']]

    def get_latest_price(self, symbol: str) -> Dict[str, Any]:
        """
        Get latest price from Yahoo Finance.
        """
        if not self._connected:
            raise ConnectionError("Yahoo Finance provider not available. Install yfinance.")

        yf_symbol = self._convert_symbol(symbol)
        ticker = self.yf.Ticker(yf_symbol)
        info = ticker.info

        return {
            'symbol': symbol,
            'price': info.get('currentPrice', info.get('regularMarketPrice', None)),
            'timestamp': datetime.now(),
            'volume': info.get('volume', None)
        }

    def get_multiple_symbols(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> Dict[str, pd.DataFrame]:
        """
        Get data for multiple symbols from Yahoo Finance.
        """
        if not self._connected:
            raise ConnectionError("Yahoo Finance provider not available. Install yfinance.")

        result = {}
        for symbol in symbols:
            try:
                result[symbol] = self.get_historical_ohlcv(symbol, start_date, end_date, interval)
            except Exception as e:
                print(f"Error fetching data for {symbol}: {e}")
                result[symbol] = pd.DataFrame()

        return result

    def is_connected(self) -> bool:
        return self._connected

    def get_provider_name(self) -> str:
        return "YahooFinance"

    def _convert_symbol(self, symbol: str) -> str:
        """
        Convert symbol to Yahoo Finance format.
        NSE stocks need .NS suffix.
        """
        if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
            # Assume NSE by default
            return f"{symbol}.NS"
        return symbol


def get_data_provider(provider_name: str) -> MarketDataProvider:
    """
    Factory function to get the appropriate data provider.

    Args:
        provider_name: Name of the provider (demo, yahoo_finance, etc.)

    Returns:
        MarketDataProvider instance
    """
    providers = {
        'demo': DemoDataProvider,
        'yahoo_finance': YahooFinanceProvider,
    }

    provider_class = providers.get(provider_name.lower())
    if not provider_class:
        raise ValueError(f"Unknown provider: {provider_name}")

    return provider_class()
