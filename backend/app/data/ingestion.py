import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from app.data.providers import get_data_provider, MarketDataProvider
from app.data.preprocessing import DataPreprocessor
from app.models.price import Price
from app.models.instrument import Instrument
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class DataIngestionService:
    """
    Service for ingesting market data from providers into the database.
    Handles fetching, cleaning, and storing price data.
    """

    def __init__(self, db: Session, provider_name: Optional[str] = None):
        """
        Initialize the data ingestion service.

        Args:
            db: Database session
            provider_name: Name of the data provider (defaults to config)
        """
        self.db = db
        provider_name = provider_name or settings.market_data_provider
        self.provider = get_data_provider(provider_name)
        self.preprocessor = DataPreprocessor()

    def ingest_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
        clean: bool = True
    ) -> int:
        """
        Ingest historical data for a single symbol.

        Args:
            symbol: Stock symbol
            start_date: Start date for data
            end_date: End date for data
            interval: Data interval
            clean: Whether to clean the data

        Returns:
            Number of rows ingested
        """
        logger.info(f"Ingesting historical data for {symbol} from {start_date} to {end_date}")

        try:
            # Fetch data from provider
            df = self.provider.get_historical_ohlcv(symbol, start_date, end_date, interval)

            if df.empty:
                logger.warning(f"No data returned for {symbol}")
                return 0

            # Clean data if requested
            if clean:
                df = self.preprocessor.clean_price_data(df)

            # Store in database
            rows_ingested = self._store_price_data(symbol, df)

            logger.info(f"Successfully ingested {rows_ingested} rows for {symbol}")
            return rows_ingested

        except Exception as e:
            logger.error(f"Error ingesting data for {symbol}: {e}")
            raise

    def ingest_multiple_symbols(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
        clean: bool = True
    ) -> dict:
        """
        Ingest historical data for multiple symbols.

        Args:
            symbols: List of stock symbols
            start_date: Start date for data
            end_date: End date for data
            interval: Data interval
            clean: Whether to clean the data

        Returns:
            Dictionary with symbol -> rows_ingested mapping
        """
        logger.info(f"Ingesting historical data for {len(symbols)} symbols")

        results = {}
        for symbol in symbols:
            try:
                rows = self.ingest_historical_data(symbol, start_date, end_date, interval, clean)
                results[symbol] = rows
            except Exception as e:
                logger.error(f"Failed to ingest {symbol}: {e}")
                results[symbol] = 0

        total_rows = sum(results.values())
        logger.info(f"Ingestion complete. Total rows: {total_rows}")

        return results

    def ingest_latest_data(self, symbols: List[str]) -> dict:
        """
        Ingest the latest data for multiple symbols.

        Args:
            symbols: List of stock symbols

        Returns:
            Dictionary with symbol -> success status
        """
        logger.info(f"Ingesting latest data for {len(symbols)} symbols")

        results = {}
        for symbol in symbols:
            try:
                latest = self.provider.get_latest_price(symbol)

                # Create a single-row DataFrame
                df = pd.DataFrame([{
                    'timestamp': latest['timestamp'],
                    'open': latest['price'],
                    'high': latest['price'],
                    'low': latest['price'],
                    'close': latest['price'],
                    'volume': latest.get('volume', 0),
                    'adjusted_close': latest['price']
                }])

                # Clean and store
                df = self.preprocessor.clean_price_data(df)
                rows = self._store_price_data(symbol, df)

                results[symbol] = {'success': True, 'rows': rows}

            except Exception as e:
                logger.error(f"Failed to ingest latest data for {symbol}: {e}")
                results[symbol] = {'success': False, 'error': str(e)}

        return results

    def update_instrument(
        self,
        symbol: str,
        name: str,
        sector: Optional[str] = None,
        exchange: str = "NSE",
        instrument_type: str = "EQUITY"
    ) -> Instrument:
        """
        Update or create an instrument record.

        Args:
            symbol: Stock symbol
            name: Full name
            sector: Sector classification
            exchange: Exchange
            instrument_type: Type of instrument

        Returns:
            Instrument object
        """
        instrument = self.db.query(Instrument).filter(Instrument.id == symbol).first()

        if instrument:
            # Update existing
            instrument.name = name
            instrument.sector = sector
            instrument.exchange = exchange
            instrument.instrument_type = instrument_type
            logger.info(f"Updated instrument: {symbol}")
        else:
            # Create new
            instrument = Instrument(
                id=symbol,
                name=name,
                sector=sector,
                exchange=exchange,
                instrument_type=instrument_type,
                is_active=True
            )
            self.db.add(instrument)
            logger.info(f"Created instrument: {symbol}")

        self.db.commit()
        return instrument

    def _store_price_data(self, symbol: str, df: pd.DataFrame) -> int:
        """
        Store price data in the database.

        Args:
            symbol: Stock symbol
            df: DataFrame with price data

        Returns:
            Number of rows stored
        """
        rows_stored = 0

        for _, row in df.iterrows():
            # Check if record already exists
            existing = self.db.query(Price).filter(
                Price.symbol == symbol,
                Price.timestamp == row['timestamp']
            ).first()

            if existing:
                # Update existing record
                existing.open = row['open']
                existing.high = row['high']
                existing.low = row['low']
                existing.close = row['close']
                existing.volume = row.get('volume', None)
                existing.adjusted_close = row.get('adjusted_close', row['close'])
            else:
                # Create new record
                price = Price(
                    symbol=symbol,
                    timestamp=row['timestamp'],
                    open=row['open'],
                    high=row['high'],
                    low=row['low'],
                    close=row['close'],
                    volume=row.get('volume', None),
                    adjusted_close=row.get('adjusted_close', row['close'])
                )
                self.db.add(price)
                rows_stored += 1

        self.db.commit()
        return rows_stored

    def get_data_availability(self, symbol: str) -> dict:
        """
        Check data availability for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with availability information
        """
        prices = self.db.query(Price).filter(Price.symbol == symbol).order_by(Price.timestamp).all()

        if not prices:
            return {
                'symbol': symbol,
                'available': False,
                'first_date': None,
                'last_date': None,
                'total_rows': 0
            }

        return {
            'symbol': symbol,
            'available': True,
            'first_date': prices[0].timestamp,
            'last_date': prices[-1].timestamp,
            'total_rows': len(prices)
        }

    def backfill_missing_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> int:
        """
        Backfill missing data for a symbol.

        Args:
            symbol: Stock symbol
            start_date: Start date for backfill
            end_date: End date for backfill
            interval: Data interval

        Returns:
            Number of rows backfilled
        """
        # Get existing data range
        availability = self.get_data_availability(symbol)

        if not availability['available']:
            # No data exists, do full ingest
            return self.ingest_historical_data(symbol, start_date, end_date, interval)

        # Find gaps in existing data
        existing_dates = pd.Series([
            p.timestamp for p in self.db.query(Price.timestamp)
            .filter(Price.symbol == symbol)
            .all()
        ])

        # Create expected date range
        expected_dates = pd.date_range(start=start_date, end=end_date, freq='D')
        expected_dates = expected_dates[expected_dates.dayofweek < 5]  # Trading days only

        # Find missing dates
        missing_dates = expected_dates[~expected_dates.isin(existing_dates)]

        if len(missing_dates) == 0:
            logger.info(f"No missing data for {symbol}")
            return 0

        logger.info(f"Found {len(missing_dates)} missing dates for {symbol}")

        # Fetch and ingest missing data
        total_ingested = 0
        for date in missing_dates:
            try:
                # Fetch single day data
                df = self.provider.get_historical_ohlcv(
                    symbol,
                    date,
                    date + timedelta(days=1),
                    interval
                )

                if not df.empty:
                    df = self.preprocessor.clean_price_data(df)
                    rows = self._store_price_data(symbol, df)
                    total_ingested += rows

            except Exception as e:
                logger.error(f"Error backfilling {symbol} for {date}: {e}")

        return total_ingested

    def is_provider_connected(self) -> bool:
        """
        Check if the data provider is connected.

        Returns:
            bool: True if connected
        """
        return self.provider.is_connected()

    def get_provider_info(self) -> dict:
        """
        Get information about the current data provider.

        Returns:
            Dictionary with provider information
        """
        return {
            'name': self.provider.get_provider_name(),
            'connected': self.provider.is_connected(),
            'type': type(self.provider).__name__
        }
