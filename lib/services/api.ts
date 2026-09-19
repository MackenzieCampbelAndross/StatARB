import type {
  BacktestConfig,
  Pair,
  Range,
  Signal,
  Trade,
} from '@/lib/demo'

export type ExperimentResult = {
  name: string
  date: string
  entry: number
  exit: number
  return: number
  sharpe: number
  drawdown: number
}

export type BacktestResult = {
  id?: string
  initial: number
  final: number
  total: number
  cagr: number
  sharpe: number
  sortino: number
  drawdown: number
  winRate: number
  profitFactor: number
  count: number
  curve?: Array<{ label: string; value: number }>
}

export type SystemStatus = {
  market: string
  quant: string
  signal: string
  database: string
  realtime: string
}

export const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Internal state tracking whether last API call succeeded
let backendConnected = false

export function isBackendOnline(): boolean {
  return backendConnected
}

/**
 * Timeout wrapper around fetch to avoid hung requests
 */
async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeoutMs = 3000
): Promise<Response> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    })
    return response
  } finally {
    clearTimeout(timer)
  }
}

/**
 * Robust, centralized API layer for StatArb N50.
 * Directly calls FastAPI backend for real-time data.
 */
export const api = {
  /**
   * Health check to detect if FastAPI is online
   */
  async checkHealth(): Promise<boolean> {
    try {
      const res = await fetchWithTimeout(`${apiBaseUrl}/health`, { method: 'GET' }, 1500)
      if (res.ok) {
        backendConnected = true
        return true
      }
    } catch {
      // Backend offline or unreachable
    }
    backendConnected = false
    return false
  },

  /**
   * Get filtered pairs from backend (/api/pairs) with fallback
   */
  async getPairs(filters?: {
    minCorrelation?: number
    maxP?: number
    maxHalfLife?: number
    signal?: string
    query?: string
  }): Promise<Pair[]> {
    const params = new URLSearchParams()
    if (filters?.minCorrelation !== undefined) params.set('minCorrelation', String(filters.minCorrelation))
    if (filters?.maxP !== undefined) params.set('maxP', String(filters.maxP))
    if (filters?.maxHalfLife !== undefined) params.set('maxHalfLife', String(filters.maxHalfLife))
    if (filters?.signal && filters.signal !== 'ALL') params.set('signal', filters.signal)
    if (filters?.query) params.set('query', filters.query)

    const url = `${apiBaseUrl}/api/pairs${params.toString() ? `?${params.toString()}` : ''}`
    const res = await fetchWithTimeout(url, { method: 'GET' }, 3000)

    if (!res.ok) {
      throw new Error(`Failed to fetch pairs: ${res.status}`)
    }

    const data = await res.json()
    if (!Array.isArray(data)) {
      throw new Error('Invalid response format from pairs API')
    }

    backendConnected = true
    return data
  },

  /**
   * Get a single pair by ID (/api/pairs/{id}) with fallback
   */
  async getPair(id: string): Promise<Pair> {
    const res = await fetchWithTimeout(`${apiBaseUrl}/api/pairs/${id}`, { method: 'GET' }, 3000)

    if (!res.ok) {
      throw new Error(`Failed to fetch pair: ${res.status}`)
    }

    const data = await res.json()
    if (!data || !data.id) {
      throw new Error('Invalid response format from pair API')
    }

    backendConnected = true
    return data
  },

  /**
   * Get active signals (/api/signals) with fallback
   */
  async getSignals(filter = 'ALL'): Promise<Signal[]> {
    const url = `${apiBaseUrl}/api/signals${filter !== 'ALL' ? `?filter=${encodeURIComponent(filter)}` : ''}`
    const res = await fetchWithTimeout(url, { method: 'GET' }, 3000)

    if (!res.ok) {
      throw new Error(`Failed to fetch signals: ${res.status}`)
    }

    const data = await res.json()
    if (!Array.isArray(data)) {
      throw new Error('Invalid response format from signals API')
    }

    backendConnected = true
    return data
  },

  /**
   * Execute backtest on the backend (/api/backtests) with fallback
   */
  async runBacktest(config: BacktestConfig): Promise<BacktestResult> {
    const res = await fetchWithTimeout(
      `${apiBaseUrl}/api/backtests`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      },
      10000 // Allow up to 10s for backtest
    )

    if (!res.ok) {
      throw new Error(`Failed to run backtest: ${res.status}`)
    }

    const data = await res.json()
    if (!data || data.final === undefined) {
      throw new Error('Invalid response format from backtest API')
    }

    backendConnected = true
    return data
  },

  /**
   * Get trades for a backtest (/api/backtests/{id}/trades) with fallback
   */
  async getBacktestTrades(backtestId?: string): Promise<Trade[]> {
    if (!backtestId) {
      throw new Error('Backtest ID is required')
    }

    const res = await fetchWithTimeout(`${apiBaseUrl}/api/backtests/${backtestId}/trades`, { method: 'GET' }, 3000)

    if (!res.ok) {
      throw new Error(`Failed to fetch backtest trades: ${res.status}`)
    }

    const data = await res.json()
    if (!Array.isArray(data)) {
      throw new Error('Invalid response format from backtest trades API')
    }

    backendConnected = true
    return data.map((t: any) => ({
      ...t,
      return: t.return ?? t.return_val ?? 0,
    }))
  },

  /**
   * Run research hypothesis experiment (/api/research/experiments) with fallback
   */
  async runExperiment(config: BacktestConfig): Promise<ExperimentResult> {
    const res = await fetchWithTimeout(
      `${apiBaseUrl}/api/research/experiments`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      },
      5000
    )

    if (!res.ok) {
      throw new Error(`Failed to run experiment: ${res.status}`)
    }

    const data = await res.json()
    if (!data || !data.name) {
      throw new Error('Invalid response format from experiment API')
    }

    backendConnected = true
    return {
      ...data,
      return: data.return ?? data.return_val ?? 0,
    }
  },

  /**
   * Get past experiments history (/api/research/experiments) with fallback
   */
  async getExperiments(): Promise<ExperimentResult[]> {
    const res = await fetchWithTimeout(`${apiBaseUrl}/api/research/experiments`, { method: 'GET' }, 3000)

    if (!res.ok) {
      throw new Error(`Failed to fetch experiments: ${res.status}`)
    }

    const data = await res.json()
    if (!Array.isArray(data)) {
      throw new Error('Invalid response format from experiments API')
    }

    backendConnected = true
    return data.map((x: any) => ({
      ...x,
      return: x.return ?? x.return_val ?? 0,
    }))
  },

  /**
   * Get portfolio risk metrics (/api/risk) with fallback
   */
  async getRisk(): Promise<Record<string, string>> {
    const res = await fetchWithTimeout(`${apiBaseUrl}/api/risk`, { method: 'GET' }, 3000)

    if (!res.ok) {
      throw new Error(`Failed to fetch risk metrics: ${res.status}`)
    }

    const data = await res.json()
    if (!data || typeof data !== 'object' || Object.keys(data).length === 0) {
      throw new Error('Invalid response format from risk API')
    }

    backendConnected = true
    return data
  },

  /**
   * Get system status telemetry (/api/system/status) with fallback
   */
  async getSystemStatus(): Promise<SystemStatus> {
    const res = await fetchWithTimeout(`${apiBaseUrl}/api/system/status`, { method: 'GET' }, 2000)

    if (!res.ok) {
      throw new Error(`Failed to fetch system status: ${res.status}`)
    }

    const data = await res.json()
    if (!data || !data.quant) {
      throw new Error('Invalid response format from system status API')
    }

    backendConnected = true
    return data
  },

  /**
   * Get historical spread and price series for a specific pair (/api/pairs/{id}/series)
   */
  async getPairSeries(
    pair: Pair,
    range: Range,
    mode: 'spread' | 'price' = 'spread'
  ): Promise<any[]> {
    const res = await fetchWithTimeout(
      `${apiBaseUrl}/api/pairs/${pair.id}/series?range=${range}&mode=${mode}`,
      { method: 'GET' },
      3000
    )

    if (!res.ok) {
      throw new Error(`Failed to fetch pair series: ${res.status}`)
    }

    const data = await res.json()
    if (!Array.isArray(data) || data.length === 0) {
      throw new Error('Invalid response format from pair series API')
    }

    backendConnected = true
    return data
  },

  /**
   * Get active cointegrated pairs exposure (/api/risk/exposure)
   */
  async getRiskExposure(): Promise<any[]> {
    const res = await fetchWithTimeout(`${apiBaseUrl}/api/risk/exposure`, { method: 'GET' }, 3000)

    if (!res.ok) {
      throw new Error(`Failed to fetch risk exposure: ${res.status}`)
    }

    const data = await res.json()
    if (!Array.isArray(data)) {
      throw new Error('Invalid response format from risk exposure API')
    }

    backendConnected = true
    return data
  },
}
