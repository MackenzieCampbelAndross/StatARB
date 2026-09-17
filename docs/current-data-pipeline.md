# Current Data Pipeline Audit

## Overview

This document audits the current implementation of the StatArb-N50 data pipeline, identifying what is working, what is mocked, and what gaps remain before implementing real market data.

**Audit Date:** 2026-09-17
**Status:** Development Phase - Backend Complete, Real Data Integration Pending

---

## 1. Current Data Source

### Market Data Provider Implementation

**Location:** `backend/app/data/providers.py`

**Current State:**
- ✅ Abstract `MarketDataProvider` interface defined
- ✅ `DemoDataProvider` implemented (deterministic, clearly labeled as demo)
- ✅ `YahooFinanceProvider` implemented (uses yfinance library)
- ❌ No production-grade real-time provider configured
- ❌ No WebSocket streaming provider implemented

**Provider Selection:**
- Environment variable: `MARKET_DATA_PROVIDER`
- Current default: Not set (would default to demo)
- Available options: `demo`, `yahoo` (historical only)

**Limitations:**
- Yahoo Finance does NOT provide real-time streaming WebSocket for NSE
- Yahoo Finance data is delayed (typically 15 minutes)
- No bid/ask spread data
- No level-2 market depth
- Rate limiting may affect real-time usage

**Configuration:**
```python
# Current .env.example
MARKET_DATA_PROVIDER=demo
MARKET_DATA_API_KEY=
```

**Gaps:**
- No real-time streaming provider implemented
- No authentication with production provider
- No provider health check mechanism
- No automatic reconnection logic
- No latency tracking

---

## 2. Historical Data Flow

### Current Implementation

**Data Ingestion:** `backend/app/data/ingestion.py`

**Flow:**
```
Provider.get_historical_ohlcv()
    ↓
DataIngestionService.ingest_historical_data()
    ↓
Database Storage (Price model)
```

**Current State:**
- ✅ Ingestion service implemented
- ✅ Database models for prices (Instrument, Price)
- ✅ Batch ingestion support
- ❌ No actual historical data ingested
- ❌ Database is empty (fresh migration)
- ❌ No scheduled/incremental ingestion

**Preprocessing:** `backend/app/data/preprocessing.py`

**Flow:**
```
Raw Data
    ↓
Timestamp Normalization
    ↓
Trading Day Alignment
    ↓
Missing Value Handling
    ↓
Duplicate Removal
    ↓
OHLCV Validation
```

**Current State:**
- ✅ DataPreprocessor class implemented
- ✅ Timestamp normalization (UTC)
- ✅ Trading day alignment
- ✅ Missing value handling (ffill, drop, interpolate)
- ✅ Duplicate removal
- ✅ OHLCV validation
- ❌ No preprocessing applied to actual data (no data yet)
- ❌ No data quality monitoring
- ❌ No outlier detection in production

**Database:** `backend/app/database/`

**Current State:**
- ✅ SQLAlchemy models defined
- ✅ Session management
- ✅ Alembic migrations configured
- ✅ Initial schema migration (001_initial_schema)
- ✅ SQLite for development, PostgreSQL ready
- ❌ Database is empty
- ❌ No indexes optimized for queries
- ❌ No data retention policy

**Gaps:**
- No historical data actually ingested
- No data quality monitoring
- No incremental updates
- No data archiving/cleanup
- No backup strategy

---

## 3. Real-Time Data Flow

### Current Implementation

**WebSocket Server:** `backend/app/realtime/websocket.py`

**Current State:**
- ✅ WebSocket endpoint at `/api/ws/signals`
- ✅ ConnectionManager for tracking clients
- ✅ Subscription management (pair-based)
- ✅ Heartbeat mechanism
- ❌ No actual market data connection
- ❌ No provider WebSocket integration
- ❌ Currently uses demo data generation (5-second intervals)
- ❌ No real-time price updates from provider

**Signal Stream:** `lib/services/websocket/signalStream.ts` (Frontend)

**Current State:**
- ✅ SignalStreamEvent type defined
- ✅ SignalStreamStatus type defined
- ❌ Placeholder implementation (no actual WebSocket connection)
- ❌ No connection to backend WebSocket
- ❌ Status always "NOT CONNECTED"

**Flow (Current - Mocked):**
```
Backend Demo Timer (5s)
    ↓
Generate Fake Signal
    ↓
WebSocket Broadcast
    ↓
Frontend (Not Connected)
```

**Flow (Required - Real):**
```
Provider WebSocket
    ↓
Market Data Stream
    ↓
Validation
    ↓
In-Memory State
    ↓
Quant Engine
    ↓
Signal Engine
    ↓
Backend WebSocket
    ↓
Frontend
```

**Gaps:**
- No provider WebSocket connection
- No real-time price updates
- No data validation on incoming ticks
- No latency tracking
- No stale data detection
- No connection health monitoring
- No automatic reconnection
- No exponential backoff

---

## 4. Database Flow

### Current Implementation

**Models:** `backend/app/models/`

**Instruments:**
- ✅ Instrument model (id, symbol, name, sector, exchange)
- ❌ No instruments populated

**Prices:**
- ✅ Price model (symbol, timestamp, open, high, low, close, volume)
- ✅ Unique constraint on (symbol, timestamp)
- ✅ Index on symbol and timestamp
- ❌ No price data stored

**Pairs:**
- ✅ Pair model (symbol_a, symbol_b, sector, correlation, coint_p_value, hedge_ratio, half_life)
- ❌ No pairs generated/stored

**Signals:**
- ✅ Signal model (pair_id, timestamp, z_score, signal, spread, hedge_ratio)
- ❌ No signals stored

**Backtests:**
- ✅ Backtest model (config, start_date, end_date, metrics)
- ✅ BacktestTrade model (backtest_id, entry_time, exit_time, pnl)
- ❌ No backtests run

**Research Experiments:**
- ✅ ResearchExperiment model (config, results)
- ❌ No experiments run

**Current Query Flow:**
```
API Request
    ↓
Database Query
    ↓
Empty Result (No Data)
    ↓
Return Empty Array
```

**Gaps:**
- Database is completely empty
- No data ingestion pipeline executed
- No data retention/cleanup
- No query optimization
- No caching layer

---

## 5. Quant Calculation Flow

### Current Implementation

**Quant Modules:** `backend/app/quant/`

**Correlation:** `app/quant/cointegration/engle_granger.py`
- ✅ CorrelationCalculator (Pearson correlation)
- ✅ Configurable lookback period
- ✅ Configurable threshold
- ✅ Returns correlation, p-value, observations
- ❌ Not used with real data (no data)

**Cointegration:** `app/quant/cointegration/engle_granger.py`
- ✅ EngleGrangerCointegration (two-step procedure)
- ✅ OLS regression for hedge ratio
- ✅ ADF test on residuals
- ✅ Configurable significance level
- ✅ Returns alpha, beta, adf_stat, p_value, is_cointegrated
- ❌ Not used with real data (no data)

**Spread:** `app/quant/spread/calculator.py`
- ✅ SpreadCalculator (S_t = A_t - βB_t)
- ✅ Rolling statistics (mean, std)
- ✅ Z-score calculation
- ✅ Half-life calculation (Ornstein-Uhlenbeck)
- ❌ Not used with real data (no data)

**Signals:** `app/quant/signals/engine.py`
- ✅ SignalEngine (LONG SPREAD, SHORT SPREAD, EXIT, WATCH)
- ✅ Configurable entry/exit thresholds
- ✅ Stop-loss support
- ✅ Max holding period
- ✅ Confidence scoring
- ❌ Not used with real data (no data)

**Backtesting:** `app/quant/backtesting/engine.py`
- ✅ BacktestEngine (no look-ahead bias)
- ✅ Transaction costs and slippage
- ✅ Position sizing (equal weight, volatility-adjusted)
- ✅ Performance metrics (Sharpe, Sortino, drawdown)
- ✅ Trade-by-trade tracking
- ❌ Not used with real data (no data)

**Walk-Forward:** `app/quant/backtesting/walk_forward.py`
- ✅ WalkForwardValidator (training/testing windows)
- ✅ In-sample vs out-of-sample separation
- ✅ Overfitting detection
- ❌ Not used with real data (no data)

**Risk Analytics:** `app/quant/risk/analytics.py`
- ✅ RiskAnalytics (VaR, Expected Shortfall)
- ✅ Sharpe and Sortino ratios
- ✅ Concentration risk (Herfindahl index)
- ✅ Correlation risk
- ✅ Risk limit validation
- ❌ Not used with real data (no data)

**Current Flow:**
```
API Request
    ↓
Quant Engine Called
    ↓
No Data Available
    ↓
Return Empty/Default Values
```

**Gaps:**
- All quant modules ready but no data to process
- No pair generation executed
- No cointegration analysis run
- No signals generated
- No backtests executed

---

## 6. Frontend API Flow

### Current Implementation

**API Adapter:** `lib/services/api.ts`

**Current State:**
```typescript
import * as demo from '@/lib/demo'
export const api: DataAdapter = demo.serviceContract
export const adapterMode = apiBaseUrl ? 'production' : 'demo'
```

**Frontend Usage:** `app/page.tsx`

**Current State:**
- ✅ All UI components import from `lib/demo/index.ts`
- ✅ Demo adapter provides deterministic data
- ✅ Demo labels clearly shown ("DEMO DATA", "CONNECTION PENDING")
- ❌ No actual API calls to backend
- ❌ Backend API not used by frontend
- ❌ Frontend and backend are disconnected

**API Endpoints Available (Backend):**
- ✅ GET /api/system/status
- ✅ GET /api/system/websocket
- ✅ GET /api/pairs
- ✅ GET /api/pairs/{pair_id}
- ✅ GET /api/signals
- ✅ GET /api/signals/{pair_id}
- ✅ POST /api/backtests
- ✅ GET /api/backtests/{backtest_id}
- ✅ POST /api/research/experiments
- ✅ GET /api/risk
- ✅ WS /api/ws/signals

**Current Flow:**
```
Frontend Component
    ↓
Demo Adapter (lib/demo/index.ts)
    ↓
Hardcoded Demo Data
    ↓
UI Display
```

**Required Flow:**
```
Frontend Component
    ↓
API Adapter (lib/services/api.ts)
    ↓
Backend API (localhost:8000)
    ↓
Database
    ↓
Quant Engine
    ↓
UI Display
```

**Gaps:**
- Frontend still uses demo adapter
- No HTTP client configured (fetch/axios)
- No error handling for API failures
- No loading states
- No WebSocket client implementation
- No reconnection logic

---

## 7. Remaining Gaps

### Critical Gaps

1. **No Real Market Data Source**
   - Current: Demo data only
   - Required: Production market data provider with real-time streaming
   - Blocker: Need to select and integrate a provider that supports NSE real-time data

2. **No Historical Data Ingested**
   - Current: Empty database
   - Required: Ingest historical Nifty 50 data
   - Blocker: Need to run ingestion pipeline

3. **No Real-Time Streaming**
   - Current: Mocked 5-second timer
   - Required: Provider WebSocket connection
   - Blocker: Need provider with WebSocket support

4. **Frontend Not Connected to Backend**
   - Current: Frontend uses demo adapter
   - Required: Frontend calls backend API
   - Blocker: Need to implement API client

5. **No Pair Generation**
   - Current: No pairs in database
   - Required: Generate and analyze Nifty 50 pairs
   - Blocker: Need historical data first

### Implementation Gaps

6. **Provider Health Monitoring**
   - Current: Basic status endpoint
   - Required: Comprehensive health checks, latency tracking, connection monitoring

7. **Data Quality Monitoring**
   - Current: Basic validation
   - Required: Real-time quality checks, stale data detection, outlier alerts

8. **WebSocket Reconnection**
   - Current: Basic disconnect handling
   - Required: Exponential backoff, automatic reconnection, graceful degradation

9. **Pair Discovery Process**
   - Current: Single process
   - Required: Separate periodic pair discovery from real-time monitoring

10. **Market Hours Handling**
    - Current: No market session logic
    - Required: Indian market session handling, closed market detection

### Testing Gaps

11. **Integration Tests**
    - Current: Unit tests for quant engine
    - Required: End-to-end integration tests for data pipeline

12. **Streaming Tests**
    - Current: No streaming tests
    - Required: WebSocket connection, reconnection, event processing tests

13. **Failure Scenario Tests**
    - Current: Basic error handling
    - Required: Provider disconnect, network failure, stale data tests

---

## 8. What is Working

### ✅ Backend Infrastructure

- FastAPI application running successfully
- Database schema created and migrated
- API endpoints implemented and accessible
- WebSocket endpoint available
- Quantitative engine modules implemented
- Test suite passing (28/28 tests)

### ✅ Frontend Infrastructure

- Next.js application running successfully
- v0-generated UI components functional
- Demo adapter provides deterministic data
- Clear demo labels in UI
- Type-safe service contract

### ✅ Documentation

- Architecture documentation complete
- Quantitative methodology documented
- Backtesting methodology documented
- Data pipeline documented
- Real-time architecture documented

### ✅ Development Environment

- Backend virtual environment configured
- Frontend dependencies installed
- Both servers running (localhost:8000, localhost:3000)
- Git repository initialized and pushed

---

## 9. What is Mocked

### ❌ Data Sources

- Market data: Demo data generation (not real)
- Real-time updates: 5-second timer (not real provider)
- Prices: Deterministic formula (not market prices)
- Volume: Fixed value (not real volume)

### ❌ Calculations

- Correlation: Not calculated (no data)
- Cointegration: Not calculated (no data)
- Hedge ratio: Not calculated (no data)
- Spread: Not calculated (no data)
- Z-score: Not calculated (no data)
- Signals: Not generated (no data)

### ❌ Database

- Instruments: Not populated
- Prices: Not stored
- Pairs: Not generated
- Signals: Not stored
- Backtests: Not run

### ❌ Real-Time Pipeline

- Provider connection: Not implemented
- WebSocket streaming: Not implemented
- Latency tracking: Not implemented
- Health monitoring: Not implemented
- Reconnection logic: Not implemented

---

## 10. Implementation Priority

### Phase 1: Data Provider Selection (CRITICAL)

**Required Before Anything Else:**
1. Research NSE-compatible market data providers
2. Verify real-time streaming capability
3. Verify WebSocket support
4. Verify historical data availability
5. Verify licensing/terms
6. Select provider and document limitations
7. Obtain API credentials

**Potential Providers to Evaluate:**
- Upstox (WebSocket available, NSE data)
- Zerodha Kite (WebSocket available, NSE data)
- FivePaisa (WebSocket available, NSE data)
- Angel One (WebSocket available, NSE data)
- Interactive Brokers (Global, may have NSE data)
- Alpha Vantage (Global, may not have real-time NSE)

**Documentation Required:**
- Create `docs/data-provider.md`
- Document exact provider selected
- Document data limitations
- Document latency expectations
- Document licensing restrictions

### Phase 2: Historical Data Ingestion

**Once Provider Selected:**
1. Configure provider credentials
2. Implement provider-specific adapter
3. Ingest Nifty 50 universe symbols
4. Ingest historical OHLCV data (at least 3-5 years)
5. Validate data quality
6. Store in database
7. Run data quality checks

### Phase 3: Pair Generation and Analysis

**Once Historical Data Available:**
1. Generate all Nifty 50 pairs (1,225 combinations)
2. Calculate correlation for all pairs
3. Run cointegration tests
4. Calculate hedge ratios
5. Calculate half-lives
6. Store qualifying pairs
7. Document pair statistics

### Phase 4: Real-Time Provider Integration

**Once Provider Selected:**
1. Implement provider WebSocket client
2. Handle authentication
3. Implement subscription management
4. Implement heartbeat/ping
5. Implement reconnection logic
6. Implement latency tracking
7. Implement health monitoring

### Phase 5: Real-Time Quant Engine

**Once Real-Time Provider Connected:**
1. Implement efficient pair state management
2. Implement incremental quant calculations
3. Implement stale data detection
4. Implement signal generation
5. Implement quality checks
6. Implement event broadcasting

### Phase 6: Frontend Integration

**Once Backend Pipeline Working:**
1. Implement HTTP client (fetch/axios)
2. Replace demo adapter with real API calls
3. Implement WebSocket client
4. Implement error handling
5. Implement loading states
6. Implement reconnection UI
7. Remove demo data from production path

### Phase 7: Testing and Validation

**Throughout Implementation:**
1. Integration tests for data pipeline
2. Streaming tests for WebSocket
3. Failure scenario tests
4. End-to-end validation
5. Performance testing
6. Documentation updates

---

## 11. Immediate Next Steps

**Step 1: Provider Research**
- Research NSE-compatible providers
- Evaluate real-time streaming capability
- Document findings in `docs/data-provider.md`

**Step 2: Provider Selection**
- Select appropriate provider
- Obtain API credentials
- Document limitations

**Step 3: Provider Implementation**
- Implement provider adapter
- Test historical data retrieval
- Test real-time streaming (if available)

**Step 4: Data Ingestion**
- Ingest Nifty 50 symbols
- Ingest historical data
- Validate data quality

**Step 5: Pipeline Integration**
- Connect provider to quant engine
- Implement real-time processing
- Connect to frontend

---

## 12. Conclusion

**Current State:**
- Backend infrastructure: ✅ Complete
- Quantitative engine: ✅ Complete
- Database schema: ✅ Complete
- API endpoints: ✅ Complete
- Documentation: ✅ Complete
- Tests: ✅ Complete

**Missing:**
- Real market data provider: ❌ CRITICAL BLOCKER
- Historical data: ❌ BLOCKER
- Real-time streaming: ❌ BLOCKER
- Frontend-backend integration: ❌ BLOCKER

**Root Cause:**
The system is architecturally complete but cannot function without a real market data provider that supports NSE real-time streaming. The current demo/yahoo finance implementations are insufficient for production use.

**Path Forward:**
1. Research and select an NSE-compatible provider
2. Implement provider integration
3. Ingest historical data
4. Implement real-time streaming
5. Integrate frontend

**Risk:**
If no suitable provider is available (e.g., no real-time NSE streaming API), the system cannot achieve its real-time goals and would need to pivot to a delayed-data model or alternative market.

---

**Audit Complete**
