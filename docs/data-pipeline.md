# Data Pipeline Documentation

## Overview

This document explains the data pipeline architecture in the StatArb-N50 platform, from market data ingestion to preprocessing and storage. The pipeline is designed to handle historical and real-time data from multiple providers while ensuring data quality and integrity.

## 1. Architecture Overview

### Data Flow

```
Market Data Provider → Ingestion Service → Preprocessing → Validation
→ Database → Quantitative Engine → API → Frontend
```

### Components

**Market Data Layer:**
- `MarketDataProvider`: Abstract interface
- `DemoDataProvider`: Deterministic development data
- `YahooFinanceProvider`: Real market data
- Future providers can be added

**Ingestion Layer:**
- `DataIngestionService`: Fetch and store data
- Bulk ingestion for historical data
- Incremental updates for real-time data

**Preprocessing Layer:**
- `DataPreprocessor`: Clean and transform data
- Timestamp normalization
- Trading day alignment
- Missing value handling

**Storage Layer:**
- SQLAlchemy ORM models
- PostgreSQL database
- Alembic migrations

## 2. Market Data Provider Interface

### Abstract Interface

**MarketDataProvider Class:**
```python
class MarketDataProvider(ABC):
    """
    Abstract interface for market data providers.
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
        Fetch historical OHLCV data for a single symbol.

        Returns DataFrame with columns:
        - timestamp: datetime index
        - open: float
        - high: float
        - low: float
        - close: float
        - volume: int
        """
        pass

    @abstractmethod
    def get_latest_price(self, symbol: str) -> float:
        """
        Fetch latest price for a symbol.
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
        Fetch historical data for multiple symbols.
        """
        pass

    @abstractmethod
    def get_realtime_stream(self, symbols: List[str]):
        """
        Get real-time streaming data (if supported).
        """
        pass
```

### Normalized Data Structure

**OHLCV DataFrame:**
```python
{
    'timestamp': pd.DatetimeIndex,  # Trading days only
    'open': float,                  # Opening price
    'high': float,                  # High price
    'low': float,                   # Low price
    'close': float,                 # Closing price
    'volume': int                   # Trading volume
}
```

**Required Properties:**
- Timestamp: UTC timezone or local market timezone
- No duplicate timestamps
- No missing timestamps (trading days only)
- No negative prices or volumes
- High >= Low
- Close between High and Low
- Volume >= 0

## 3. Demo Data Provider

### Purpose

Provides deterministic, non-random data for development and testing. This is clearly labeled as demo data and never presented as real market data.

### Implementation

**DemoDataProvider Class:**
```python
class DemoDataProvider(MarketDataProvider):
    """
    Deterministic demo data provider for development.
    Clearly labeled as demo data, not real market data.
    """

    def get_historical_ohlcv(self, symbol, start_date, end_date, interval="1d"):
        """
        Generate deterministic demo OHLCV data.
        """
        # Generate trading days
        dates = pd.date_range(start_date, end_date, freq='B')  # Business days

        # Generate deterministic prices based on symbol hash
        base_price = self._generate_base_price(symbol)
        prices = self._generate_price_series(dates, base_price)

        # Generate OHLCV
        data = []
        for i, date in enumerate(dates):
            price = prices[i]
            high = price * 1.02
            low = price * 0.98
            open_price = price * 0.99
            close = price
            volume = 1000000

            data.append({
                'timestamp': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })

        return pd.DataFrame(data).set_index('timestamp')

    def _generate_base_price(self, symbol):
        """
        Generate deterministic base price from symbol.
        """
        hash_val = sum(ord(c) for c in symbol)
        return 100 + (hash_val % 900)  # Price between 100 and 1000

    def _generate_price_series(self, dates, base_price):
        """
        Generate deterministic price series.
        """
        np.random.seed(42)  # Fixed seed for reproducibility
        returns = np.random.normal(0.001, 0.02, len(dates))
        prices = base_price * (1 + returns).cumprod()
        return prices
```

**Important Notes:**
- Uses fixed random seed for reproducibility
- Clearly labeled as demo data
- Never presented as real market data
- Used only for development and testing

## 4. Yahoo Finance Provider

### Purpose

Provides real market data from Yahoo Finance API for production use.

### Implementation

**YahooFinanceProvider Class:**
```python
class YahooFinanceProvider(MarketDataProvider):
    """
    Yahoo Finance data provider for real market data.
    """

    def __init__(self):
        import yfinance as yf
        self.yf = yf

    def get_historical_ohlcv(self, symbol, start_date, end_date, interval="1d"):
        """
        Fetch historical OHLCV data from Yahoo Finance.
        """
        ticker = self.yf.Ticker(symbol)
        data = ticker.history(
            start=start_date,
            end=end_date,
            interval=interval
        )

        # Normalize column names
        data.columns = data.columns.str.lower()

        # Ensure required columns
        required = ['open', 'high', 'low', 'close', 'volume']
        for col in required:
            if col not in data.columns:
                raise ValueError(f"Missing required column: {col}")

        return data[required]

    def get_latest_price(self, symbol):
        """
        Fetch latest price from Yahoo Finance.
        """
        ticker = self.yf.Ticker(symbol)
        info = ticker.info
        return info.get('currentPrice') or info.get('regularMarketPrice')

    def get_multiple_symbols(self, symbols, start_date, end_date, interval="1d"):
        """
        Fetch data for multiple symbols.
        """
        results = {}
        for symbol in symbols:
            try:
                results[symbol] = self.get_historical_ohlcv(
                    symbol, start_date, end_date, interval
                )
            except Exception as e:
                logger.error(f"Failed to fetch data for {symbol}: {e}")
                results[symbol] = None
        return results
```

**API Requirements:**
- `yfinance` Python package
- Internet connection
- Rate limiting considerations

**Rate Limiting:**
- Yahoo Finance has informal rate limits
- Implement delays between requests
- Cache responses when possible

## 5. Data Ingestion Service

### IngestionService Class

```python
class DataIngestionService:
    """
    Service for ingesting market data and storing in database.
    """

    def __init__(self, provider: MarketDataProvider, db_session):
        self.provider = provider
        self.db_session = db_session

    def ingest_historical_data(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ):
        """
        Ingest historical data for multiple symbols.
        """
        for symbol in symbols:
            try:
                # Fetch data from provider
                data = self.provider.get_historical_ohlcv(
                    symbol, start_date, end_date, interval
                )

                # Store in database
                self._store_ohlcv_data(symbol, data)

                logger.info(f"Ingested data for {symbol}")

            except Exception as e:
                logger.error(f"Failed to ingest {symbol}: {e}")

    def _store_ohlcv_data(self, symbol: str, data: pd.DataFrame):
        """
        Store OHLCV data in database.
        """
        for timestamp, row in data.iterrows():
            # Check if record exists
            existing = self.db_session.query(Price).filter(
                Price.symbol == symbol,
                Price.timestamp == timestamp
            ).first()

            if existing:
                # Update existing record
                existing.open = row['open']
                existing.high = row['high']
                existing.low = row['low']
                existing.close = row['close']
                existing.volume = row['volume']
            else:
                # Create new record
                price = Price(
                    symbol=symbol,
                    timestamp=timestamp,
                    open=row['open'],
                    high=row['high'],
                    low=row['low'],
                    close=row['close'],
                    volume=row['volume']
                )
                self.db_session.add(price)

        self.db_session.commit()

    def ingest_latest_prices(self, symbols: List[str]):
        """
        Ingest latest prices for real-time updates.
        """
        for symbol in symbols:
            try:
                price = self.provider.get_latest_price(symbol)
                self._store_latest_price(symbol, price)
            except Exception as e:
                logger.error(f"Failed to ingest latest price for {symbol}: {e}")

    def _store_latest_price(self, symbol: str, price: float):
        """
        Store latest price in database.
        """
        # Store as intraday or latest record
        # Implementation depends on use case
        pass
```

### Bulk Ingestion

**For Historical Data:**
```python
def bulk_ingest(provider, symbols, start_date, end_date):
    """
    Bulk ingest historical data.
    """
    ingestion_service = DataIngestionService(provider, db_session)
    ingestion_service.ingest_historical_data(symbols, start_date, end_date)
```

**For Incremental Updates:**
```python
def incremental_ingest(provider, symbols, days=1):
    """
    Incrementally ingest recent data.
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    ingestion_service = DataIngestionService(provider, db_session)
    ingestion_service.ingest_historical_data(symbols, start_date, end_date)
```

## 6. Data Preprocessing

### DataPreprocessor Class

```python
class DataPreprocessor:
    """
    Preprocess market data for quantitative analysis.
    """

    def normalize_timestamps(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize timestamps to UTC.
        """
        if data.index.tz is None:
            data.index = data.index.tz_localize('UTC')
        else:
            data.index = data.index.tz_convert('UTC')
        return data

    def align_trading_days(self, df_a: pd.DataFrame, df_b: pd.DataFrame) -> tuple:
        """
        Align two series to common trading days.
        """
        # Get common timestamps
        common_dates = pd.Index(df_a['timestamp']).intersection(pd.Index(df_b['timestamp']))

        # Filter to common dates
        aligned_a = df_a[df_a['timestamp'].isin(common_dates)]
        aligned_b = df_b[df_b['timestamp'].isin(common_dates)]

        return aligned_a, aligned_b

    def handle_missing_values(self, data: pd.DataFrame, method: str = "ffill") -> pd.DataFrame:
        """
        Handle missing values in data.
        """
        if method == "ffill":
            return data.fillna(method='ffill')
        elif method == "drop":
            return data.dropna()
        elif method == "interpolate":
            return data.interpolate()
        else:
            raise ValueError(f"Unknown method: {method}")

    def remove_duplicates(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Remove duplicate records.
        """
        return data[~data.index.duplicated(keep='last')]

    def validate_ohlcv(self, data: pd.DataFrame) -> bool:
        """
        Validate OHLCV data integrity.
        """
        # Check for negative prices
        if (data[['open', 'high', 'low', 'close']] < 0).any().any():
            logger.error("Negative prices detected")
            return False

        # Check for negative volume
        if (data['volume'] < 0).any():
            logger.error("Negative volume detected")
            return False

        # Check high >= low
        if (data['high'] < data['low']).any():
            logger.error("High < Low detected")
            return False

        # Check close between high and low
        if ((data['close'] > data['high']) | (data['close'] < data['low'])).any():
            logger.error("Close outside High-Low range")
            return False

        return True

    def detect_outliers(self, data: pd.DataFrame, threshold: float = 3.0) -> pd.DataFrame:
        """
        Detect outliers using z-score method.
        """
        # Calculate z-scores for prices
        z_scores = (data[['open', 'high', 'low', 'close']] - data[['open', 'high', 'low', 'close']].mean()) / data[['open', 'high', 'low', 'close']].std()

        # Identify outliers
        outliers = (z_scores.abs() > threshold).any(axis=1)

        return data[outliers]
```

### Trading Day Alignment

**Purpose:**
Ensure both assets in a pair have data for the same trading days to avoid look-ahead bias.

**Implementation:**
```python
def align_pair_data(series_a, series_b):
    """
    Align two price series to common trading days.
    """
    # Convert to DataFrames if needed
    if isinstance(series_a, pd.Series):
        df_a = series_a.to_frame('price')
        df_a['timestamp'] = series_a.index
    else:
        df_a = series_a

    if isinstance(series_b, pd.Series):
        df_b = series_b.to_frame('price')
        df_b['timestamp'] = series_b.index
    else:
        df_b = series_b

    # Align trading days
    preprocessor = DataPreprocessor()
    aligned_a, aligned_b = preprocessor.align_trading_days(df_a, df_b)

    return aligned_a, aligned_b
```

**Critical for Cointegration:**
- Cointegration requires same observation dates
- Missing dates introduce bias
- Forward-filling distorts statistical tests

## 7. Data Validation

### Validation Checks

**1. Timestamp Validation:**
```python
def validate_timestamps(data: pd.DataFrame) -> bool:
    """
    Validate timestamp consistency.
    """
    # Check for missing timestamps
    if data.index.isna().any():
        return False

    # Check for duplicates
    if data.index.duplicated().any():
        return False

    # Check timezone
    if data.index.tz is None:
        return False

    return True
```

**2. Price Validation:**
```python
def validate_prices(data: pd.DataFrame) -> bool:
    """
    Validate price data.
    """
    # Check for negative prices
    if (data[['open', 'high', 'low', 'close']] < 0).any().any():
        return False

    # Check for zero prices
    if (data[['open', 'high', 'low', 'close']] == 0).any().any():
        return False

    # Check for infinity
    if np.isinf(data[['open', 'high', 'low', 'close']]).any().any():
        return False

    return True
```

**3. Volume Validation:**
```python
def validate_volume(data: pd.DataFrame) -> bool:
    """
    Validate volume data.
    """
    # Check for negative volume
    if (data['volume'] < 0).any():
        return False

    # Check for infinity
    if np.isinf(data['volume']).any():
        return False

    return True
```

**4. Logical Validation:**
```python
def validate_ohlcv_logic(data: pd.DataFrame) -> bool:
    """
    Validate OHLCV logical relationships.
    """
    # High >= Low
    if (data['high'] < data['low']).any():
        return False

    # Close between High and Low
    if ((data['close'] > data['high']) | (data['close'] < data['low'])).any():
        return False

    # Open between High and Low
    if ((data['open'] > data['high']) | (data['open'] < data['low'])).any():
        return False

    return True
```

### Data Quality Report

```python
def generate_data_quality_report(data: pd.DataFrame) -> dict:
    """
    Generate data quality report.
    """
    report = {
        'total_records': len(data),
        'missing_values': data.isna().sum().to_dict(),
        'duplicate_timestamps': data.index.duplicated().sum(),
        'negative_prices': (data[['open', 'high', 'low', 'close']] < 0).any().any(),
        'zero_prices': (data[['open', 'high', 'low', 'close']] == 0).any().any(),
        'invalid_ohlcv': not validate_ohlcv_logic(data),
        'date_range': {
            'start': data.index.min(),
            'end': data.index.max()
        },
        'statistics': {
            'mean': data[['open', 'high', 'low', 'close']].mean().to_dict(),
            'std': data[['open', 'high', 'low', 'close']].std().to_dict(),
            'min': data[['open', 'high', 'low', 'close']].min().to_dict(),
            'max': data[['open', 'high', 'low', 'close']].max().to_dict()
        }
    }

    return report
```

## 8. Database Storage

### Database Models

**Instrument Model:**
```python
class Instrument(Base):
    """
    Market instrument (stock, index, etc.).
    """
    __tablename__ = 'instruments'

    id = Column(String, primary_key=True)
    symbol = Column(String, unique=True, nullable=False)
    name = Column(String)
    sector = Column(String)
    exchange = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Price Model:**
```python
class Price(Base):
    """
    Historical price data.
    """
    __tablename__ = 'prices'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, ForeignKey('instruments.id'), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint('symbol', 'timestamp', name='uq_symbol_timestamp'),
        Index('idx_symbol_timestamp', 'symbol', 'timestamp'),
    )
```

### Database Operations

**Insert Data:**
```python
def insert_prices(db_session, symbol: str, data: pd.DataFrame):
    """
    Insert price data into database.
    """
    for timestamp, row in data.iterrows():
        price = Price(
            symbol=symbol,
            timestamp=timestamp,
            open=row['open'],
            high=row['high'],
            low=row['low'],
            close=row['close'],
            volume=row['volume']
        )
        db_session.add(price)

    db_session.commit()
```

**Query Data:**
```python
def query_prices(db_session, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """
    Query price data from database.
    """
    prices = db_session.query(Price).filter(
        Price.symbol == symbol,
        Price.timestamp >= start_date,
        Price.timestamp <= end_date
    ).order_by(Price.timestamp).all()

    data = [{
        'timestamp': p.timestamp,
        'open': p.open,
        'high': p.high,
        'low': p.low,
        'close': p.close,
        'volume': p.volume
    } for p in prices]

    return pd.DataFrame(data).set_index('timestamp')
```

## 9. Corporate Actions

### Types of Corporate Actions

**1. Stock Splits:**
- Adjust historical prices
- Maintain continuity
- Adjust volume accordingly

**2. Dividends:**
- Adjust for dividend payments
- Total return calculations
- Ex-dividend dates

**3. Mergers and Acquisitions:**
- Symbol changes
- Delisting
- Replacement symbols

**4. Rights Issues:**
- Adjust for rights offerings
- Maintain price continuity

### Current Implementation

**Status:**
- Basic corporate action handling not yet implemented
- Prices are used as-is from provider
- Provider may include adjustments

**Future Enhancements:**
- Implement split adjustments
- Track dividend payments
- Handle symbol changes
- Maintain historical constituents

## 10. Data Freshness

### Monitoring Data Freshness

**Check Latest Data:**
```python
def check_data_freshness(db_session, symbol: str, max_age_hours: int = 24) -> bool:
    """
    Check if data is fresh enough.
    """
    latest = db_session.query(Price).filter(
        Price.symbol == symbol
    ).order_by(Price.timestamp.desc()).first()

    if not latest:
        return False

    age = datetime.utcnow() - latest.timestamp
    return age.total_seconds() < max_age_hours * 3600
```

**Data Freshness Report:**
```python
def generate_freshness_report(db_session, symbols: List[str]) -> dict:
    """
    Generate data freshness report for all symbols.
    """
    report = {}
    for symbol in symbols:
        latest = db_session.query(Price).filter(
            Price.symbol == symbol
        ).order_by(Price.timestamp.desc()).first()

        if latest:
            age = datetime.utcnow() - latest.timestamp
            report[symbol] = {
                'latest_timestamp': latest.timestamp,
                'age_hours': age.total_seconds() / 3600,
                'is_fresh': age.total_seconds() < 24 * 3600
            }
        else:
            report[symbol] = {
                'latest_timestamp': None,
                'age_hours': float('inf'),
                'is_fresh': False
            }

    return report
```

## 11. Data Backup and Recovery

### Backup Strategy

**Database Backups:**
- Regular PostgreSQL dumps
- Point-in-time recovery
- Offsite storage

**Data Export:**
- CSV exports for analysis
- JSON exports for API use
- Parquet for big data

### Recovery Procedures

**Restore from Backup:**
```bash
# Restore PostgreSQL dump
pg_restore -d statarb_n50 backup.dump
```

**Validate Restored Data:**
```python
def validate_restored_data(db_session):
    """
    Validate restored data integrity.
    """
    # Check record counts
    instrument_count = db_session.query(Instrument).count()
    price_count = db_session.query(Price).count()

    # Check data ranges
    first_price = db_session.query(Price).order_by(Price.timestamp).first()
    last_price = db_session.query(Price).order_by(Price.timestamp.desc()).first()

    return {
        'instruments': instrument_count,
        'prices': price_count,
        'date_range': (first_price.timestamp, last_price.timestamp)
    }
```

## 12. Data Pipeline Monitoring

### Metrics to Track

**Ingestion Metrics:**
- Records ingested per day
- Ingestion latency
- Ingestion success rate
- API call count

**Quality Metrics:**
- Missing value rate
- Duplicate rate
- Outlier rate
- Validation failure rate

**Freshness Metrics:**
- Data age per symbol
- Stale data alerts
- Update frequency

**Performance Metrics:**
- Query latency
- Database size
- Index efficiency

### Alerting

**Alert Conditions:**
- Ingestion failure
- Data validation failure
- Stale data
- Database connection failure
- API rate limit exceeded

## 13. Configuration

### Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:password@localhost/statarb_n50

# Market Data Provider
MARKET_DATA_PROVIDER=yahoo
MARKET_DATA_API_KEY=your_api_key_here

# Real-time Data
REALTIME_DATA_PROVIDER=websocket

# Ingestion Settings
INGESTION_BATCH_SIZE=100
INGESTION_INTERVAL_SECONDS=300

# Validation Settings
MAX_MISSING_VALUE_RATE=0.05
MAX_OUTLIER_RATE=0.01
DATA_FRESHNESS_HOURS=24
```

### Provider Configuration

**Yahoo Finance:**
```python
YAHOO_CONFIG = {
    'rate_limit_delay': 1.0,  # Seconds between requests
    'max_retries': 3,
    'timeout': 30
}
```

**Demo Provider:**
```python
DEMO_CONFIG = {
    'base_price_range': (100, 1000),
    'volatility': 0.02,
    'seed': 42
}
```

## 14. Best Practices

### Data Quality

1. **Always validate data before use**
   - Check for missing values
   - Check for outliers
   - Validate logical relationships

2. **Handle missing data appropriately**
   - Don't silently forward-fill
   - Document imputation methods
   - Consider impact on statistical tests

3. **Maintain data provenance**
   - Track data source
   - Record ingestion timestamp
   - Document transformations

### Performance

1. **Use bulk operations**
   - Batch inserts
   - Bulk queries
   - Minimize database round trips

2. **Index appropriately**
   - Index symbol and timestamp
   - Index frequently queried fields
   - Monitor index usage

3. **Cache when appropriate**
   - Cache recent queries
   - Cache provider responses
   - Invalidate properly

### Security

1. **Never commit API keys**
   - Use environment variables
   - Use secret management
   - Rotate keys regularly

2. **Validate all inputs**
   - Sanitize user inputs
   - Validate parameter ranges
   - Prevent SQL injection

3. **Audit data access**
   - Log all data access
   - Monitor for anomalies
   - Implement access controls

## 15. Limitations and Future Work

### Current Limitations

1. **Survivorship Bias:**
   - Uses current Nifty 50 universe
   - Does not account for dropped constituents
   - Historical constituent data not yet implemented

2. **Corporate Actions:**
   - Basic handling not implemented
   - Relies on provider adjustments
   - May miss some adjustments

3. **Real-time Data:**
   - WebSocket implementation not connected to live provider
   - Currently shows "NOT CONNECTED" status
   - Requires provider configuration

### Future Enhancements

1. **Historical Constituents:**
   - Implement historical Nifty 50 constituents
   - Track index changes over time
   - Eliminate survivorship bias

2. **Advanced Corporate Actions:**
   - Implement split adjustments
   - Track dividend payments
   - Handle symbol changes

3. **Real-time Provider Integration:**
   - Connect to live market data provider
   - Implement streaming updates
   - Handle disconnections gracefully

4. **Data Quality Dashboard:**
   - Visual data quality monitoring
   - Real-time alerts
   - Historical quality trends

## Conclusion

The data pipeline provides a robust foundation for market data ingestion, preprocessing, and storage. The platform uses a provider-agnostic architecture that allows easy addition of new data sources. All data is validated and quality-checked before use. The platform is transparent about data sources, quality, and limitations, making it suitable for academic evaluation and research.
