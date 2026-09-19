# StatArb N50 Backend

Statistical arbitrage research platform backend for Nifty 50 equities.

## Overview

This backend provides a complete quantitative research platform for statistical arbitrage strategies on Nifty 50 equities. It includes:

- **Market Data Layer**: Provider-agnostic data ingestion and preprocessing
- **Quantitative Engine**: Correlation, cointegration, spread, Z-score, signals, backtesting, risk analytics
- **REST API**: Full API matching frontend service contract
- **Real-time Streaming**: WebSocket support for live signal delivery
- **Database**: PostgreSQL with SQLAlchemy ORM and Alembic migrations

## Setup

### Prerequisites

- Python 3.14+
- PostgreSQL (optional, SQLite for development)
- pip

### Installation

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

### Database Setup

**Option 1: PostgreSQL (Production)**
```bash
# Create PostgreSQL database
createdb statarb_n50

# Update DATABASE_URL in .env
# DATABASE_URL=postgresql://user:password@localhost/statarb_n50

# Run migrations
alembic upgrade head
```

**Option 2: SQLite (Development)**
```bash
# Use SQLite for development (default)
# DATABASE_URL=sqlite:///./statarb_n50.db

# Run migrations
alembic upgrade head
```

### Running the Server

Development server with auto-reload:
```bash
python -m app.main
```

Or using uvicorn directly:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### System Status
- `GET /api/system/status` - System component status
- `GET /api/system/websocket` - WebSocket endpoint information

### Pairs
- `GET /api/pairs` - List all pairs
- `GET /api/pairs/{pair_id}` - Get pair details

### Signals
- `GET /api/signals` - List all signals
- `GET /api/signals/{pair_id}` - Get signals for specific pair

### Backtesting
- `POST /api/backtests` - Run backtest
- `GET /api/backtests/{backtest_id}` - Get backtest results

### Research
- `POST /api/research/experiments` - Create research experiment
- `GET /api/research/experiments/{experiment_id}` - Get experiment results

### Risk
- `GET /api/risk` - Get risk metrics

### WebSocket
- `WS /api/ws/signals` - Real-time signal streaming

## Project Structure

```
backend/
├── app/
│   ├── api/               # FastAPI endpoints
│   │   ├── backtests.py   # Backtest endpoints
│   │   ├── pairs.py       # Pair endpoints
│   │   ├── research.py    # Research endpoints
│   │   ├── risk.py        # Risk analytics endpoints
│   │   ├── signals.py     # Signal endpoints
│   │   ├── system.py      # System status endpoints
│   │   └── websocket.py   # WebSocket endpoint
│   ├── core/              # Configuration and settings
│   │   └── config.py      # Settings class
│   ├── data/              # Data processing and providers
│   │   ├── ingestion.py   # Data ingestion service
│   │   ├── preprocessing.py # Data preprocessing
│   │   └── providers.py   # Market data providers
│   ├── database/          # Database configuration
│   │   ├── base.py        # SQLAlchemy base
│   │   └── session.py     # Database session
│   ├── models/            # SQLAlchemy models
│   │   ├── backtest.py    # Backtest models
│   │   ├── instrument.py  # Instrument model
│   │   ├── pair.py        # Pair model
│   │   ├── price.py       # Price model
│   │   ├── research.py    # Research experiment model
│   │   └── signal.py      # Signal model
│   ├── schemas/           # Pydantic schemas
│   │   ├── backtests.py   # Backtest schemas
│   │   ├── pairs.py       # Pair schemas
│   │   ├── research.py    # Research schemas
│   │   ├── risk.py        # Risk schemas
│   │   └── signals.py     # Signal schemas
│   ├── quant/             # Quantitative engine
│   │   ├── backtesting/   # Backtesting engine
│   │   │   ├── engine.py  # Main backtest engine
│   │   │   └── walk_forward.py # Walk-forward validation
│   │   ├── cointegration/ # Cointegration analysis
│   │   │   └── engle_granger.py # Engle-Granger test
│   │   ├── pairs/         # Pair generation
│   │   │   └── generator.py # Pair generator
│   │   ├── risk/          # Risk analytics
│   │   │   └── analytics.py # Risk calculations
│   │   ├── signals/       # Signal generation
│   │   │   └── engine.py  # Signal engine
│   │   └── spread/        # Spread calculation
│   │       └── calculator.py # Spread calculator
│   ├── realtime/          # Real-time streaming
│   │   └── websocket.py   # WebSocket handler
│   └── main.py            # Application entry point
├── tests/                 # pytest tests
│   └── test_quantitative.py # Quantitative engine tests
├── migrations/            # Alembic migrations
├── docs/                  # Documentation
│   ├── architecture.md    # System architecture
│   ├── quantitative-methodology.md # Quantitative methods
│   ├── backtesting.md     # Backtesting documentation
│   ├── data-pipeline.md   # Data pipeline documentation
│   └── realtime.md        # Real-time architecture
├── requirements.txt       # Python dependencies
├── .env.example           # Environment configuration template
└── README.md              # This file
```

## Development

### Running Tests

Run all tests:
```bash
pytest
```

Run specific test file:
```bash
pytest tests/test_quantitative.py
```

Run with coverage:
```bash
pytest --cov=app --cov-report=html
```

### Database Migrations

Create new migration:
```bash
alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback migration:
```bash
alembic downgrade -1
```

### Code Style

The project follows standard Python conventions:
- PEP 8 style guide
- Type hints where appropriate
- Docstrings for all public functions
- Clear variable and function names

## Configuration

### Environment Variables

**Database:**
- `DATABASE_URL`: Database connection string (default: sqlite:///./statarb_n50.db)

**Market Data:**
- `MARKET_DATA_PROVIDER`: Provider name (yahoo, demo)
- `MARKET_DATA_API_KEY`: API key for provider (if required)

**Real-time:**
- `REALTIME_DATA_PROVIDER`: Real-time provider (websocket, sse)

**API:**
- `API_HOST`: API host (default: 0.0.0.0)
- `API_PORT`: API port (default: 8000)

See `.env.example` for all available configuration options.

## Quantitative Engine

### Correlation
- Pearson correlation coefficient
- Configurable lookback period
- Configurable threshold (default: 0.70)

### Cointegration
- Engle-Granger two-step procedure
- Augmented Dickey-Fuller test
- Configurable significance level (default: 0.05)

### Spread
- Spread calculation: S_t = A_t - βB_t
- Rolling statistics (mean, std)
- Z-score calculation
- Half-life of mean reversion

### Signals
- LONG SPREAD, SHORT SPREAD, EXIT, WATCH
- Configurable entry/exit thresholds
- Stop-loss support
- Maximum holding period
- Confidence scoring

### Backtesting
- No look-ahead bias enforcement
- Transaction costs and slippage
- Position sizing (equal weight, volatility-adjusted)
- Performance metrics (Sharpe, Sortino, drawdown, etc.)
- Trade-by-trade tracking

### Walk-Forward Validation
- Training/testing window generation
- In-sample vs out-of-sample separation
- Overfitting detection
- Stability metrics

### Risk Analytics
- VaR (95%, 99%) and Expected Shortfall
- Sharpe and Sortino ratios
- Concentration risk (Herfindahl index)
- Correlation risk
- Risk limit validation

## Testing

The test suite includes:
- Correlation calculation tests
- Spread and Z-score tests
- Signal generation tests
- Backtesting engine tests
- Risk analytics tests
- Look-ahead bias prevention tests
- Date alignment tests
- No duplicate pairs tests

All tests use deterministic datasets and do not depend on live market data.

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- `architecture.md`: System architecture and integration
- `quantitative-methodology.md`: Mathematical methods and formulas
- `backtesting.md`: Backtesting methodology and best practices
- `data-pipeline.md`: Data ingestion and preprocessing
- `realtime.md`: Real-time streaming architecture

## Limitations

1. **Survivorship Bias**: Uses current Nifty 50 universe for historical testing. Historical constituent data not yet implemented.

2. **Corporate Actions**: Basic corporate action handling not implemented. Relies on provider adjustments.

3. **Real-time Data**: WebSocket implementation not connected to live provider. Shows "NOT CONNECTED" status until configured.

4. **Database**: Currently empty after migration. Requires data ingestion for full functionality.

## Future Enhancements

1. **Historical Constituents**: Implement historical Nifty 50 constituents to eliminate survivorship bias.

2. **Corporate Actions**: Implement split adjustments, dividend tracking, and symbol change handling.

3. **Real-time Provider**: Connect to live market data provider for real-time signal streaming.

4. **Additional Providers**: Add support for more market data providers (Alpha Vantage, Quandl, etc.).

5. **Advanced Analytics**: Add more sophisticated risk metrics and portfolio optimization.

## Security

- Never commit API keys or secrets
- Use environment variables for sensitive configuration
- Validate all user inputs
- Implement rate limiting for production
- Use HTTPS for production deployments

## License

This is a senior-level academic project for research and educational purposes.

## Support

For issues or questions, refer to the documentation in the `docs/` directory or check the test suite for usage examples.
