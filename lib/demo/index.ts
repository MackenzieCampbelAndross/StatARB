export type PairSignal = 'LONG SPREAD' | 'SHORT SPREAD' | 'EXIT' | 'WATCH'
export type Range = '1D' | '1W' | '1M' | '3M' | '6M' | '1Y'
export type Pair = { id: string; pair: string; a: string; b: string; sector: string; correlation: number; cointP: number; hedgeRatio: number; halfLife: number; adfP: number; z: number; signal: PairSignal }
export type Signal = Pair & { priceA: number; priceB: number; spread: number; updated: string }
export type BacktestConfig = { entry: number; exit: number; stop: number; holding: number; cost: number; slippage: number; position: string; start: string; end: string }
export type Trade = { id: number; pair: string; entryDate: string; exitDate: string; direction: 'LONG' | 'SHORT'; entryZ: number; exitZ: number; holding: number; pnl: number; return: number }

export const pairs: Pair[] = [
 { id:'hdfcbank-icicibank', pair:'HDFCBANK / ICICIBANK', a:'HDFCBANK', b:'ICICIBANK', sector:'Financials', correlation:.89, cointP:.014, hedgeRatio:1.12, halfLife:5.3, adfP:.021, z:2.31, signal:'SHORT SPREAD' },
 { id:'axisbank-sbin', pair:'AXISBANK / SBIN', a:'AXISBANK', b:'SBIN', sector:'Financials', correlation:.84, cointP:.032, hedgeRatio:.86, halfLife:6.8, adfP:.041, z:-1.62, signal:'WATCH' },
 { id:'reliance-ongc', pair:'RELIANCE / ONGC', a:'RELIANCE', b:'ONGC', sector:'Energy', correlation:.87, cointP:.022, hedgeRatio:1.14, halfLife:8.1, adfP:.029, z:-2.08, signal:'LONG SPREAD' },
 { id:'infy-tcs', pair:'INFY / TCS', a:'INFY', b:'TCS', sector:'Technology', correlation:.91, cointP:.031, hedgeRatio:.96, halfLife:11.7, adfP:.038, z:1.84, signal:'WATCH' },
 { id:'hindunilvr-itc', pair:'HINDUNILVR / ITC', a:'HINDUNILVR', b:'ITC', sector:'Consumer', correlation:.82, cointP:.047, hedgeRatio:.73, halfLife:18.4, adfP:.052, z:.74, signal:'WATCH' },
 { id:'lt-adaniports', pair:'LT / ADANIPORTS', a:'LT', b:'ADANIPORTS', sector:'Industrials', correlation:.79, cointP:.061, hedgeRatio:1.31, halfLife:27.2, adfP:.068, z:-.42, signal:'EXIT' },
]

export const getPairs = (filters?: { minCorrelation:number; maxP:number; maxHalfLife:number; signal:string; query?:string }) => pairs.filter(p => !filters || (p.correlation >= filters.minCorrelation && p.cointP <= filters.maxP && p.halfLife <= filters.maxHalfLife && (filters.signal === 'ALL' || p.signal === filters.signal) && (!filters.query || p.pair.toLowerCase().includes(filters.query.toLowerCase()))))
export const getPair = (id:string) => pairs.find(p => p.id === id) ?? pairs[0]
export const series = (pair:Pair, range:Range, mode:'spread'|'price'='spread') => { const count = range==='1D'?24:range==='1W'?28:range==='1M'?30:range==='3M'?36:range==='6M'?42:48; return Array.from({length:count}, (_,i) => { const wave = Math.sin(i*.7 + pair.z) * .52 + Math.cos(i*.19) * .24; const z = pair.z * .72 + wave; const base = 100 + i*.12 + Math.sin(i*.2)*.7; return { label:`${String((i%28)+1).padStart(2,'0')} Sep`, spread:Number(z.toFixed(2)), mean:0, upper1:1, lower1:-1, upper2:2, lower2:-2, a:Number((base + wave*.8).toFixed(2)), b:Number((base - wave*.65).toFixed(2)), entry:i===8||i===29?z:undefined, exit:i===16||i===37?z:undefined } }) }
export const getSignals = () => pairs.map((p,i) => ({...p, priceA:[1732.4,1124.8,2941.2,1812.6,2640.1,3567.4][i], priceB:[823.7,812.2,241.8,3890.5,468.2,1245.9][i], spread:Number((p.z*.38).toFixed(2)), updated:'13:42:08 IST'}))
export const defaultBacktest:BacktestConfig = { entry:2, exit:0, stop:4, holding:30, cost:.1, slippage:.05, position:'Volatility Adjusted', start:'2020-01-01', end:'2025-12-31' }
export const trades:Trade[] = Array.from({length:18},(_,i)=>({id:i+1,pair:pairs[i%pairs.length].pair,entryDate:`${String((i%26)+1).padStart(2,'0')} ${i%2?'Mar':'Sep'} 202${i%5}`,exitDate:`${String((i%26)+4).padStart(2,'0')} ${i%2?'Mar':'Sep'} 202${i%5}`,direction:i%2?'LONG':'SHORT',entryZ:i%2? -2.1:2.3,exitZ:i%3===0?.12:-.08,holding:3+(i%18),pnl:Math.round((i%2?1:-1)*(-1)**(i%5)* (1200+i*173)),return:Number((((i%2?1:-1)*(-1)**(i%5)*(.7+i*.09)).toFixed(2)))}))
export const backtestResult = (config:BacktestConfig) => ({ initial:1000000, final:1184200 + Math.round((config.entry-2)*12000), total:18.42, cagr:3.43, sharpe:1.31, sortino:1.84, drawdown:-8.21, winRate:57.4, profitFactor:1.64, count:143 })
export const curve = (mode:'equity'|'drawdown'|'monthly') => Array.from({length:36},(_,i)=>({label:`${String((i%12)+1).padStart(2,'0')}/${2023+Math.floor(i/12)}`, value:mode==='equity'?1000000+i*5100+Math.sin(i)*9000:mode==='drawdown'?-Math.abs(Math.sin(i*.37)*8.2):Math.sin(i*.6)*3.2}))
export const risk = { volatility:'12.84%', sharpe:'1.31', sortino:'1.84', drawdown:'-8.21%', var:'-₹18,420', es:'-₹26,180', gross:'₹6,42,800', net:'₹84,200', turnover:'2.31x' }
export const experiments = [{name:'Baseline mean reversion',date:'16 Sep 2026',entry:2,exit:0,return:18.42,sharpe:1.31,drawdown:-8.21},{name:'Tighter entry threshold',date:'15 Sep 2026',entry:2.3,exit:.2,return:15.08,sharpe:1.18,drawdown:-6.94},{name:'Longer holding window',date:'14 Sep 2026',entry:2,exit:0,return:21.14,sharpe:1.22,drawdown:-11.2}]
export const snapshot = () => '13:42:08 IST'
export const demoStatus = { market:'DEMO', quant:'DEMO', signal:'DEMO', database:'LOCAL', realtime:'NOT CONNECTED' }
export const apiConfig = { baseUrl: process.env.NEXT_PUBLIC_API_URL ?? '', adapter: 'demo' as const }
export const runBacktest = async (config:BacktestConfig) => { await new Promise(r=>setTimeout(r,450)); return backtestResult(config) }
export const runExperiment = async (config:BacktestConfig) => { await new Promise(r=>setTimeout(r,350)); return {name:'Custom experiment',date:'16 Sep 2026',entry:config.entry,exit:config.exit,return:Number((18.42+(config.entry-2)*1.7).toFixed(2)),sharpe:Number((1.31-(config.entry-2)*.08).toFixed(2)),drawdown:Number((-8.21-(config.holding-30)*.04).toFixed(2))} }
export const serviceContract = { getPairs, getPair, getSignals, runBacktest, runExperiment }
