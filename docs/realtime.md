# Real-Time Architecture Documentation

## Overview

This document explains the real-time streaming architecture for the StatArb-N50 platform, from market data updates to frontend signal delivery.

## 1. Architecture Overview

### System Components

**Real-Time Pipeline:**
```
Market Data Provider
↓
Price Update Service
↓
Spread Calculation Engine
↓
Z-Score Calculator
↓
Signal Generation Engine
↓
WebSocket Server
↓
Frontend Client
```

**Key Design Principles:**
- No fake real-time functionality
- Clear status indicators
- Graceful degradation
- Proper error handling

## 2. WebSocket Server

### Implementation

**Framework:** FastAPI WebSocket support

**Endpoint:** `/api/ws/signals`

**Connection Management:**
```python
ConnectionManager class:
- Tracks active connections
- Manages client subscriptions
- Handles heartbeats
- Monitors connection health
```

### Connection Lifecycle

**Connection:**
1. Client establishes WebSocket connection
2. Server accepts connection
3. Client subscribes to specific pairs
4. Server sends periodic updates
5. Client can unsubscribe or disconnect

**Disconnection:**
1. Client or server initiates close
2. Resources cleaned up
- Subscriptions removed
- Connection count updated

### Message Protocol

**Client to Server:**

**Subscribe:**
```json
{
  "action": "subscribe",
  "pair_ids": ["hdfcbank-icicibank", "axisbank-sbin"]
}
```

**Unsubscribe:**
```json
{
  "action": "unsubscribe",
  "pair_ids": ["hdfcbank-icicibank"]
}
```

**Heartbeat:**
```json
{
  "action": "heartbeat"
}
```

**Server to Client:**

**Signal Update:**
```json
{
  "type": "signal",
  "pair": "HDFCBANK / ICICIBANK",
  "priceA": 1732.4,
  "priceB": 823.7,
  "spread": 0.88,
  "zScore": 2.31,
  "signal": "SHORT SPREAD",
  "timestamp": "2026-09-17T20:55:25Z"
}
```

**Status Update:**
```json
{
  "type": "status",
  "status": "connected",
  "message": "WebSocket connection established",
  "client_id": "client_12345",
  "timestamp": "2026-09-17T20:55:25Z"
}
```

**Error Message:**
```json
{
  "type": "error",
  "message": "Error calculating signal data"
}
```

## 3. Signal Stream Service

### Implementation

**Location:** `app/realtime/signal_stream.py`

**Frontend Interface:**
```typescript
interface SignalStreamEvent {
  pair: string
  priceA: number
  priceB: number
  spread: number
  zScore: number
  signal: string
  timestamp: string
}

interface SignalStreamStatus {
  status: 'NOT CONNECTED' | 'CONNECTED'
}
```

**Current Status:**
```typescript
signalStream = {
  status: 'NOT CONNECTED',
  connect: async () => ({ status: 'NOT CONNECTED' }),
  disconnect: () => undefined,
  subscribe: (listener) => () => undefined
}
```

**Integration Point:**
- Will be connected to FastAPI WebSocket endpoint
- Backend will replace demo implementation
- Frontend will receive real signal updates

## 4. Update Frequency

### Current Implementation

**Demo Mode:**
- No real-time data
- Period: N/A (demo only)

**Production Plan:**
- **Option 1:** Poll-based (5-10 second intervals)
- **Option 2:** Push-based (WebSocket from provider)
- **Option 3:** Hybrid (WebSocket for signals, polling for prices)

### Update Triggers

**Price-Based:**
- New price data from provider
- Threshold crossings (Z-score bands)
- Signal changes

**Time-Based:**
- Periodic health checks
- Connection keep-alive
- Market status updates

## 5. Connection Status

### Status Indicators

**Market Data:**
- CONNECTED: Provider API is accessible
- DISCONNECTED: Provider API is down or credentials invalid

**Quant Engine:**
- READY: Quantitative calculations working
- ERROR: Calculation engine failure

**Signal Engine:**
- READY: Signal generation operational
- ERROR: Signal generation failure

**Database:**
- CONNECTED: Database accessible
- ERROR: Database connection issue

**Real-Time Stream:**
- CONNECTED: WebSocket has active connections
- DISCONNECTED: No active WebSocket connections

### Status API

**Endpoint:** `GET /api/system/status`

**Response:**
```json
{
  "market": "CONNECTED",
  "quant": "READY",
  "signal": "READY",
  "database": "CONNECTED",
  "realtime": "CONNECTED"
}
```

**WebSocket Info:**
**Endpoint:** `GET /api/system/websocket`

**Response:**
```json
{
  "status": "available",
  "endpoint": "/api/ws/signals",
  "message": "WebSocket endpoint available for real-time signal streaming"
}
```

## 6. Error Handling

### Connection Errors

**Provider Disconnection:**
- Log disconnection event
- Mark provider as DISCONNECTED
- Stop signal updates
- Show "REAL-TIME DATA DISCONNECTED" in UI
- Attempt reconnection

**WebSocket Errors:**
- Log error details
- Close affected connections
- Send error message to clients
- Allow reconnection

### Calculation Errors

**Data Issues:**
- Log calculation error
- Use last known good values
- Flag calculation status as ERROR
- Continue with other pairs

**Database Errors:**
- Log database errors
- Use cached data if available
- Flag database status as ERROR
- Allow continued operation with degraded service

## 7. Graceful Degradation

### When Real-Time Unavailable

**Behavior:**
- Show "REAL-TIME DATA NOT CONNECTED" clearly
- Continue showing last known values
- Disable real-time features
- Show honest error state
- Allow users to trigger manual refresh

### Alternative Data Sources

**Fallback to Periodic Polling:**
- If WebSocket fails, fall back to polling
- Update frequency: 30-60 seconds
- Clearly label as delayed data
- Show data timestamp

**Fallback to Cached Data:**
- Use last known good signal
- Show "CACHED DATA" indicator
- Update timestamp to show staleness
- Allow user to force refresh

## 8. Performance Considerations

### Scalability

**Connection Limits:**
- Default: No hard limit
- Monitor: Active connection count
- Thresholds: Add limits if needed

**Update Frequency:**
- Balance between responsiveness and resource usage
- Default: 5-second intervals (configurable)
- Higher frequency = more server load

**Bandwidth:**
- Minimize message size
- Only send changed data
- Use binary format if needed
- Implement compression if needed

### Latency

**Target Latency:**
- Market data to signal: < 1 second
- Signal to frontend: < 2 seconds
- Total latency: < 3 seconds

**Measurement:**
- Log timestamps at each stage
- Track cumulative latency
- Alert on latency degradation

## 9. Security Considerations

### Authentication

**Current:** No authentication (development mode)

**Production:**
- Implement authentication for WebSocket
- Validate client credentials
- Rate limiting per client
- IP whitelisting if needed

### Authorization

**Current:** All pairs accessible to all clients

**Production:**
- Pair-based access control
- User-specific subscriptions
- API key validation

### Data Protection

**No Sensitive Data:**
- Only market data transmitted
- No personal or account information
- No order execution data (research platform)

## 10. Testing Real-Time Features

### Unit Tests

**WebSocket Tests:**
- Connection establishment
- Message protocol
- Subscription management
- Error handling
- Reconnection logic

**Integration Tests:**
- End-to-end signal flow
- Provider to signal pipeline
- Database to signal pipeline
- WebSocket to frontend integration

### Load Tests

**Connection Load:**
- Multiple concurrent connections
- Subscription scalability
- Message throughput
- Memory usage monitoring

**Data Load:**
- High-frequency price updates
- Multiple pair subscriptions
- Calculation engine load
- Database query performance

## 11. Monitoring

### Metrics to Track

**Connection Metrics:**
- Active connection count
- Connection duration
- Reconnection attempts
- Failed connections

**Data Metrics:**
- Update frequency
- Data freshness (timestamp)
- Calculation latency
- Error rate

**System Metrics:**
- CPU usage
- Memory usage
- Database query times
- API response times

### Alerting

**Alert Conditions:**
- High error rate
- Long-running queries
- Database connection failures
- Provider disconnections
- High latency

## 12. Configuration

### Environment Variables

```env
REALTIME_DATA_PROVIDER=websocket
REALTIME_RECONNECT_INTERVAL=5
REALTIME_HEARTBEAT_INTERVAL=30
API_HOST=0.0.0.0
API_PORT=8000
```

### Runtime Configuration

**Update Frequency:**
- Configurable in code
- Default: 5 seconds
- Range: 1-60 seconds

**Connection Timeout:**
- Configurable heartbeat interval
- Default: 30 seconds
- Used to detect dead connections

**Subscription Limits:**
- Max pairs per client (if needed)
- Max total connections (if needed)
- Rate limits (if needed)

## 13. Frontend Integration

### WebSocket Client

**Current Demo Implementation:**
```typescript
signalStream = {
  status: 'NOT CONNECTED',
  connect: async () => ({ status: 'NOT CONNECTED' }),
  disconnect: () => undefined,
  subscribe: (listener) => () => undefined
}
```

**Production Integration:**
```typescript
const ws = new WebSocket('ws://localhost:8000/api/ws/signals')

ws.onopen = () => {
  ws.send(JSON.stringify({
    action: 'subscribe',
    pair_ids: ['hdfcbank-icicibank']
  }))
}

ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  if (data.type === 'signal') {
    // Update UI with signal data
  }
}
```

### State Management

**Signal Stream State:**
- Connection status
- Current signals
- Last update timestamp
- Error state
- Subscription list

### UI Updates

**When Signal Received:**
- Update pair display
- Update Z-score indicator
- Update signal badge
- Update timestamp
- Trigger visual indicators

**When Disconnected:**
- Show "REAL-TIME DATA DISCONNECTED"
- Grey out real-time features
- Show last known state
- Enable manual refresh button

## 14. Future Enhancements

### Advanced Features

**Server-Side Calculations:**
- Offload calculations to server
- Reduce client-side processing
- Handle multiple pairs efficiently

**Push Notifications:**
- Alert on signal changes
- Threshold breach notifications
- System status alerts

**Backtesting Real-Time:**
- Paper trading mode
- Real-time strategy monitoring
- Live performance tracking

**Market Simulator:**
- Simulated live market data
- Testing environment
- Strategy validation

## 15. Troubleshooting

### Common Issues

**Connection Fails:**
- Check provider API key
- Verify WebSocket endpoint
- Check CORS configuration
- Check firewall settings

**No Updates:**
- Check subscription configuration
- Verify data is arriving
- Check calculation engine logs
- Verify database queries

**Slow Updates:**
- Check update frequency setting
- Check database query performance
- Check calculation engine optimization
- Check network latency

**High Memory Usage:**
- Monitor connection count
- Check for memory leaks
- Optimize data structures
- Implement connection limits

## Conclusion

The real-time architecture provides a foundation for live signal delivery. The system is designed to be honest about data sources and connection status. When real-time data is not available, the system clearly indicates this rather than pretending to be live. The WebSocket implementation follows best practices for reliability, performance, and user experience.
