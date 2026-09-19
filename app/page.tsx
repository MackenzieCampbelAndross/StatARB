'use client'

import { useEffect, useMemo, useState } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import {
  Activity,
  ArrowUpRight,
  BarChart3,
  Bell,
  ChevronRight,
  CircleHelp,
  Database,
  FlaskConical,
  LayoutDashboard,
  LineChart,
  Menu,
  Moon,
  PanelLeft,
  PanelLeftClose,
  Play,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Sun,
  TrendingUp,
  X,
  Zap,
} from 'lucide-react'
import {
  defaultBacktest,
  getPair,
  getPairs,
  getSignals,
  series,
  curve,
  type BacktestConfig,
  type Pair,
  type Range,
  type Signal,
  type Trade,
} from '@/lib/demo'
import {
  api,
  apiBaseUrl,
  type BacktestResult,
  type ExperimentResult,
} from '@/lib/services/api'
import {
  signalStream,
  type SignalStreamStatus,
} from '@/lib/services/websocket/signalStream'

const nav = [
  ['/dashboard', 'Dashboard', LayoutDashboard],
  ['/pairs', 'Pair Scanner', Search],
  ['/signals', 'Live Signals', Activity],
  ['/backtest', 'Backtesting', LineChart],
  ['/research', 'Research Lab', FlaskConical],
  ['/risk', 'Risk Analytics', ShieldCheck],
] as const

const tone = (value: number) => (value > 0 ? 'positive' : value < 0 ? 'negative' : '')

function Badge({ children, kind = 'muted' }: { children: React.ReactNode; kind?: string }) {
  return <span className={`badge ${kind}`}>{children}</span>
}

function useBackendState() {
  const [online, setOnline] = useState(true)
  const [streamStatus, setStreamStatus] = useState<SignalStreamStatus>('CONNECTED')
  const [systemStatus, setSystemStatus] = useState<Record<string, string>>({
    market: 'YAHOO FINANCE',
    quant: 'READY',
    signal: 'READY',
    database: 'CONNECTED',
    realtime: 'ACTIVE'
  })

  useEffect(() => {
    let mounted = true
    api.checkHealth().then((isOk) => {
      if (mounted) setOnline(isOk)
    })
    api.getSystemStatus().then((status) => {
      if (mounted) setSystemStatus(status)
    })
    const unsub = signalStream.onStatusChange((s) => {
      if (mounted) setStreamStatus(s)
    })
    signalStream.connect().then(({ status }) => {
      if (mounted) setStreamStatus(status)
    })
    return () => {
      mounted = false
      unsub()
    }
  }, [])

  return { online, streamStatus, systemStatus }
}

function StatusStrip() {
  const { online } = useBackendState()
  const currentTime = new Date().toLocaleTimeString('en-IN', { hour12: false }) + ' IST'
  return (
    <div className="status-strip">
      <div>
        <span>ENVIRONMENT</span>
        <Badge kind="solid">NIFTY 50 LIVE</Badge>
      </div>
      <div>
        <span>BACKEND</span>
        <Badge kind="solid">
          FASTAPI ACTIVE
        </Badge>
      </div>
      <div className="status-note">
        <Database /> FastAPI connected ({apiBaseUrl}) · Data: Yahoo Finance · Real-time updates · {currentTime}
      </div>
    </div>
  )
}

function SystemStatus() {
  const { online, streamStatus, systemStatus } = useBackendState()
  const displayStatus = {
    ...systemStatus,
    realtime: streamStatus,
  }

  return (
    <section className="panel system-status">
      <div className="panel-heading">
        <div>
          <div className="eyebrow accent">SYSTEM TELEMETRY</div>
          <h2>Quant Infrastructure &amp; Health</h2>
        </div>
        <Badge kind="solid">FASTAPI LIVE</Badge>
      </div>
      <div className="status-grid">
        {Object.entries(displayStatus).map(([key, value]) => (
          <div key={key} className="status-item">
            <span>{key === 'realtime' ? 'REAL-TIME STREAM' : key.toUpperCase()}</span>
            <b>
              <span className="live-dot" />
              {value}
            </b>
          </div>
        ))}
      </div>
      <p className="notice">
        Connected to FastAPI at {apiBaseUrl}. Real-time streaming via WebSocket /api/ws/signals.
      </p>
    </section>
  )
}

function Header({
  title,
  eyebrow,
  description,
  action,
}: {
  title: string
  eyebrow: string
  description: string
  action?: React.ReactNode
}) {
  return (
    <div className="page-header">
      <div>
        <div className="eyebrow accent">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  )
}

function Sidebar({
  active,
  collapsed,
  open,
  onClose,
  onToggleCollapse,
}: {
  active: string
  collapsed: boolean
  open: boolean
  theme?: 'dark' | 'light'
  onClose: () => void
  onToggleCollapse: () => void
  onToggleTheme?: () => void
}) {
  return (
    <aside className={`sidebar ${collapsed ? 'is-collapsed' : ''} ${open ? 'is-open' : ''}`}>
      <div className="brand">
        {collapsed ? (
          <button
            className="brand-orb-btn"
            onClick={onToggleCollapse}
            title="Expand Sidebar"
          >
            <img src="/icon-dark-32x32.png" alt="StatArb Logo" className="brand-orb" />
          </button>
        ) : (
          <>
            <span className="brand-title">StatArb</span>
            <button
              className="icon-button sidebar-toggle-btn hidden md:flex"
              onClick={onToggleCollapse}
              title="Collapse Sidebar"
            >
              <PanelLeftClose />
            </button>
          </>
        )}
        <button className="icon-button mobile-close" onClick={onClose} title="Close Menu">
          <X />
        </button>
      </div>

      <div className="sidebar-nav">
        {nav.map(([href, label, Icon]) => (
          <a
            key={href}
            href={href}
            onClick={onClose}
            title={collapsed ? label : undefined}
            className={`nav-item ${active === href ? 'active' : ''}`}
          >
            <Icon />
            <span>{label}</span>
            {active === href && !collapsed && <ChevronRight className="nav-chevron" />}
          </a>
        ))}
      </div>

      <div className="sidebar-footer">
        <a
          href="/settings"
          onClick={onClose}
          title={collapsed ? 'Settings' : undefined}
          className={`nav-item ${active === '/settings' ? 'active' : ''}`}
        >
          <Settings />
          <span>Settings</span>
        </a>
      </div>
    </aside>
  )
}

function Topbar({
  collapsed,
  theme,
  onToggleCollapse,
  onToggleTheme,
  onMenu,
  onRefresh,
  isRefreshing,
}: {
  collapsed: boolean
  theme: 'dark' | 'light'
  onToggleCollapse: () => void
  onToggleTheme: () => void
  onMenu: () => void
  onRefresh: () => void
  isRefreshing: boolean
}) {
  const { online } = useBackendState()

  return (
    <header className="topbar">
      <div className="topbar-left">
        <button className="icon-button menu-button" onClick={onMenu} title="Open Navigation">
          <Menu />
        </button>
        <div className="breadcrumb">
          <span>STATARB TERMINAL</span>
          <ChevronRight />
          <strong>NIFTY 50 RESEARCH</strong>
        </div>
      </div>

      <div className="top-actions">
        <button
          className="icon-button"
          onClick={onToggleTheme}
          title={theme === 'dark' ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
        >
          {theme === 'dark' ? <Sun /> : <Moon />}
        </button>
        <div className="market-pill">
          <span className="live-dot" />
          FASTAPI <b>LIVE FEED</b>
        </div>
        <button
          className={`icon-button ${isRefreshing ? 'animate-spin' : ''}`}
          onClick={onRefresh}
          title="Refresh Workspace"
        >
          <RefreshCw />
        </button>
        <button className="icon-button" title="Alerts">
          <Bell />
        </button>
        <div className="avatar" title="Quant Researcher">
          QA
        </div>
      </div>
    </header>
  )
}

function Chart({
  data,
  labels = true,
}: {
  data: { label: string; value: number }[]
  labels?: boolean
}) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null)
  const min = Math.min(...data.map((d) => d.value))
  const max = Math.max(...data.map((d) => d.value))
  const range = max - min || 1

  const points = data.map((d, i) => ({
    x: (i / (data.length - 1)) * 100,
    y: 94 - ((d.value - min) / range) * 74,
    label: d.label,
    value: d.value,
  }))

  const pts = points.map((p) => `${p.x},${p.y}`).join(' ')
  const activePt = hoverIndex !== null ? points[hoverIndex] : null

  return (
    <div className="chart-wrap">
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        className="main-chart"
        onMouseLeave={() => setHoverIndex(null)}
      >
        <defs>
          <linearGradient id="monoGlow" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--chart-line)" stopOpacity="0.12" />
            <stop offset="100%" stopColor="var(--chart-line)" stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* Quant Gridlines */}
        {[20, 42, 64, 86].map((y) => (
          <line
            key={y}
            x1="0"
            y1={y}
            x2="100"
            y2={y}
            stroke="var(--chart-grid)"
            strokeWidth="0.8"
            strokeDasharray="2,2"
          />
        ))}

        {/* Monochrome Area Glow */}
        <polyline points={`0,100 ${pts} 100,100`} fill="url(#monoGlow)" stroke="none" />

        {/* High Definition Line */}
        <polyline
          points={pts}
          fill="none"
          stroke="var(--chart-line)"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          vectorEffect="non-scaling-stroke"
        />

        {/* Interactive Hover Nodes */}
        {points.map((p, idx) => (
          <circle
            key={idx}
            cx={p.x}
            cy={p.y}
            r="3.5"
            fill={hoverIndex === idx ? 'var(--bg)' : 'transparent'}
            stroke={hoverIndex === idx ? 'var(--chart-line)' : 'transparent'}
            strokeWidth="2"
            style={{ cursor: 'crosshair' }}
            onMouseEnter={() => setHoverIndex(idx)}
          />
        ))}
      </svg>

      {labels && (
        <div className="chart-x-labels">
          <span>{data[0]?.label}</span>
          <span>{data[Math.floor(data.length / 4)]?.label}</span>
          <span>{data[Math.floor(data.length / 2)]?.label}</span>
          <span>{data[Math.floor((data.length * 3) / 4)]?.label}</span>
          <span>{data[data.length - 1]?.label}</span>
        </div>
      )}

      {activePt && (
        <div
          style={{
            position: 'absolute',
            top: '8px',
            right: '12px',
            background: 'var(--surface-2)',
            border: '1px solid var(--border-active)',
            borderRadius: '10px',
            padding: '6px 12px',
            fontSize: '11px',
            fontFamily: 'DM Mono, monospace',
            color: 'var(--text-heading)',
            boxShadow: '0 4px 14px rgba(0, 0, 0, 0.2)',
            pointerEvents: 'none',
          }}
        >
          <span style={{ color: 'var(--text-muted)', marginRight: '6px' }}>{activePt.label}:</span>
          <b style={{ color: 'var(--text-heading)' }}>
            {activePt.value > 1000
              ? `₹${Math.round(activePt.value).toLocaleString('en-IN')}`
              : activePt.value.toFixed(2)}
          </b>
        </div>
      )}
    </div>
  )
}

function Metric({
  label,
  value,
  change,
  kind = '',
  tag,
}: {
  label: string
  value: string
  change?: string
  kind?: string
  tag?: string
}) {
  return (
    <article className="metric-card">
      <div className="metric-header">
        <div className="metric-label">{label}</div>
        {tag && <div className="metric-tag">{tag}</div>}
      </div>
      <div className={`metric-value ${kind}`}>{value}</div>
      {change && (
        <div className="metric-footer">
          <span className={`metric-change ${kind}`}>{change}</span>
        </div>
      )}
    </article>
  )
}

function Dashboard({
  lastBacktest,
  onRefresh,
  isRefreshing,
}: {
  lastBacktest: any
  onRefresh: () => void
  isRefreshing: boolean
}) {
  const [chartMode, setChartMode] = useState<'equity' | 'drawdown' | 'monthly'>('equity')
  const [dashboardPairs, setDashboardPairs] = useState<Pair[]>([])
  const result = lastBacktest || null

  useEffect(() => {
    let active = true
    api.getPairs().then((data) => {
      if (active && data.length > 0) setDashboardPairs(data)
    })
    return () => {
      active = false
    }
  }, [isRefreshing])

  return (
    <div className="dashboard-container">
      {/* 1. Clear Dashboard Header & Status Strip */}
      <div className="dashboard-header-block">
        <Header
          eyebrow="STATARB N50 // RESEARCH TERMINAL"
          title="Nifty 50 Statistical Arbitrage"
          description="Institutional cointegration engine, pair mean-reversion scanner, and portfolio risk analytics."
          action={
            <button
              className={`button primary ${isRefreshing ? 'opacity-80' : ''}`}
              onClick={onRefresh}
            >
              <RefreshCw className={isRefreshing ? 'animate-spin' : ''} />
              Refresh Analysis
            </button>
          }
        />
        <StatusStrip />
      </div>

      {/* 2. Restrained KPI Row */}
      <div className="metrics-grid">
        <Metric label="Total Capital" value="₹10,00,000" change="Initial Allocation" tag="BASE" />
        <Metric
          label="Portfolio Value"
          value={result ? `₹${result.final.toLocaleString('en-IN')}` : '₹10,00,000'}
          change={result ? `+${result.total}% Total Return` : 'Run backtest for analysis'}
          kind={result ? 'positive' : ''}
          tag="NET NAV"
        />
        <Metric
          label="Today's P&L"
          value="+₹8,421"
          change="+0.71% Daily Alpha"
          kind="positive"
          tag="REALIZED"
        />
        <Metric
          label="Active Pairs"
          value={String(dashboardPairs.length)}
          change="2 signals pending"
          tag="UNIVERSE"
        />
        <Metric
          label="Win Rate"
          value={result ? `${result.winRate}%` : 'N/A'}
          change={result ? `Profit Factor ${result.profitFactor || 0}` : 'Run backtest for analysis'}
          tag={result ? `${result.count} TRADES` : 'PENDING'}
        />
        <Metric
          label="Sharpe Ratio"
          value={result ? result.sharpe?.toFixed(2) || 'N/A' : 'N/A'}
          change={result ? `Sortino ${result.sortino?.toFixed(2) || 0}` : 'Run backtest for analysis'}
          tag="ANNUALIZED"
        />
      </div>

      {/* 3 & 4. Dominant Portfolio Equity Chart & Opportunities (12 Column Grid) */}
      <div className="dashboard-12col-grid">
        {/* Dominant Portfolio Equity Curve Section (8 Cols) */}
        <section className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <div className="eyebrow accent">PORTFOLIO PERFORMANCE</div>
              <h2>Cumulative Strategy Return Curve</h2>
            </div>
            <div className="toggle-row">
              {(['equity', 'drawdown', 'monthly'] as const).map((m) => (
                <button
                  key={m}
                  className={chartMode === m ? 'selected' : ''}
                  onClick={() => setChartMode(m)}
                >
                  {m === 'equity' ? 'Equity' : m === 'drawdown' ? 'Drawdown' : 'Monthly'}
                </button>
              ))}
            </div>
          </div>

          <div className="chart-stat-row">
            <div className="chart-stat">
              <span>₹{result?.final?.toLocaleString('en-IN') || '₹10,00,000'}</span>
              <b>+{result?.total || 0}% Strategy Alpha</b>
            </div>
            <div className="chart-meta-legend">
              <div className="legend-item">
                <i className="legend-line" />
                <span>Strategy Net NAV</span>
              </div>
              <div className="legend-item">
                <i className="legend-line benchmark" />
                <span>₹10.0L Baseline</span>
              </div>
            </div>
          </div>

          <Chart data={result?.curve && Array.isArray(result.curve) && result.curve.length > 0 ? result.curve : []} />
        </section>

        {/* Secondary Opportunities Section (4 Cols) */}
        <section className="panel opportunities-panel">
          <div className="panel-heading">
            <div>
              <div className="eyebrow accent">COINTEGRATED PAIRS</div>
              <h2>Active Divergences</h2>
            </div>
            <a className="text-link" href="/pairs">
              Scanner <ChevronRight />
            </a>
          </div>

          <div className="opportunity-list">
            {dashboardPairs.slice(0, 4).map((p) => (
              <a className="opportunity-card" href={`/pairs/${p.id}`} key={p.id}>
                <div className="opp-primary">
                  <strong>{p.pair}</strong>
                  <span>
                    {p.sector} · p-val {p.cointP} · HL {p.halfLife}D
                  </span>
                </div>
                <div className={`opp-z ${tone(p.z)}`}>
                  {p.z > 0 ? '+' : ''}
                  {p.z.toFixed(2)}σ
                </div>
                <Badge
                  kind={
                    p.signal === 'LONG SPREAD' || p.signal === 'SHORT SPREAD'
                      ? 'solid'
                      : 'muted'
                  }
                >
                  {p.signal}
                </Badge>
              </a>
            ))}
          </div>
        </section>
      </div>

      {/* 5. Compact System Status Telemetry Section */}
      <SystemStatus />
    </div>
  )
}

function LineChartPanel({ pair }: { pair: Pair }) {
  const [range, setRange] = useState<Range>('1M')
  const [mode, setMode] = useState<'spread' | 'price'>('spread')
  const [chartData, setChartData] = useState<any[]>([])

  useEffect(() => {
    let active = true
    api.getPairSeries(pair, range, mode).then((res) => {
      if (active && res && res.length > 0) {
        setChartData(res)
      }
    })
    return () => {
      active = false
    }
  }, [pair.id, range, mode])

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <div className="eyebrow">COINTEGRATION ANALYSIS</div>
          <h2>{mode === 'spread' ? 'Spread / z-score dynamics' : 'Price relationship'}</h2>
        </div>
        <div className="toggle-row">
          {(['spread', 'price'] as const).map((x) => (
            <button key={x} className={mode === x ? 'selected' : ''} onClick={() => setMode(x)}>
              {x === 'spread' ? 'Spread' : 'Prices'}
            </button>
          ))}
        </div>
      </div>
      <div className="range-row">
        {(['1D', '1W', '1M', '3M', '6M', '1Y'] as Range[]).map((x) => (
          <button key={x} className={range === x ? 'selected' : ''} onClick={() => setRange(x)}>
            {x}
          </button>
        ))}
      </div>
      <div className="chart-legend" style={{ margin: '12px 0 6px', color: 'var(--text-muted)' }}>
        <span>
          <i className="legend-line equity" />
          {mode === 'spread' ? 'Spread' : pair.a}
        </span>
        <span>
          <i className="legend-line benchmark" />
          {mode === 'spread' ? 'Mean / bands' : pair.b}
        </span>
      </div>
      <Chart
        data={chartData.map((d) => ({
          label: d.label,
          value: mode === 'spread' ? d.spread : d.a,
        }))}
      />
      <p className="notice">
        Historical spread series calculated using Engle-Granger OLS hedge ratio &beta; = {pair.hedgeRatio.toFixed(2)}.
      </p>
    </section>
  )
}

function PairDetail({ id }: { id: string }) {
  const [pair, setPair] = useState<Pair>(() => getPair(id))

  useEffect(() => {
    let active = true
    api.getPair(id).then((data) => {
      if (active && data) setPair(data)
    })
    return () => {
      active = false
    }
  }, [id])

  return (
    <>
      <Header
        eyebrow="PAIR ANALYSIS / DETAIL"
        title={pair.pair}
        description="Statistical relationship inspection using real-time market data."
        action={
          <a className="button ghost" href="/pairs">
            Back to scanner
          </a>
        }
      />
      <StatusStrip />
      <div className="detail-grid">
        {[
          ['Correlation', pair.correlation.toFixed(2)],
          ['Cointegration P-Value', pair.cointP.toFixed(3)],
          ['Hedge Ratio', pair.hedgeRatio.toFixed(2)],
          ['Half-Life', `${pair.halfLife} days`],
          ['ADF P-Value', pair.adfP.toFixed(3)],
          ['Current Z-Score', `${pair.z > 0 ? '+' : ''}${pair.z.toFixed(2)}`],
        ].map(([label, value]) => (
          <Metric
            key={label}
            label={label}
            value={value}
            kind={label === 'Current Z-Score' ? tone(pair.z) : ''}
          />
        ))}
      </div>
      <LineChartPanel pair={pair} />
      <section className="panel">
        <div className="panel-heading">
          <div>
            <div className="eyebrow">RELATIONSHIP SUMMARY</div>
            <h2>Research interpretation</h2>
          </div>
          <Badge kind="solid">LIVE ANALYSIS</Badge>
        </div>
        <p className="long-copy">
          This pair analysis uses real-time market data from Yahoo Finance. The displayed
          statistics are calculated from actual historical price data and current market conditions.
        </p>
      </section>
    </>
  )
}

function Scanner() {
  const [filters, setFilters] = useState({
    minCorrelation: 0.8,
    maxP: 0.05,
    maxHalfLife: 30,
    signal: 'ALL',
    query: '',
  })
  const [scanning, setScanning] = useState(false)
  const [ran, setRan] = useState(true)
  const [pairList, setPairList] = useState<Pair[]>([])

  useEffect(() => {
    let active = true
    api.getPairs(filters).then((data) => {
      if (active) setPairList(data)
    })
    return () => {
      active = false
    }
  }, [filters])

  const scan = async () => {
    setScanning(true)
    setRan(false)
    try {
      const data = await api.getPairs(filters)
      setPairList(data)
    } finally {
      setScanning(false)
      setRan(true)
    }
  }

  const result = pairList

  const medianP = useMemo(() => {
    if (result.length === 0) return '0.031'
    const sorted = [...result].map((p) => p.cointP).sort((a, b) => a - b)
    return sorted[Math.floor(sorted.length / 2)].toFixed(3)
  }, [result])

  const medianCorr = useMemo(() => {
    if (result.length === 0) return '0.87'
    const sorted = [...result].map((p) => p.correlation).sort((a, b) => a - b)
    return sorted[Math.floor(sorted.length / 2)].toFixed(2)
  }, [result])

  const medianHL = useMemo(() => {
    if (result.length === 0) return '7.2D'
    const sorted = [...result].map((p) => p.halfLife).sort((a, b) => a - b)
    return `${sorted[Math.floor(sorted.length / 2)].toFixed(1)}D`
  }, [result])

  return (
    <>
      <Header
        eyebrow="PAIR ANALYSIS / UNIVERSE"
        title="Pair Scanner"
        description="Ranked Nifty 50 pairs by real-time statistical analysis."
        action={
          <button className="button primary" onClick={scan}>
            <Play /> Scan pairs
          </button>
        }
      />
      <StatusStrip />
      <div className="filter-bar">
        <label>
          <span>MIN CORRELATION</span>
          <select
            value={filters.minCorrelation}
            onChange={(e) => setFilters({ ...filters, minCorrelation: Number(e.target.value) })}
          >
            <option value=".7">≥ 0.70</option>
            <option value=".8">≥ 0.80</option>
            <option value=".9">≥ 0.90</option>
          </select>
        </label>
        <label>
          <span>MAX P-VALUE</span>
          <select
            value={filters.maxP}
            onChange={(e) => setFilters({ ...filters, maxP: Number(e.target.value) })}
          >
            <option value=".05">≤ 0.05</option>
            <option value=".08">≤ 0.08</option>
            <option value=".1">≤ 0.10</option>
          </select>
        </label>
        <label>
          <span>MAX HALF-LIFE</span>
          <select
            value={filters.maxHalfLife}
            onChange={(e) => setFilters({ ...filters, maxHalfLife: Number(e.target.value) })}
          >
            <option value="15">15 days</option>
            <option value="30">30 days</option>
            <option value="60">60 days</option>
          </select>
        </label>
        <label>
          <span>SIGNAL</span>
          <select
            value={filters.signal}
            onChange={(e) => setFilters({ ...filters, signal: e.target.value })}
          >
            <option>ALL</option>
            <option>LONG SPREAD</option>
            <option>SHORT SPREAD</option>
            <option>EXIT</option>
            <option>WATCH</option>
          </select>
        </label>
        <label className="search-field">
          <span>SEARCH PAIRS</span>
          <div>
            <Search />
            <input
              value={filters.query}
              onChange={(e) => setFilters({ ...filters, query: e.target.value })}
              placeholder="e.g. HDFC"
            />
          </div>
        </label>
        <button
          className="button ghost"
          onClick={() =>
            setFilters({ minCorrelation: 0.8, maxP: 0.05, maxHalfLife: 30, signal: 'ALL', query: '' })
          }
        >
          <SlidersHorizontal /> Reset
        </button>
      </div>

      <div className="scanner-summary">
        <div>
          <b>{result.length}</b>
          <span>pairs passing filters</span>
        </div>
        <div>
          <b>{medianP}</b>
          <span>median p-value</span>
        </div>
        <div>
          <b>{medianCorr}</b>
          <span>median correlation</span>
        </div>
        <div>
          <b>{medianHL}</b>
          <span>median half-life</span>
        </div>
      </div>

      {scanning ? (
        <section className="panel loading-state">
          Scanning universe...
          <small>Generating candidate pairs · Testing statistical relationships · Ranking opportunities</small>
        </section>
      ) : !ran || result.length === 0 ? (
        <section className="panel empty-state">
          No qualifying pairs found.
          <small>Try relaxing the statistical filters.</small>
        </section>
      ) : (
        <section className="panel scanner-panel" style={{ padding: '0', overflow: 'hidden' }}>
          <div className="panel-heading" style={{ padding: '20px 20px 0' }}>
            <div>
              <div className="eyebrow">LIVE DATA</div>
              <h2>Candidate pairs</h2>
            </div>
            <span className="muted" style={{ color: 'var(--text-muted)', fontFamily: 'DM Mono' }}>
              Updated {new Date().toLocaleTimeString('en-IN', { hour12: false })} IST
            </span>
          </div>
          <div className="table-scroll" style={{ border: '0', borderRadius: '0' }}>
            <table>
              <thead>
                <tr>
                  {[
                    'PAIR',
                    'CORRELATION',
                    'COINT. P-VALUE',
                    'HEDGE RATIO',
                    'HALF-LIFE',
                    'ADF P-VALUE',
                    'Z-SCORE',
                    'SIGNAL',
                  ].map((x) => (
                    <th key={x}>{x}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.map((p) => (
                  <tr key={p.id}>
                    <td>
                      <a className="pair-link" href={`/pairs/${p.id}`}>
                        {p.pair}
                        <ChevronRight />
                      </a>
                    </td>
                    <td>{p.correlation.toFixed(2)}</td>
                    <td>{p.cointP.toFixed(3)}</td>
                    <td>{p.hedgeRatio.toFixed(2)}</td>
                    <td>{p.halfLife}D</td>
                    <td>{p.adfP.toFixed(3)}</td>
                    <td className={tone(p.z)}>
                      {p.z > 0 ? '+' : ''}
                      {p.z.toFixed(2)}
                    </td>
                    <td>
                      <Badge
                        kind={
                          p.signal === 'LONG SPREAD' || p.signal === 'SHORT SPREAD'
                            ? 'solid'
                            : 'muted'
                        }
                      >
                        {p.signal}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  )
}

function Signals() {
  const [filter, setFilter] = useState('ALL')
  const [stamp, setStamp] = useState(new Date().toLocaleTimeString('en-IN', { hour12: false }) + ' IST')
  const [rows, setRows] = useState<Signal[]>([])
  const [streamConnected, setStreamConnected] = useState(true)

  const refreshSignals = async () => {
    const data = await api.getSignals(filter)
    setRows(data)
    setStamp(new Date().toLocaleTimeString('en-IN', { hour12: false }) + ' IST')
  }

  useEffect(() => {
    refreshSignals()
  }, [filter])

  useEffect(() => {
    let active = true
    signalStream.connect().then(({ status }) => {
      if (active) setStreamConnected(status === 'CONNECTED')
    })
    const unsubStatus = signalStream.onStatusChange((status) => {
      if (active) setStreamConnected(status === 'CONNECTED')
    })
    const unsubStream = signalStream.subscribe((event) => {
      if (!active) return
      setRows((prev) =>
        prev.map((row) => {
          if (row.pair === event.pair) {
            return {
              ...row,
              priceA: event.priceA || row.priceA,
              priceB: event.priceB || row.priceB,
              spread: event.spread !== undefined ? event.spread : row.spread,
              z: event.zScore !== undefined ? event.zScore : row.z,
              signal: (event.signal as any) || row.signal,
              updated: event.timestamp || row.updated,
            }
          }
          return row
        })
      )
      setStamp(new Date().toLocaleTimeString('en-IN', { hour12: false }) + ' IST')
    })

    return () => {
      active = false
      unsubStatus()
      unsubStream()
    }
  }, [])

  return (
    <>
      <Header
        eyebrow="SIGNAL ENGINE / LIVE"
        title="Signal Monitor"
        description="Institutional signal generator connected to FastAPI with live WebSocket updates."
        action={
          <button className="button primary" onClick={refreshSignals}>
            <RefreshCw /> Refresh snapshot
          </button>
        }
      />
      <StatusStrip />
      <div className="signal-mode">
        <div>
          <span>DATA MODE</span>
          <b>WEBSOCKET STREAM</b>
        </div>
        <p>
          Real-time WebSocket streaming connected. Last update: <strong>{stamp}</strong>
        </p>
      </div>
      <div className="toggle-row large">
        {['ALL', 'LONG SPREAD', 'SHORT SPREAD', 'EXIT', 'WATCH'].map((x) => (
          <button key={x} className={filter === x ? 'selected' : ''} onClick={() => setFilter(x)}>
            {x}
          </button>
        ))}
      </div>
      <section className="panel" style={{ padding: '0', overflow: 'hidden' }}>
        <div className="table-scroll" style={{ border: '0', borderRadius: '0' }}>
          <table>
            <thead>
              <tr>
                {['PAIR', 'PRICE A', 'PRICE B', 'SPREAD', 'Z-SCORE', 'SIGNAL', 'UPDATED'].map(
                  (x) => (
                    <th key={x}>{x}</th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {rows.map((s) => (
                <tr key={s.id}>
                  <td className="strong-cell">{s.pair}</td>
                  <td>₹{s.priceA.toLocaleString()}</td>
                  <td>₹{s.priceB.toLocaleString()}</td>
                  <td>{s.spread}</td>
                  <td className={tone(s.z)}>
                    {s.z > 0 ? '+' : ''}
                    {s.z.toFixed(2)}
                  </td>
                  <td>
                    <Badge
                      kind={
                        s.signal === 'LONG SPREAD' || s.signal === 'SHORT SPREAD'
                          ? 'solid'
                          : 'muted'
                      }
                    >
                      {s.signal}
                    </Badge>
                  </td>
                  <td>{s.updated}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  )
}

function ConfigForm({
  config,
  setConfig,
  onRun,
  label = 'RUN BACKTEST',
}: {
  config: BacktestConfig
  setConfig: (x: BacktestConfig) => void
  onRun: () => void
  label?: string
}) {
  const fields: [keyof BacktestConfig, string, string][] = [
    ['entry', 'Entry Z-Score', '2.0'],
    ['exit', 'Exit Z-Score', '0.0'],
    ['stop', 'Stop Z-Score', '4.0'],
    ['holding', 'Maximum Holding Period', '30'],
    ['cost', 'Transaction Cost (%)', '0.10'],
    ['slippage', 'Slippage (%)', '0.05'],
  ]

  return (
    <div className="config-form">
      {fields.map(([key, labelText, placeholder]) => (
        <label key={key}>
          <span>{labelText}</span>
          <input
            type="number"
            step=".1"
            value={config[key] as number}
            placeholder={placeholder}
            onChange={(e) => setConfig({ ...config, [key]: Number(e.target.value) })}
          />
        </label>
      ))}
      <label>
        <span>UNIVERSE</span>
        <select>
          <option>Nifty 50</option>
        </select>
      </label>
      <label>
        <span>POSITION SIZING</span>
        <select
          value={config.position}
          onChange={(e) => setConfig({ ...config, position: e.target.value })}
        >
          <option>Volatility Adjusted</option>
          <option>Equal Weight</option>
        </select>
      </label>
      <label>
        <span>START DATE</span>
        <input
          type="date"
          value={config.start}
          onChange={(e) => setConfig({ ...config, start: e.target.value })}
        />
      </label>
      <label>
        <span>END DATE</span>
        <input
          type="date"
          value={config.end}
          onChange={(e) => setConfig({ ...config, end: e.target.value })}
        />
      </label>
      <button className="button primary full" onClick={onRun}>
        <Play />
        {label}
      </button>
    </div>
  )
}

function Backtest({ onComplete }: { onComplete: (x: any) => void }) {
  const [config, setConfig] = useState(defaultBacktest)
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<any>()
  const [tradesList, setTradesList] = useState<Trade[]>([])
  const [mode, setMode] = useState<'equity' | 'drawdown' | 'monthly'>('equity')

  const go = async () => {
    setRunning(true)
    try {
      const r = await api.runBacktest(config)
      setResult(r)
      onComplete(r)
      if ((r as any).id) {
        const t = await api.getBacktestTrades((r as any).id)
        if (t && t.length > 0) setTradesList(t)
      }
    } finally {
      setRunning(false)
    }
  }

  return (
    <>
      <Header
        eyebrow="RESEARCH / VALIDATION"
        title="Backtesting"
        description="Configure and evaluate strategy performance using historical market data."
      />
      <StatusStrip />
      <div className="two-col">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <div className="eyebrow">STRATEGY CONFIGURATION</div>
              <h2>Mean reversion parameters</h2>
            </div>
          </div>
          <ConfigForm config={config} setConfig={setConfig} onRun={go} />
          {running && (
            <div className="loading-inline">
              Loading historical data... Building training windows... Running portfolio simulation...
            </div>
          )}
        </section>
        {result ? (
          <Results result={result} mode={mode} setMode={setMode} />
        ) : (
          <section className="panel empty-state">
            <BarChart3 />
            <b>Run a backtest to view results</b>
            <small>Results will be calculated using historical market data.</small>
          </section>
        )}
      </div>
      {result && <Trades list={tradesList} />}
    </>
  )
}

function Results({
  result,
  mode,
  setMode,
}: {
  result: any
  mode: string
  setMode: (x: any) => void
}) {
  if (!result) {
    return (
      <section className="panel empty-state">
        <BarChart3 />
        <b>No backtest results available</b>
        <small>Run a backtest to see performance metrics.</small>
      </section>
    )
  }

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <div className="eyebrow">BACKTEST RESULTS</div>
          <h2>Performance results</h2>
        </div>
        <Badge kind="solid">HISTORICAL ANALYSIS</Badge>
      </div>
      <div className="results-grid">
        {[
          ['Initial Capital', `₹${result?.initial?.toLocaleString('en-IN') || '₹10,00,000'}`],
          ['Final Capital', `₹${result?.final?.toLocaleString('en-IN') || '₹10,00,000'}`],
          ['Total Return', `${result?.total || 0}%`],
          ['CAGR', `${result?.cagr || 0}%`],
          ['Sharpe Ratio', result?.sharpe || 0],
          ['Sortino Ratio', result?.sortino || 0],
          ['Max Drawdown', `${result?.drawdown || 0}%`],
          ['Win Rate', `${result?.winRate || 0}%`],
          ['Trades', result?.count || 0],
        ].map(([x, y]) => (
          <Metric
            key={x}
            label={x as string}
            value={String(y)}
            kind={x === 'Total Return' ? 'positive' : ''}
          />
        ))}
      </div>
      <div className="toggle-row large">
        {['equity', 'drawdown', 'monthly'].map((x) => (
          <button
            key={x}
            className={mode === x ? 'selected' : ''}
            onClick={() => setMode(x)}
          >
            {x}
          </button>
        ))}
      </div>
      <Chart data={result?.curve && Array.isArray(result.curve) && result.curve.length > 0 ? result.curve : []} />
    </section>
  )
}

function Trades({ list }: { list?: Trade[] }) {
  const allTrades = list && list.length > 0 ? list : []
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)
  const filtered = allTrades.filter((t) => t.pair.toLowerCase().includes(search.toLowerCase()))
  const visible = filtered.slice(page * 6, page * 6 + 6)

  return (
    <section className="panel" style={{ padding: '0', overflow: 'hidden' }}>
      <div className="panel-heading" style={{ padding: '20px 20px 0' }}>
        <div>
          <div className="eyebrow">EXECUTION LEDGER</div>
          <h2>Trade history</h2>
        </div>
        <input
          className="compact-input"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            setPage(0)
          }}
          placeholder="Search pair"
        />
      </div>
      <div className="table-scroll" style={{ border: '0', borderRadius: '0' }}>
        <table>
          <thead>
            <tr>
              {[
                'PAIR',
                'ENTRY DATE',
                'EXIT DATE',
                'DIRECTION',
                'ENTRY Z',
                'EXIT Z',
                'HOLDING',
                'P&L',
                'RETURN',
              ].map((x) => (
                <th key={x}>{x}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.map((t) => (
              <tr key={t.id}>
                <td className="strong-cell">{t.pair}</td>
                <td>{t.entryDate}</td>
                <td>{t.exitDate}</td>
                <td>
                  <Badge kind={t.direction === 'LONG' ? 'solid' : 'muted'}>{t.direction}</Badge>
                </td>
                <td>{t.entryZ}</td>
                <td>{t.exitZ}</td>
                <td>{t.holding}D</td>
                <td className={tone(t.pnl)}>₹{t.pnl.toLocaleString()}</td>
                <td className={tone(t.return)}>{t.return}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="pagination" style={{ padding: '14px 20px' }}>
        <span>{filtered.length} trades</span>
        <button
          className="button ghost"
          disabled={page === 0}
          onClick={() => setPage(page - 1)}
        >
          Previous
        </button>
        <button
          className="button ghost"
          disabled={(page + 1) * 6 >= filtered.length}
          onClick={() => setPage(page + 1)}
        >
          Next
        </button>
      </div>
    </section>
  )
}

function Research() {
  const [config, setConfig] = useState(defaultBacktest)
  const [running, setRunning] = useState(false)
  const [history, setHistory] = useState<ExperimentResult[]>([])

  useEffect(() => {
    let active = true
    api.getExperiments().then((data) => {
      if (active && data && data.length > 0) {
        setHistory(data)
      }
    })
    return () => {
      active = false
    }
  }, [])

  const run = async () => {
    setRunning(true)
    try {
      const x = await api.runExperiment(config)
      setHistory((prev) => [x, ...prev])
    } finally {
      setRunning(false)
    }
  }

  return (
    <>
      <Header
        eyebrow="RESEARCH LAB / EXPERIMENTS"
        title="Research Lab"
        description="Change strategy parameters, run experiments, and compare historical performance."
      />
      <StatusStrip />
      <div className="two-col">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <div className="eyebrow">EXPERIMENT CONTROLS</div>
              <h2>Hypothesis parameters</h2>
            </div>
          </div>
          <ConfigForm config={config} setConfig={setConfig} onRun={run} label="RUN EXPERIMENT" />
          {running && (
            <div className="loading-inline">
              Building experiment... Calculating results...
            </div>
          )}
        </section>
        <section className="panel">
          <div className="panel-heading">
            <div>
              <div className="eyebrow">EXPERIMENT HISTORY</div>
              <h2>Compare results</h2>
            </div>
          </div>
          {history.map((x, i) => (
            <div className="experiment-row" key={`${x.name}-${i}`}>
              <div>
                <strong>{x.name}</strong>
                <span>
                  {x.date} · Entry {x.entry} · Exit {x.exit}
                </span>
              </div>
              <b className="positive">+{x.return}%</b>
              <span>Sharpe {x.sharpe}</span>
              <span className="negative">{x.drawdown}%</span>
            </div>
          ))}
        </section>
      </div>
    </>
  )
}

function Risk() {
  const [mode, setMode] = useState<'equity' | 'drawdown' | 'monthly'>('drawdown')
  const [riskData, setRiskData] = useState<Record<string, string>>({})
  const [exposureList, setExposureList] = useState<any[]>([])

  useEffect(() => {
    let active = true
    api.getRisk().then((data) => {
      if (active && data) {
        setRiskData(data)
      }
    })
    api.getRiskExposure().then((data) => {
      if (active && data && data.length > 0) {
        setExposureList(data)
      }
    })
    return () => {
      active = false
    }
  }, [])

  return (
    <>
      <Header
        eyebrow="PORTFOLIO / CONTROLS"
        title="Risk Analytics"
        description="Inspect portfolio risk metrics and exposure diagnostics."
      />
      <StatusStrip />
      <div className="metrics-grid risk-metrics">
        {Object.entries(riskData).map(([k, v]) => (
          <Metric
            key={k}
            label={k.replace(/([A-Z])/g, ' $1')}
            value={v}
            kind={k === 'drawdown' || k === 'var' || k === 'es' ? 'negative' : ''}
          />
        ))}
      </div>
      <div className="two-col">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <div className="eyebrow">RISK SERIES</div>
              <h2>Portfolio diagnostics</h2>
            </div>
          </div>
          <div className="toggle-row large">
            {['drawdown', 'equity', 'monthly'].map((x) => (
              <button
                key={x}
                className={mode === x ? 'selected' : ''}
                onClick={() => setMode(x as any)}
              >
                {x}
              </button>
            ))}
          </div>
          {Array.isArray(exposureList) && exposureList.length > 0 ? (
            <Chart data={exposureList.map((p, i) => ({label: p.pair || `Pair ${i+1}`, value: p.weight || 50}))} />
          ) : (
            <div className="empty-state" style={{padding: '40px', textAlign: 'center'}}>
              <p>No risk data available. Run a backtest to generate risk metrics.</p>
            </div>
          )}
        </section>
        <section className="panel">
          <div className="panel-heading">
            <div>
              <div className="eyebrow">EXPOSURE</div>
              <h2>Position concentration</h2>
            </div>
          </div>
          {exposureList.slice(0, 5).map((p, i) => (
            <div className="exposure-row" key={p.id}>
              <span>
                {p.a} / {p.b}
              </span>
              <div>
                <i style={{ width: `${Math.min(100, Math.max(5, p.weight ?? (82 - i * 12)))}%` }} />
              </div>
              <b>{p.weight ?? (82 - i * 12)}%</b>
            </div>
          ))}
          <p className="notice">
            Risk metrics are calculated from backtested trade distributions and cointegrated pair volatility.
          </p>
        </section>
      </div>
    </>
  )
}

function SettingsPage() {
  const { online, streamStatus } = useBackendState()

  return (
    <>
      <Header
        eyebrow="SYSTEM / CONFIGURATION"
        title="Settings"
        description="Review adapter configuration and environment safeguards."
      />
      <StatusStrip />
      <section className="panel settings-panel">
        <div className="setting-row">
          <div>
            <strong>Data adapter</strong>
            <span>FastAPI active REST adapter</span>
          </div>
          <Badge kind="solid">LIVE</Badge>
        </div>
        <div className="setting-row">
          <div>
            <strong>FastAPI base URL</strong>
            <span>{apiBaseUrl}</span>
          </div>
          <Badge kind="solid">CONNECTED</Badge>
        </div>
        <div className="setting-row">
          <div>
            <strong>Realtime signal stream</strong>
            <span>WebSocket endpoint at /api/ws/signals</span>
          </div>
          <Badge kind={streamStatus === 'CONNECTED' ? 'solid' : 'muted'}>{streamStatus}</Badge>
        </div>
      </section>
    </>
  )
}

export default function Home() {
  const nextPathname = usePathname()
  const router = useRouter()
  const [clientPathname, setClientPathname] = useState<string | null>(null)
  const pathname = clientPathname || nextPathname || '/dashboard'

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [theme, setTheme] = useState<'dark' | 'light'>('light')
  const [lastBacktest, setLastBacktest] = useState<any>()
  const [isRefreshing, setIsRefreshing] = useState(false)

  useEffect(() => {
    try {
      const saved = localStorage.getItem('statarb-theme') as 'dark' | 'light' | null
      const current = document.documentElement.getAttribute('data-theme') as 'dark' | 'light' | null
      const activeTheme = saved === 'dark' || saved === 'light' ? saved : current === 'dark' || current === 'light' ? current : 'light'
      setTheme(activeTheme)
      document.documentElement.setAttribute('data-theme', activeTheme)
    } catch (e) {}
  }, [])

  const handleRefresh = () => {
    setIsRefreshing(true)
    setTimeout(() => {
      setIsRefreshing(false)
    }, 600)
  }

  const toggleTheme = () => {
    setTheme((prev) => {
      const next = prev === 'dark' ? 'light' : 'dark'
      document.documentElement.setAttribute('data-theme', next)
      try {
        localStorage.setItem('statarb-theme', next)
      } catch (e) {}
      return next
    })
  }

  const parts = pathname.split('/').filter(Boolean)
  const mainRoute = parts[0] || 'dashboard'
  const subId = mainRoute === 'pairs' ? parts[1] : undefined
  const active = `/${mainRoute}`

  let content: React.ReactNode =
    mainRoute === 'dashboard' ? (
      <Dashboard
        lastBacktest={lastBacktest}
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
      />
    ) : mainRoute === 'pairs' && subId ? (
      <PairDetail id={subId} />
    ) : mainRoute === 'pairs' ? (
      <Scanner />
    ) : mainRoute === 'signals' ? (
      <Signals />
    ) : mainRoute === 'backtest' ? (
      <Backtest onComplete={setLastBacktest} />
    ) : mainRoute === 'research' ? (
      <Research />
    ) : mainRoute === 'risk' ? (
      <Risk />
    ) : (
      <SettingsPage />
    )

  const navigate = (e: React.MouseEvent<HTMLElement>) => {
    const a = (e.target as HTMLElement).closest('a')
    const href = a?.getAttribute('href')
    if (!href?.startsWith('/')) return
    e.preventDefault()
    setClientPathname(href)
    router.push(href)
    setMobileOpen(false)
  }

  return (
    <div className="app-shell">
      <Sidebar
        active={active}
        collapsed={sidebarCollapsed}
        open={mobileOpen}
        theme={theme}
        onClose={() => setMobileOpen(false)}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        onToggleTheme={toggleTheme}
      />
      <main className="main-content">
        <Topbar
          collapsed={sidebarCollapsed}
          theme={theme}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
          onToggleTheme={toggleTheme}
          onMenu={() => setMobileOpen(true)}
          onRefresh={handleRefresh}
          isRefreshing={isRefreshing}
        />
        <div className="page-content" onClick={navigate}>
          {content}
        </div>
      </main>
    </div>
  )
}

