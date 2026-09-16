'use client'

import { useMemo, useState } from 'react'
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  Bell,
  BrainCircuit,
  ChevronRight,
  CircleHelp,
  Database,
  FlaskConical,
  Gauge,
  LayoutDashboard,
  LineChart,
  Menu,
  Play,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  TrendingDown,
  TrendingUp,
  X,
} from 'lucide-react'

const nav = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/pairs', label: 'Pair Scanner', icon: Search },
  { href: '/signals', label: 'Live Signals', icon: Activity },
  { href: '/backtest', label: 'Backtesting', icon: LineChart },
  { href: '/research', label: 'Research Lab', icon: FlaskConical },
  { href: '/risk', label: 'Risk Analytics', icon: ShieldCheck },
]

const pairs = [
  { pair: 'HDFCBANK / ICICIBANK', sector: 'Financials', z: '+2.31', p: '0.014', half: '5.3D', signal: 'SHORT SPREAD', strength: 'Strong', beta: '0.82', ret: '+1.8%' },
  { pair: 'RELIANCE / ONGC', sector: 'Energy', z: '-2.08', p: '0.022', half: '8.1D', signal: 'LONG SPREAD', strength: 'Strong', beta: '1.14', ret: '+2.4%' },
  { pair: 'INFY / TCS', sector: 'Technology', z: '+1.84', p: '0.031', half: '11.7D', signal: 'WATCH', strength: 'Moderate', beta: '0.96', ret: '+0.6%' },
  { pair: 'SBIN / AXISBANK', sector: 'Financials', z: '-1.62', p: '0.048', half: '6.8D', signal: 'WATCH', strength: 'Moderate', beta: '1.08', ret: '-0.3%' },
  { pair: 'MARUTI / TATAMOTORS', sector: 'Auto', z: '+1.42', p: '0.057', half: '14.2D', signal: 'EXIT', strength: 'Weak', beta: '0.74', ret: '+0.9%' },
]

const trades = [
  ['HDFCBANK / ICICIBANK', '12 Sep', '16 Sep', 'SHORT', '3D', '+₹4,280', 'Closed'],
  ['RELIANCE / ONGC', '11 Sep', '—', 'LONG', '5D', '+₹2,910', 'Open'],
  ['INFY / TCS', '09 Sep', '13 Sep', 'SHORT', '4D', '+₹1,231', 'Closed'],
  ['SBIN / AXISBANK', '06 Sep', '—', 'LONG', '8D', '-₹842', 'Open'],
]

function Sparkline({ tone = 'cyan', down = false }: { tone?: 'cyan' | 'green' | 'red'; down?: boolean }) {
  const points = down ? '0,12 16,8 31,14 49,5 64,10 82,4 100,11' : '0,16 15,13 29,15 43,7 58,11 73,3 87,7 100,1'
  return <svg viewBox="0 0 100 20" className={`sparkline ${tone}`} aria-hidden="true"><polyline points={points} fill="none" stroke="currentColor" strokeWidth="1.6" vectorEffect="non-scaling-stroke" /></svg>
}

function Chart() {
  return <div className="chart-wrap">
    <div className="chart-y-labels"><span>₹10.5L</span><span>₹10.3L</span><span>₹10.1L</span><span>₹9.9L</span></div>
    <svg viewBox="0 0 760 220" preserveAspectRatio="none" className="main-chart" role="img" aria-label="Portfolio equity curve rising from nine point nine lakh to ten point four lakh">
      <defs><linearGradient id="area" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#32c5c9" stopOpacity=".18" /><stop offset="1" stopColor="#32c5c9" stopOpacity="0" /></linearGradient></defs>
      {[25, 75, 125, 175].map((y) => <line key={y} x1="0" y1={y} x2="760" y2={y} stroke="currentColor" opacity=".1" />)}
      <path d="M0 181 L42 168 L83 175 L126 143 L166 152 L205 112 L247 129 L289 104 L330 118 L371 86 L413 92 L456 69 L495 83 L536 45 L580 60 L620 33 L660 47 L710 23 L760 32 L760 220 L0 220Z" fill="url(#area)" />
      <path d="M0 181 L42 168 L83 175 L126 143 L166 152 L205 112 L247 129 L289 104 L330 118 L371 86 L413 92 L456 69 L495 83 L536 45 L580 60 L620 33 L660 47 L710 23 L760 32" fill="none" stroke="#42d1d2" strokeWidth="2" vectorEffect="non-scaling-stroke" />
      <circle cx="710" cy="23" r="4" fill="#42d1d2" />
    </svg>
    <div className="chart-x-labels"><span>01 Sep</span><span>05 Sep</span><span>09 Sep</span><span>13 Sep</span><span>16 Sep</span></div>
  </div>
}

function Metric({ label, value, change, tone = 'cyan', spark = false }: { label: string; value: string; change?: string; tone?: 'cyan' | 'green' | 'red'; spark?: boolean }) {
  return <article className="metric-card"><div className="metric-label">{label}</div><div className={`metric-value ${tone}`}>{value}</div>{change && <div className={`metric-change ${tone}`}>{change}</div>}{spark && <Sparkline tone={tone} down={tone === 'red'} />}</article>
}

function Badge({ children, tone = 'muted' }: { children: React.ReactNode; tone?: 'green' | 'red' | 'amber' | 'cyan' | 'muted' }) { return <span className={`badge ${tone}`}>{children}</span> }

function Sidebar({ active, open, onClose }: { active: string; open: boolean; onClose: () => void }) {
  return <aside className={`sidebar ${open ? 'is-open' : ''}`}><div className="brand"><div className="brand-mark">S<span>/</span>N</div><div><div className="brand-name">STATARB <b>N50</b></div><div className="brand-sub">QUANT RESEARCH TERMINAL</div></div><button className="icon-button mobile-close" onClick={onClose} aria-label="Close navigation"><X /></button></div><div className="sidebar-section"><div className="eyebrow">WORKSPACE</div>{nav.map(({ href, label, icon: Icon }) => <a key={href} href={href} className={`nav-item ${active === href ? 'active' : ''}`} onClick={onClose}><Icon /><span>{label}</span>{active === href && <ChevronRight className="nav-chevron" />}</a>)}</div><div className="sidebar-section secondary"><div className="eyebrow">SYSTEM</div><a href="/settings" className={`nav-item ${active === '/settings' ? 'active' : ''}`} onClick={onClose}><Settings /><span>Settings</span></a><a href="#status" className="nav-item"><CircleHelp /><span>System Status</span></a></div><div className="connection"><div className="eyebrow">DATA CONNECTION</div><div className="connection-state"><span className="live-dot" /> LIVE <span className="connection-time">13:42:08 IST</span></div><div className="connection-meta"><Database /> Market data streaming</div></div></aside>
}

function Topbar({ onMenu }: { onMenu: () => void }) { return <header className="topbar"><button className="icon-button menu-button" onClick={onMenu} aria-label="Open navigation"><Menu /></button><div className="breadcrumb"><span>RESEARCH WORKSPACE</span><ChevronRight /><strong>Overview</strong></div><div className="top-actions"><div className="market-pill"><span className="live-dot" /> NSE <b>OPEN</b></div><button className="icon-button" aria-label="Refresh data"><RefreshCw /></button><button className="icon-button has-notification" aria-label="Notifications"><Bell /><i /></button><div className="avatar">RK</div></div></header> }

function PageHeader({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: React.ReactNode }) { return <div className="page-header"><div><div className="eyebrow accent">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>{action}</div> }

function Dashboard() { return <><PageHeader eyebrow="STATARB N50 / OVERVIEW" title="Nifty 50 Statistical Arbitrage" description="Monitor cointegration opportunities, portfolio performance, and execution health." action={<button className="button primary"><RefreshCw /> Refresh analysis</button>} /><div className="status-strip"><div><span>MARKET STATUS</span><Badge tone="green">OPEN</Badge></div><div><span>DATA STATUS</span><Badge tone="cyan">CONNECTED</Badge></div><div><span>LAST UPDATE</span><b>13:42:08 IST</b></div><div className="status-note"><Activity /> Engines operational</div></div><section className="metrics-grid"><Metric label="Capital" value="₹10,00,000" change="Initial allocation" /><Metric label="Portfolio Value" value="₹10,42,381" change="+4.24% all time" tone="green" spark /><Metric label="Today's P&L" value="+₹8,421" change="+0.81% today" tone="green" spark /><Metric label="Active Pairs" value="4" change="2 signals pending" /><Metric label="Win Rate" value="57.4%" change="Last 90 days" tone="cyan" /><Metric label="Sharpe Ratio" value="1.31" change="Rolling 1 year" tone="cyan" /></section><div className="dashboard-grid"><section className="panel chart-panel"><div className="panel-heading"><div><div className="eyebrow">PERFORMANCE</div><h2>Portfolio equity curve</h2></div><div className="legend"><span><i className="legend-line equity" /> Portfolio</span><span><i className="legend-line benchmark" /> NIFTY 50</span></div></div><div className="chart-stat"><span>₹10,42,381</span><b>+4.24%</b><small>vs. ₹10,00,000 initial capital</small></div><Chart /></section><section className="panel opportunities"><div className="panel-heading"><div><div className="eyebrow">SIGNAL MONITOR</div><h2>Active opportunities</h2></div><a className="text-link" href="/pairs">View scanner <ArrowUpRight /></a></div><div className="opportunity-list">{pairs.slice(0, 4).map((p) => <a href="/pairs/hdfcbank-icicibank" className="opportunity" key={p.pair}><div><strong>{p.pair}</strong><span>{p.sector}</span></div><div className={`z-score ${p.z.startsWith('-') ? 'negative' : ''}`}>{p.z}</div><div className="opp-signal"><Badge tone={p.signal.includes('SHORT') ? 'red' : p.signal.includes('LONG') ? 'green' : 'amber'}>{p.signal}</Badge><span>p {p.p}</span></div></a>)}</div></section></div><section className="panel"><div className="panel-heading"><div><div className="eyebrow">EXECUTION LOG</div><h2>Recent trades</h2></div><a className="text-link" href="/signals">All activity <ArrowUpRight /></a></div><TradeTable /></section><section className="panel health-panel"><div className="panel-heading"><div><div className="eyebrow">INFRASTRUCTURE</div><h2>System health</h2></div><Badge tone="green">ALL SYSTEMS NOMINAL</Badge></div><div className="health-grid">{[['Market Data','CONNECTED'],['Quant Engine','RUNNING'],['Signal Engine','RUNNING'],['Database','CONNECTED'],['Last Calculation','13:42:08']].map(([a,b]) => <div className="health-item" key={a}><span>{a}</span><strong><i className="live-dot" />{b}</strong></div>)}</div></section></> }

function TradeTable() { return <div className="table-scroll"><table><thead><tr>{['PAIR','ENTRY','EXIT','DIRECTION','HOLDING','P&L','STATUS'].map((x) => <th key={x}>{x}</th>)}</tr></thead><tbody>{trades.map((t) => <tr key={t[0]}><td className="strong-cell">{t[0]}</td><td>{t[1]}</td><td>{t[2]}</td><td><Badge tone={t[3] === 'LONG' ? 'green' : 'red'}>{t[3]}</Badge></td><td>{t[4]}</td><td className={t[5].startsWith('+') ? 'positive' : 'negative'}>{t[5]}</td><td><Badge tone={t[6] === 'Open' ? 'cyan' : 'muted'}>{t[6]}</Badge></td></tr>)}</tbody></table></div> }

function Scanner() { const [query, setQuery] = useState(''); const filtered = useMemo(() => pairs.filter((p) => p.pair.toLowerCase().includes(query.toLowerCase())), [query]); return <><PageHeader eyebrow="PAIR ANALYSIS / UNIVERSE" title="Pair Scanner" description="Ranked Nifty 50 equity pairs by cointegration strength and mean-reversion quality." action={<button className="button primary"><Play /> Run scan</button>} /><div className="filter-bar"><label><span>UNIVERSE</span><select><option>NIFTY 50</option><option>NIFTY 100</option></select></label><label><span>LOOKBACK</span><select><option>252 trading days</option><option>504 trading days</option></select></label><label><span>MIN. CORRELATION</span><select><option>0.70</option><option>0.80</option></select></label><label className="search-field"><span>SEARCH PAIRS</span><div><Search /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="e.g. HDFC" /></div></label><button className="button ghost"><SlidersHorizontal /> Filters</button></div><div className="scanner-summary"><div><b>{filtered.length}</b><span>pairs passing filters</span></div><div><b>0.031</b><span>median p-value</span></div><div><b>0.87</b><span>median correlation</span></div><div><b>7.2D</b><span>median half-life</span></div></div><section className="panel scanner-panel"><div className="panel-heading"><div><div className="eyebrow">COINTEGRATION RANKING</div><h2>Candidate pairs</h2></div><div className="table-actions"><span className="muted">Updated 13:42 IST</span><button className="icon-button"><RefreshCw /></button></div></div><div className="table-scroll"><table><thead><tr>{['PAIR','SECTOR','Z-SCORE','P-VALUE','HALF-LIFE','SIGNAL','STRENGTH','BETA','1D RETURN'].map((x) => <th key={x}>{x}</th>)}</tr></thead><tbody>{filtered.map((p) => <tr key={p.pair}><td><a href="/pairs/hdfcbank-icicibank" className="pair-link">{p.pair}<ChevronRight /></a></td><td>{p.sector}</td><td className={p.z.startsWith('-') ? 'negative strong-cell' : 'positive strong-cell'}>{p.z}</td><td>{p.p}</td><td>{p.half}</td><td><Badge tone={p.signal.includes('SHORT') ? 'red' : p.signal.includes('LONG') ? 'green' : p.signal === 'EXIT' ? 'cyan' : 'amber'}>{p.signal}</Badge></td><td><span className="strength"><i style={{ width: p.strength === 'Strong' ? '84%' : p.strength === 'Moderate' ? '58%' : '31%' }} />{p.strength}</span></td><td>{p.beta}</td><td className={p.ret.startsWith('+') ? 'positive' : 'negative'}>{p.ret}</td></tr>)}</tbody></table></div></section></> }

function GenericPage({ type }: { type: string }) { const config: Record<string, [string,string,string]> = { signals: ['SIGNAL ENGINE / LIVE','Live Signals','Real-time entry, exit, and watch signals from the active mean-reversion engine.'], backtest: ['RESEARCH / VALIDATION','Backtesting','Evaluate strategy performance across historical Nifty 50 market regimes.'], research: ['RESEARCH LAB / EXPERIMENTS','Research Lab','Build, compare, and validate statistical arbitrage hypotheses.'], risk: ['PORTFOLIO / CONTROLS','Risk Analytics','Monitor exposure, concentration, drawdown, and position-level risk.'], settings: ['SYSTEM / CONFIGURATION','Settings','Configure research defaults, execution safeguards, and data connections.'] }; const [ey,title,desc] = config[type] || config.research; const ModuleIcon = type === 'risk' ? ShieldCheck : type === 'backtest' ? LineChart : FlaskConical; return <><PageHeader eyebrow={ey} title={title} description={desc} action={<button className="button primary"><RefreshCw /> Refresh view</button>} /><div className="placeholder-grid"><section className="panel hero-panel"><div className="hero-icon"><ModuleIcon /></div><div className="eyebrow accent">MODULE READY</div><h2>{title} workspace</h2><p>The frontend surface is ready for the quantitative backend adapter. Connect the corresponding FastAPI service to replace the isolated mock responses without changing this workflow.</p><div className="module-stats"><div><b>04</b><span>active datasets</span></div><div><b>12</b><span>saved analyses</span></div><div><b>99.8%</b><span>data coverage</span></div></div></section><section className="panel"><div className="panel-heading"><div><div className="eyebrow">RECENT ACTIVITY</div><h2>Research log</h2></div><Badge tone="cyan">MOCK ADAPTER</Badge></div>{['Daily universe refresh completed','Cointegration scan finished · 126 pairs','Risk limits validated','Signal engine heartbeat received'].map((x,i) => <div className="log-row" key={x}><span className="log-time">13:{42-i*4}:0{i}</span><span>{x}</span><Badge tone={i === 2 ? 'green' : 'muted'}>{i === 2 ? 'PASS' : 'DONE'}</Badge></div>)}</section></div></> }

export default function Home() { const [pathname, setPathname] = useState(typeof window !== 'undefined' ? window.location.pathname : '/dashboard'); const [mobileOpen, setMobileOpen] = useState(false); const route = pathname.split('/')[1] || 'dashboard'; const active = `/${route}`; const content = route === 'dashboard' ? <Dashboard /> : route === 'pairs' ? <Scanner /> : <GenericPage type={route} />; const navigate = (e: React.MouseEvent<HTMLElement>) => { const target = (e.target as HTMLElement).closest('a'); const href = target?.getAttribute('href'); if (!href?.startsWith('/')) return; e.preventDefault(); window.history.pushState({}, '', href); setPathname(href); setMobileOpen(false); }; return <div className="app-shell"><Sidebar active={active} open={mobileOpen} onClose={() => setMobileOpen(false)} /><main className="main-content"><Topbar onMenu={() => setMobileOpen(true)} /><div className="page-content" onClick={navigate}>{content}</div></main></div> }

function _unused() { return <><ArrowDownRight /><Gauge /><BarChart3 /><BrainCircuit /><Sparkles /><TrendingDown /><TrendingUp /></> }

type ReactNode = React.ReactNode
