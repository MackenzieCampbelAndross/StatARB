# StatArb-N50 Architecture Documentation

## Current Frontend Architecture

### Technology Stack
- **Framework**: Next.js 16.3.3 with React 19
- **Language**: TypeScript 5.7.3
- **Styling**: Tailwind CSS 4.3.3 with shadcn/ui components
- **Package Manager**: pnpm 12.3.4
- **Build Tool**: Next.js built-in bundler

### Frontend Structure
```
app/
├── layout.tsx          # Root layout with metadata
├── page.tsx            # Main application (monolithic component)
├── [...slug]/page.tsx  # Catch-all route handler
└── globals.css         # Global styles

lib/
├── utils.ts            # Utility functions (cn helper)
├── demo/
│   └── index.ts        # Demo data adapter and service contract
└── services/
    ├── api.ts          # API service interface
    └── websocket/
        └── signalStream.ts  # WebSocket placeholder

components/
└── ui/                 # shadcn/ui components
```

### Current Service Interface

The frontend uses a service contract pattern defined in `lib/demo/index.ts`:

```typescript
// Data Types
type PairSignal = 'LONG SPREAD' | 'SHORT SPREAD' | 'EXIT' | 'WATCH'
type Range = '1D' | '1W' | '1M' | '3M' | '6M' | '1Y'
type Pair = {
  id: string
  pair: string
  a: string
  b: string
  sector: string
  correlation: number
  cointP: number
  hedgeRatio: number
  halfLife: number
  adfP: number
  z: number
  signal: PairSignal
}
type Signal = Pair & { priceA: number; priceB: number; spread: number; updated: string }
type BacktestConfig = {
  entry: number
  exit: number
  stop: number
  holding: number
  cost: number
  slippage: number
  position: string
  start: string
  end: string
}
type Trade = {
  id: number
  pair: string
  entryDate: string
  exitDate: string
  direction: 'LONG' | 'SHORT'
  entryZ: number
  exitZ: number
  holding: number
  pnl: number
  return: number
}

// Service Contract Functions
getPairs(filters?: FilterConfig): Pair[]
getPair(id: string): Pair
getSignals(): Signal[]
runBacktest(config: BacktestConfig): Promise<BacktestResult>
runExperiment(config: BacktestConfig): Promise<ExperimentResult>
```

### Current Demo Data Adapter

**Location**: `lib/demo/index.ts`

The demo adapter provides:
- **6 hardcoded pairs** with deterministic statistics
- **Deterministic time series** generation for charts
- **18 mock trades** for backtest results
- **Fixed backtest results** that vary slightly based on config
- **Experiment history** with 3 sample experiments
- **System status** showing demo mode

**Important**: All data is deterministic and fixed. The frontend is currently in demo mode with a clear "DEMO DATA" banner.

### WebSocket Interface

**Location**: `lib/services/websocket/signalStream.ts`

```typescript
type SignalStreamEvent = {
  pair: string
  priceA: number
  priceB: number
  spread: number
  zScore: number
  signal: string
  timestamp: string
}

type SignalStreamStatus = 'NOT CONNECTED' | 'CONNECTED'

signalStream = {
  status: 'NOT CONNECTED',
  connect: async () => ({ status: 'NOT CONNECTED' }),
  disconnect: () => undefined,
  subscribe: (listener) => () => undefined
}
```

Currently intentionally does not simulate streaming. This is ready for backend WebSocket/SSE integration.

### UI Sections and Routes

The application is a single-page app with client-side routing through these sections:

1. **Dashboard** (`/dashboard`)
   - Portfolio metrics (Capital, P&L, Win Rate, Sharpe)
   - Equity curve chart
   - Active opportunities list
   - System status panel

2. **Pair Scanner** (`/pairs`)
   - Filter controls (correlation, p-value, half-life, signal, search)
   - Pair table with statistics
   - Signal badges
   - Z-score indicators

3. **Pair Detail** (`/pairs/{id}`)
   - Full pair statistics
   - Spread/price chart with range selector
   - Research interpretation

4. **Signal Monitor** (`/signals`)
   - Signal table with price updates
   - Filter by signal type
   - Real-time timestamp display

5. **Backtesting** (`/backtest`)
   - Configuration form (entry/exit Z, holding period, costs, dates)
   - Performance metrics grid
   - Equity/drawdown/monthly charts
   - Trade history table with pagination

6. **Research Lab** (`/research`)
   - Experiment configuration
   - Experiment history comparison
   - Parameter exploration

7. **Risk Analytics** (`/risk`)
   - Risk metrics display
   - (Currently using demo data)

8. **Settings** (`/settings`)
   - Placeholder for configuration

### Current API Integration

**Location**: `lib/services/api.ts`

```typescript
import * as demo from '@/lib/demo'
export const api: DataAdapter = demo.serviceContract
export const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? ''
export const adapterMode = apiBaseUrl ? 'production' : 'demo'
```

The frontend is currently bound to the demo adapter. When `NEXT_PUBLIC_API_URL` is set, it should switch to production mode (to be implemented).

## Backend Integration Plan

### Phase 1: Repository Inspection ✅
- ✅ Inspect existing frontend architecture
- ✅ Document service interfaces
- ✅ Identify demo data locations
- ✅ Create architecture documentation

### Phase 2: Backend Foundation
- Set up FastAPI project structure
- Configure PostgreSQL with SQLAlchemy
- Create Alembic migrations
- Set up environment configuration (.env)

### Phase 3: Market Data Layer
- Create `MarketDataProvider` interface
- Implement provider abstraction
- Add historical data ingestion
- Support multiple providers (Yahoo Finance, Alpha Vantage, etc.)
- Data normalization and validation

### Phase 4: Universe & Pairs
- Nifty 50 universe service
- Pair generation (N×(N-1)/2 combinations)
- Avoid duplicate pairs
- Support historical constituents (future)

### Phase 5: Correlation & Cointegration
- Correlation calculation engine
- Configurable correlation threshold
- Engle-Granger cointegration implementation
- ADF test with configurable p-value
- Store test methodology and parameters

### Phase 6: Spread & Z-Score
- Spread calculation: S_t = A_t - βB_t
- Rolling statistics (mean, std)
- Z-score calculation
- Half-life of mean reversion
- Handle edge cases (NaN, Infinity)

### Phase 7: Signal Engine
- Configurable signal thresholds
- Rule-based signal generation
- Signal history tracking
- Confidence metrics

### Phase 8: Backtesting
- Walk-forward validation
- Transaction costs and slippage
- Position sizing
- Performance metrics (Sharpe, Sortino, drawdown, etc.)
- Trade ledger
- Prevent look-ahead bias

### Phase 9: Risk Analytics
- Portfolio exposure analysis
- Drawdown calculation
- Volatility metrics
- Concentration risk
- Correlated positions

### Phase 10: REST API
Implement endpoints matching the service contract:
- `GET /api/pairs` - Replace `getPairs()`
- `GET /api/pairs/{id}` - Replace `getPair()`
- `GET /api/signals` - Replace `getSignals()`
- `POST /api/backtests` - Replace `runBacktest()`
- `POST /api/research/experiments` - Replace `runExperiment()`
- `GET /api/risk` - Risk metrics
- `GET /api/system/status` - System health

### Phase 11: Real-time Pipeline
- WebSocket/SSE implementation
- Signal streaming
- Price updates
- Connection status monitoring
- Handle disconnections gracefully

### Phase 12: Frontend Integration
- Replace demo adapter with real API calls
- Update `lib/services/api.ts` to use fetch/axios
- Wire up WebSocket/SSE in `signalStream.ts`
- Remove demo data from production flows
- Show honest error states when backend unavailable

### Phase 13: Testing
- pytest for quantitative engine
- Unit tests for calculations
- Integration tests for API
- Look-ahead bias tests
- Data leakage tests

### Phase 14: Documentation
- Quantitative methodology documentation
- Backtesting methodology
- Data pipeline documentation
- Real-time architecture
- Final cleanup

## Backend Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── pairs.py
│   │   ├── signals.py
│   │   ├── backtests.py
│   │   ├── research.py
│   │   ├── risk.py
│   │   └── system.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── security.py
│   │   └── logging.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── providers.py
│   │   ├── ingestion.py
│   │   └── preprocessing.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── session.py
│   │   └── base.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── instrument.py
│   │   ├── price.py
│   │   ├── pair.py
│   │   ├── signal.py
│   │   ├── backtest.py
│   │   └── research.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── pairs.py
│   │   ├── signals.py
│   │   ├── backtests.py
│   │   └── research.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── universe.py
│   │   └── market_data.py
│   ├── quant/
│   │   ├── __init__.py
│   │   ├── pairs/
│   │   │   ├── __init__.py
│   │   │   └── generator.py
│   │   ├── cointegration/
│   │   │   ├── __init__.py
│   │   │   └── engle_granger.py
│   │   ├── spread/
│   │   │   ├── __init__.py
│   │   │   └── calculator.py
│   │   ├── signals/
│   │   │   ├── __init__.py
│   │   │   └── engine.py
│   │   ├── backtesting/
│   │   │   ├── __init__.py
│   │   │   ├── engine.py
│   │   │   └── walk_forward.py
│   │   └── risk/
│   │       ├── __init__.py
│   │       └── analytics.py
│   ├── realtime/
│   │   ├── __init__.py
│   │   ├── signal_stream.py
│   │   └── websocket.py
│   └── main.py
├── tests/
│   ├── __init__.py
│   ├── test_pairs.py
│   ├── test_cointegration.py
│   ├── test_spread.py
│   ├── test_signals.py
│   ├── test_backtesting.py
│   └── test_risk.py
├── migrations/
│   └── versions/
├── requirements.txt
├── .env.example
└── pyproject.toml
```

## Key Integration Points

### 1. Service Contract Matching
The backend API must match the exact TypeScript interface defined in `lib/demo/index.ts`. This ensures minimal frontend changes.

### 2. WebSocket Events
The backend WebSocket must emit events matching `SignalStreamEvent` type:
```typescript
{
  pair: string
  priceA: number
  priceB: number
  spread: number
  zScore: number
  signal: string
  timestamp: string
}
```

### 3. System Status
Backend must provide system status with these components:
- Market Data: CONNECTED / DISCONNECTED
- Quant Engine: READY / ERROR
- Signal Engine: READY / ERROR
- Database: CONNECTED / ERROR
- Real-Time Stream: CONNECTED / DISCONNECTED

### 4. Error Handling
When backend is unavailable:
- Show honest error states
- Do not fall back to demo data
- Display clear error messages
- Maintain UI functionality where possible

## Configuration

Environment variables needed:
```env
DATABASE_URL=postgresql://user:password@localhost/statarb
MARKET_DATA_API_KEY=your_api_key
MARKET_DATA_PROVIDER=yahoo_finance
REALTIME_DATA_PROVIDER=websocket
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Important Constraints

1. **No Look-Ahead Bias**: Never use future information in historical calculations
2. **No Survivorship Bias**: Document when using current universe for historical tests
3. **No Fake Data**: Never generate random financial data
4. **No Fake Real-Time**: Clearly show when real-time is not connected
5. **Configurable Thresholds**: All statistical parameters must be configurable
6. **Transparent Methodology**: Document all mathematical methods
7. **Separation of Concerns**: Keep quantitative logic separate from API/UI code
8. **Test Coverage**: Test all mathematical calculations with deterministic data

## Next Steps

Proceed with Phase 2: Backend Foundation
- Set up FastAPI project structure
- Configure PostgreSQL
- Create initial migrations
- Set up environment configuration
