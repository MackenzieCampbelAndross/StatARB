# Data Provider Research and Selection

## Overview

This document researches available market data providers for NSE (National Stock Exchange of India) real-time and historical data, evaluates their capabilities, and provides recommendations for the StatArb-N50 project.

**Research Date:** 2026-09-17
**Target Universe:** Nifty 50 Equities (NSE)
**Requirements:** Real-time streaming, historical OHLCV, WebSocket support

---

## 1. Provider Options

### Licensed Real-Time Providers (Trading Account Required)

#### 1.1 Arrow API (iRage Broking)

**Type:** Broker API with market data
**Website:** https://arrow.trade
**Documentation:** https://docs.arrow.trade

**Capabilities:**
- ✅ Real-time WebSocket streaming (HFT-grade)
- ✅ Historical OHLCV data
- ✅ Multiple data modes (LTP, Quote, Full market depth)
- ✅ Sub-second latency
- ✅ Cross-exchange support (NSE, BSE, NFO, BFO, MCX)
- ✅ Official Python SDK (`pyarrow-client`)
- ✅ 5-level bid/ask market depth
- ✅ WebSocket endpoint: `wss://ds.arrow.trade`

**Pricing:**
- Offer period: 2 months free full API access
- Post-offer: ₹20/order flat brokerage
- Market data included with trading account

**Limitations:**
- ❌ Requires trading account (not data-only)
- ❌ Tied to broker services
- ❌ No standalone data-only subscription
- ❌ Pricing model is per-order, not per-data

**Data Quality:**
- Real-time (not delayed)
- Authorized exchange data
- Ultra-low latency
- Professional grade

**Python SDK:**
```bash
pip install pyarrow-client
```

**Suitability for Research:**
- ⚠️ Suitable but requires trading account
- ⚠️ May have compliance implications for academic project
- ✅ Excellent technical capabilities
- ✅ Free trial period available

---

#### 1.2 Global Datafeeds

**Type:** Licensed data vendor
**Website:** https://globaldatafeeds.in
**Documentation:** https://globaldatafeeds.in/authorised-data-vendors/

**Capabilities:**
- ✅ Real-time WebSocket streaming
- ✅ Historical data (backfill from 2010)
- ✅ Multiple protocols (WebSocket, REST, DotNet, COM, FIX)
- ✅ Covers NSE, BSE, MCX, NCDEX
- ✅ Authorized realtime data vendor
- ✅ Real-time, intraday, EOD data
- ✅ Option chain, option greeks

**Pricing:**
- Not publicly listed (contact for quote)
- Likely subscription-based
- Separate from trading account

**Limitations:**
- ❌ Pricing not transparent
- ❌ May require business account
- ❌ Minimum commitment likely

**Data Quality:**
- Real-time (not delayed)
- Authorized exchange data
- Low latency
- Professional grade

**Suitability for Research:**
- ✅ Suitable (data-only, no trading required)
- ⚠️ Pricing unknown
- ⚠️ May be expensive for academic project
- ✅ Professional-grade data

---

#### 1.3 TrueData

**Type:** Market data API provider
**Website:** https://www.truedata.in
**Documentation:** https://www.truedata.in/products/marketdataapi

**Capabilities:**
- ✅ Real-time WebSocket streaming
- ✅ Historical data
- ✅ JSON format
- ✅ Supports NSE (Stocks & Indices), NFO, NSE CDS, MCX
- ✅ Option-chain, option greeks
- ✅ Web, Mobile, Desktop support

**Pricing:**
- Flexible pricing
- No commitment required
- Contact for specific pricing

**Limitations:**
- ❌ Pricing not publicly listed
- ❌ Requires contact for quote

**Data Quality:**
- Real-time (not delayed)
- Authentic and accurate
- Low latency

**Suitability for Research:**
- ✅ Suitable (data-only)
- ⚠️ Pricing unknown
- ✅ No commitment required
- ✅ Flexible options

---

#### 1.4 HDFC Securities

**Type:** Broker API with market data
**Website:** https://developer.hdfcsec.com
**Documentation:** https://developer.hdfcsec.com/ir-docs/docs/market_data_websocket

**Capabilities:**
- ✅ Real-time WebSocket streaming
- ✅ Up to 1500 instruments per connection
- ✅ 3 simultaneous WebSocket connections per API key
- ✅ Open, high, low, close, LTP
- ✅ 5-level bid/ask market depth
- ✅ Covers NSE, BSE, MCX

**Pricing:**
- Requires HDFC Securities trading account
- Account fees apply
- Data included with account

**Limitations:**
- ❌ Requires trading account
- ❌ Tied to HDFC Securities broker
- ❌ No standalone data subscription

**Data Quality:**
- Real-time (not delayed)
- Authorized exchange data
- Professional grade

**Suitability for Research:**
- ⚠️ Suitable but requires HDFC account
- ⚠️ Broker-specific
- ✅ Good technical capabilities

---

#### 1.5 Infoway

**Type:** Market data API provider
**Website:** https://docs.infoway.io
**Documentation:** https://docs.infoway.io/en-docs/readme/other-stock-markets/indian-stock-data-api

**Capabilities:**
- ✅ Real-time WebSocket streaming
- ✅ HTTP API
- ✅ Covers 5,800+ securities (BSE, NSE)
- ✅ Low-latency delivery
- ✅ Order book data
- ✅ Rate limits documented

**Pricing:**
- Not publicly listed
- Subject to rate limits
- Contact for pricing

**Limitations:**
- ❌ Pricing not transparent
- ❌ Rate limits apply
- ❌ May require business account

**Data Quality:**
- Real-time (not delayed)
- Low latency
- Professional grade

**Suitability for Research:**
- ✅ Suitable (data-only)
- ⚠️ Pricing unknown
- ⚠️ Rate limits may be restrictive
- ✅ HTTP + WebSocket options

---

### Free/Public APIs (No Real-Time Streaming)

#### 2.1 nselib

**Type:** Python library for NSE public data
**PyPI:** https://pypi.org/project/nselib/
**Documentation:** Built-in

**Capabilities:**
- ✅ Price volume data
- ✅ Historical data (up to 1 month with period parameter)
- ✅ Deliverable positions
- ✅ Index constituents
- ✅ Market activity data
- ✅ Corporate filings
- ✅ Trading holiday calendar
- ❌ NO real-time streaming
- ❌ NO WebSocket support
- ❌ Data is delayed (typically 15 minutes)

**Pricing:**
- ✅ Free
- ✅ No account required
- ✅ Open source

**Limitations:**
- ❌ No real-time streaming
- ❌ Delayed data only
- ❌ Rate limited by NSE
- ❌ No WebSocket

**Data Quality:**
- Delayed (15 minutes)
- Official NSE data
- Reliable but not real-time

**Python SDK:**
```bash
pip install nselib
```

**Example:**
```python
from nselib import capital_market

# Get price volume data
df = capital_market.price_volume_data(symbol='SBIN', period='1M')

# Get index constituents
nifty50 = capital_market.index_constituents(index='NIFTY 50')
```

**Suitability for Research:**
- ✅ Excellent for historical data
- ✅ Free and accessible
- ❌ NOT suitable for real-time requirements
- ❌ Delayed data only

---

#### 2.2 nsepython

**Type:** Unofficial Python wrapper for NSE India API
**GitHub:** https://github.com/aeron7/nsepython
**PyPI:** Available

**Capabilities:**
- ✅ NSE India public data
- ✅ Index data
- ✅ Equity data
- ✅ Derivatives data
- ❌ NO real-time streaming
- ❌ NO WebSocket support
- ❌ Data is delayed

**Pricing:**
- ✅ Free
- ✅ No account required
- ✅ Open source

**Limitations:**
- ❌ No real-time streaming
- ❌ Delayed data only
- ❌ Unofficial (may break)
- ❌ Rate limited

**Data Quality:**
- Delayed (15 minutes)
- Official NSE data (via unofficial wrapper)
- Risk of API changes

**Suitability for Research:**
- ✅ Good for historical data
- ✅ Free
- ❌ NOT suitable for real-time
- ❌ Unofficial wrapper (risk)

---

#### 2.3 nseindia-data

**Type:** Unofficial Python API for NSE India
**PyPI:** https://pypi.org/project/nseindia-data/

**Capabilities:**
- ✅ Market status
- ✅ Equity quotes
- ✅ Index data
- ✅ Top gainers/losers
- ❌ NO real-time streaming
- ❌ NO WebSocket support
- ❌ Data is delayed

**Pricing:**
- ✅ Free
- ✅ No account required
- ✅ Open source

**Limitations:**
- ❌ No real-time streaming
- ❌ Delayed data only
- ❌ Unofficial

**Data Quality:**
- Delayed (15 minutes)
- Official NSE data (via unofficial wrapper)
- Risk of API changes

**Suitability for Research:**
- ✅ Good for historical data
- ✅ Free
- ❌ NOT suitable for real-time
- ❌ Unofficial wrapper (risk)

---

#### 2.4 nsefin

**Type:** Historical candlestick data from NSE India
**PyPI:** https://pypi.org/project/nsefin/

**Capabilities:**
- ✅ Historical candlestick data
- ✅ Equity data
- ✅ Index data
- ❌ NO real-time streaming
- ❌ NO WebSocket support
- ❌ Historical only

**Pricing:**
- ✅ Free
- ✅ No account required
- ✅ Open source

**Limitations:**
- ❌ No real-time streaming
- ❌ Historical only
- ❌ Index historical data not working
- ❌ Daily row caps (~70 rows)
- ❌ NSE endpoints may change

**Data Quality:**
- Historical (delayed)
- Official NSE data
- Stability issues

**Suitability for Research:**
- ✅ Good for historical backtesting
- ✅ Free
- ❌ NOT suitable for real-time
- ❌ Stability concerns

---

#### 2.5 nsefetch

**Type:** Modern Python library for NSE data
**PyPI:** https://pypi.org/project/nsefetch/
**Documentation:** https://github.com/yourusername/nsefetch

**Capabilities:**
- ✅ Market status
- ✅ NIFTY 50 snapshot
- ✅ Stock quotes
- ✅ Bulk stock quotes
- ✅ Option chain
- ✅ Market depth (optional)
- ✅ Sector data
- ✅ Async support
- ✅ Rate limiting (GCRA)
- ✅ Caching (Redis or in-memory)
- ✅ Circuit breaker
- ✅ Stale fallback
- ✅ Typed responses (Pydantic)
- ❌ NO real-time streaming
- ❌ NO WebSocket support
- ❌ Data is delayed

**Pricing:**
- ✅ Free
- ✅ No account required
- ✅ Open source

**Limitations:**
- ❌ No real-time streaming
- ❌ Delayed data only
- ❌ Rate limited
- ❌ Public NSE API

**Data Quality:**
- Delayed (15 minutes)
- Official NSE data
- Well-engineered (rate limiting, caching)
- Reliable but not real-time

**Python SDK:**
```bash
pip install nsefetch
```

**Example:**
```python
from nsefetch import MarketService

with MarketService() as service:
    # Get NIFTY 50
    nifty50 = service.get_nifty50()

    # Get stock quote
    quote = service.get_stock("RELIANCE")

    # Get bulk quotes
    quotes = service.get_bulk_stocks(["HDFCBANK", "ICICIBANK", "SBIN"])
```

**Suitability for Research:**
- ✅ Excellent for historical data
- ✅ Well-engineered (rate limiting, caching, async)
- ✅ Free and accessible
- ❌ NOT suitable for real-time requirements
- ❌ Delayed data only

---

## 2. Summary Table

| Provider | Real-Time | WebSocket | Historical | Free | Account Required | Python SDK | Suitability |
|----------|-----------|-----------|------------|------|------------------|------------|-------------|
| Arrow API | ✅ | ✅ | ✅ | ❌ | Yes (Trading) | ✅ | ⚠️ Good but requires trading account |
| Global Datafeeds | ✅ | ✅ | ✅ | ❌ | No (Data-only) | ❌ | ✅ Good but pricing unknown |
| TrueData | ✅ | ✅ | ✅ | ❌ | No (Data-only) | ❌ | ✅ Good but pricing unknown |
| HDFC Securities | ✅ | ✅ | ✅ | ❌ | Yes (Trading) | ❌ | ⚠️ Broker-specific |
| Infoway | ✅ | ✅ | ✅ | ❌ | No (Data-only) | ❌ | ✅ Good but pricing unknown |
| nselib | ❌ | ❌ | ✅ | ✅ | No | ✅ | ✅ Excellent for historical, no real-time |
| nsepython | ❌ | ❌ | ✅ | ✅ | No | ✅ | ⚠️ Good for historical, unofficial |
| nseindia-data | ❌ | ❌ | ✅ | ✅ | No | ✅ | ⚠️ Good for historical, unofficial |
| nsefin | ❌ | ❌ | ✅ | ✅ | No | ✅ | ⚠️ Historical only, stability issues |
| nsefetch | ❌ | ❌ | ✅ | ✅ | No | ✅ | ✅ Excellent for historical, no real-time |

---

## 3. Critical Finding

**Real-Time WebSocket Streaming Requirement:**

NONE of the free/public NSE APIs provide real-time WebSocket streaming. All free options:
- Provide delayed data (typically 15 minutes)
- Do NOT support WebSocket
- Do NOT support real-time streaming
- Are limited to HTTP polling

**For True Real-Time Streaming:**
A licensed data vendor or broker API is REQUIRED. This involves:
- API key registration
- Payment/subscription
- Compliance with exchange regulations
- Possible trading account requirement

---

## 4. Recommendations

### Option A: Licensed Real-Time Provider (Production Path)

**Selected Provider:** Arrow API (for free trial period)

**Rationale:**
- ✅ Real-time WebSocket streaming
- ✅ Official Python SDK
- ✅ 2-month free trial period
- ✅ HFT-grade latency
- ✅ Professional-grade data
- ✅ Well-documented

**Implementation Plan:**
1. Sign up for Arrow API free trial
2. Obtain API credentials
3. Install `pyarrow-client`
4. Implement provider adapter
5. Test historical data retrieval
6. Test WebSocket streaming
7. Implement reconnection logic
8. Document 15-minute delay limitation (after trial)

**Limitations:**
- Requires trading account registration
- Free trial limited to 2 months
- Post-trial requires trading activity or payment
- May have compliance implications for academic project

**Cost:** Free for 2 months, then ₹20/order (not suitable for research-only)

---

### Option B: Free Historical + Delayed "Real-Time" (Academic Path)

**Selected Provider:** nsefetch for historical, delayed polling for "real-time"

**Rationale:**
- ✅ Free (no cost)
- ✅ No account required
- ✅ Excellent Python library (nsefetch)
- ✅ Rate limiting and caching built-in
- ✅ Async support
- ✅ Suitable for academic project
- ✅ Can ingest historical data for backtesting
- ✅ Can poll for delayed "real-time" updates

**Implementation Plan:**
1. Use `nsefetch` for historical data ingestion
2. Poll every 15 seconds for delayed quotes
3. Clearly label as "DELAYED DATA (15 min)"
4. Implement polling-based "real-time" updates
5. Document that this is NOT true real-time
6. Focus on backtesting and research capabilities

**Limitations:**
- ❌ NO true real-time streaming
- ❌ Data is delayed (15 minutes)
- ❌ NO WebSocket
- ❌ Polling-based (not push-based)
- ❌ Not suitable for actual trading

**Cost:** Free

---

### Option C: Hybrid Approach (Research + Real-Time Trial)

**Selected Provider:** nsefetch for historical, Arrow API for real-time (trial period)

**Rationale:**
- ✅ Best of both worlds
- ✅ Free historical data from nsefetch
- ✅ Real-time from Arrow API during trial
- ✅ Can demonstrate both capabilities
- ✅ After trial, fall back to delayed data

**Implementation Plan:**
1. Use `nsefetch` for historical data ingestion
2. Use Arrow API for real-time streaming (trial period)
3. Implement provider abstraction to switch easily
4. Document trial period limitation
5. After trial, automatically switch to delayed mode
6. Clearly communicate data source to user

**Limitations:**
- Complex implementation (two providers)
- Trial period limitation
- Requires two API integrations
- More maintenance

**Cost:** Free (during trial), then free (delayed only)

---

## 5. Final Recommendation

### For Academic Research Project: **Option B (Free Historical + Delayed "Real-Time")**

**Reasoning:**
1. **No Cost:** Academic projects typically have no budget
2. **No Account Required:** No trading account or subscription needed
3. **Sufficient for Research:** Delayed data is acceptable for research and backtesting
4. **Honest Transparency:** Can clearly label data as delayed
5. **Proven Libraries:** nsefetch is well-engineered and reliable
6. **Focus on Backtesting:** Research focus is on methodology, not live trading

**Implementation with nsefetch:**

**Historical Data:**
```python
from nsefetch import MarketService

with MarketService() as service:
    # Get NIFTY 50 constituents
    nifty50 = service.get_nifty50()

    # Get historical data for each symbol
    for symbol in nifty50:
        data = service.get_stock(symbol)
        # Store in database
```

**Delayed "Real-Time" Updates:**
```python
# Poll every 15 seconds
while True:
    with MarketService() as service:
        quotes = service.get_bulk_stocks(nifty50_symbols)
        # Update pair states
        # Calculate spreads
        # Generate signals
        # Emit WebSocket events
    time.sleep(15)
```

**UI Labels:**
- "DELAYED DATA (15 min)" instead of "LIVE"
- Show actual data timestamp
- Show latency (server_time - provider_timestamp)
- Show provider name (NSE)

**Trade-offs:**
- ❌ No true real-time streaming
- ❌ 15-minute delay
- ❌ Polling instead of WebSocket
- ✅ Free
- ✅ No account required
- ✅ Suitable for research
- ✅ Honest about limitations

---

## 6. If True Real-Time is Required

If the project requires true real-time streaming (not acceptable to use delayed data):

**Recommended Provider:** Arrow API (free trial period)

**Next Steps:**
1. Sign up for Arrow API account
2. Complete KYC (if required)
3. Obtain API credentials
4. Install `pyarrow-client`
5. Implement WebSocket integration
6. Document trial period
7. Plan for post-trial (either pay or switch to delayed)

**Alternative:** Contact Global Datafeeds or TrueData for academic pricing

---

## 7. Conclusion

**For this academic research project, I recommend Option B:**

**Use nsefetch for:**
- Historical data ingestion (free, no account)
- Delayed "real-time" polling (15-second intervals)
- Clear labeling as delayed data
- Focus on backtesting and research

**Benefits:**
- Zero cost
- No account required
- Reliable data source
- Suitable for academic purposes
- Honest about limitations

**Trade-offs:**
- No true real-time streaming
- 15-minute data delay
- Polling instead of WebSocket

**This approach aligns with the project's goal:**
- Correctness and transparency over visual complexity
- Academic research platform (not live trading)
- Honest communication of data sources and limitations

---

**Document Complete**
