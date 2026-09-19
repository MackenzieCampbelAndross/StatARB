import * as demo from '@/lib/demo'
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
 * Directly calls FastAPI backend with transparent, seamless fallback to demo data
 * whenever the backend is unreachable or returning errors.
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
    try {
      const params = new URLSearchParams()
      if (filters?.minCorrelation !== undefined) params.set('minCorrelation', String(filters.minCorrelation))
      if (filters?.maxP !== undefined) params.set('maxP', String(filters.maxP))
      if (filters?.maxHalfLife !== undefined) params.set('maxHalfLife', String(filters.maxHalfLife))
      if (filters?.signal && filters.signal !== 'ALL') params.set('signal', filters.signal)
      if (filters?.query) params.set('query', filters.query)

      const url = `${apiBaseUrl}/api/pairs${params.toString() ? `?${params.toString()}` : ''}`
      const res = await fetchWithTimeout(url, { method: 'GET' }, 3000)

      if (res.ok) {
        const data = await res.json()
        if (Array.isArray(data) && data.length > 0) {
          backendConnected = true
          return data
        }
      }
    } catch (err) {
      // Graceful fallback to demo data
    }
    const fallbackFilters = filters
      ? {
          minCorrelation: filters.minCorrelation ?? 0.7,
          maxP: filters.maxP ?? 0.05,
          maxHalfLife: filters.maxHalfLife ?? 30,
          signal: filters.signal ?? 'ALL',
          query: filters.query,
        }
      : undefined
    return demo.getPairs(fallbackFilters)
  },

  /**
   * Get a single pair by ID (/api/pairs/{id}) with fallback
   */
  async getPair(id: string): Promise<Pair> {
    try {
      const res = await fetchWithTimeout(`${apiBaseUrl}/api/pairs/${id}`, { method: 'GET' }, 3000)
      if (res.ok) {
        const data = await res.json()
        if (data && data.id) {
          backendConnected = true
          return data
        }
      }
    } catch (err) {
      // Graceful fallback
    }
    return demo.getPair(id)
  },

  /**
   * Get active signals (/api/signals) with fallback
   */
  async getSignals(filter = 'ALL'): Promise<Signal[]> {
    try {
      const url = `${apiBaseUrl}/api/signals${filter !== 'ALL' ? `?filter=${encodeURIComponent(filter)}` : ''}`
      const res = await fetchWithTimeout(url, { method: 'GET' }, 3000)
      if (res.ok) {
        const data = await res.json()
        if (Array.isArray(data)) {
          backendConnected = true
          return data
        }
      }
    } catch (err) {
      // Graceful fallback
    }
    const demoData = demo.getSignals()
    return filter === 'ALL' ? demoData : demoData.filter((x) => x.signal === filter)
  },

  /**
   * Execute backtest on the backend (/api/backtests) with fallback
   */
  async runBacktest(config: BacktestConfig): Promise<BacktestResult> {
    try {
      const res = await fetchWithTimeout(
        `${apiBaseUrl}/api/backtests`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(config),
        },
        10000 // Allow up to 10s for backtest
      )
      if (res.ok) {
        const data = await res.json()
        if (data && data.final !== undefined) {
          backendConnected = true
          return data
        }
      }
    } catch (err) {
      // Graceful fallback
    }
    return demo.runBacktest(config)
  },

  /**
   * Get trades for a backtest (/api/backtests/{id}/trades) with fallback
   */
  async getBacktestTrades(backtestId?: string): Promise<Trade[]> {
    if (!backtestId) return demo.trades
    try {
      const res = await fetchWithTimeout(`${apiBaseUrl}/api/backtests/${backtestId}/trades`, { method: 'GET' }, 3000)
      if (res.ok) {
        const data = await res.json()
        if (Array.isArray(data) && data.length > 0) {
          backendConnected = true
          return data.map((t: any) => ({
            ...t,
            return: t.return ?? t.return_val ?? 0,
          }))
        }
      }
    } catch (err) {
      // Graceful fallback
    }
    return demo.trades
  },

  /**
   * Run research hypothesis experiment (/api/research/experiments) with fallback
   */
  async runExperiment(config: BacktestConfig): Promise<ExperimentResult> {
    try {
      const res = await fetchWithTimeout(
        `${apiBaseUrl}/api/research/experiments`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(config),
        },
        5000
      )
      if (res.ok) {
        const data = await res.json()
        if (data && data.name) {
          backendConnected = true
          return {
            ...data,
            return: data.return ?? data.return_val ?? 0,
          }
        }
      }
    } catch (err) {
      // Graceful fallback
    }
    return demo.runExperiment(config)
  },

  /**
   * Get past experiments history (/api/research/experiments) with fallback
   */
  async getExperiments(): Promise<ExperimentResult[]> {
    try {
      const res = await fetchWithTimeout(`${apiBaseUrl}/api/research/experiments`, { method: 'GET' }, 3000)
      if (res.ok) {
        const data = await res.json()
        if (Array.isArray(data) && data.length > 0) {
          backendConnected = true
          return data.map((x: any) => ({
            ...x,
            return: x.return ?? x.return_val ?? 0,
          }))
        }
      }
    } catch (err) {
      // Graceful fallback
    }
    return demo.experiments
  },

  /**
   * Get portfolio risk metrics (/api/risk) with fallback
   */
  async getRisk(): Promise<Record<string, string>> {
    try {
      const res = await fetchWithTimeout(`${apiBaseUrl}/api/risk`, { method: 'GET' }, 3000)
      if (res.ok) {
        const data = await res.json()
        if (data && typeof data === 'object' && Object.keys(data).length > 0) {
          backendConnected = true
          return data
        }
      }
    } catch (err) {
      // Graceful fallback
    }
    return demo.risk
  },

  /**
   * Get system status telemetry (/api/system/status) with fallback
   */
  async getSystemStatus(): Promise<SystemStatus> {
    try {
      const res = await fetchWithTimeout(`${apiBaseUrl}/api/system/status`, { method: 'GET' }, 2000)
      if (res.ok) {
        const data = await res.json()
        if (data && data.quant) {
          backendConnected = true
          return data
        }
      }
    } catch (err) {
      // Graceful fallback
    }
    return demo.demoStatus
  },

  /**
   * Get historical spread and price series for a specific pair (/api/pairs/{id}/series)
   */
  async getPairSeries(
    pair: Pair,
    range: Range,
    mode: 'spread' | 'price' = 'spread'
  ): Promise<any[]> {
    try {
      const res = await fetchWithTimeout(
        `${apiBaseUrl}/api/pairs/${pair.id}/series?range=${range}&mode=${mode}`,
        { method: 'GET' },
        3000
      )
      if (res.ok) {
        const data = await res.json()
        if (Array.isArray(data) && data.length > 0) {
          backendConnected = true
          return data
        }
      }
    } catch (err) {
      // Graceful fallback
    }
    return demo.series(pair, range, mode)
  },

  /**
   * Get active cointegrated pairs exposure (/api/risk/exposure)
   */
  async getRiskExposure(): Promise<any[]> {
    try {
      const res = await fetchWithTimeout(`${apiBaseUrl}/api/risk/exposure`, { method: 'GET' }, 3000)
      if (res.ok) {
        const data = await res.json()
        if (Array.isArray(data) && data.length > 0) {
          backendConnected = true
          return data
        }
      }
    } catch (err) {
      // Graceful fallback
    }
    return demo.pairs.slice(0, 5).map((p, i) => ({
      ...p,
      weight: 18.4 - i * 2.8,
    }))
  },
}

export const adapterMode = process.env.NEXT_PUBLIC_API_URL ? 'production' : 'demo'
