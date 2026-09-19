export type SignalStreamEvent = {
  pair: string
  priceA: number
  priceB: number
  spread: number
  zScore: number
  signal: string
  timestamp: string
}

export type SignalStreamStatus = 'NOT CONNECTED' | 'CONNECTED'

type SignalListener = (event: SignalStreamEvent) => void
type StatusListener = (status: SignalStreamStatus) => void

class SignalStreamClient {
  private socket: WebSocket | null = null
  private listeners: Set<SignalListener> = new Set()
  private statusListeners: Set<StatusListener> = new Set()
  private subscribedPairs: Set<string> = new Set()
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private isExplicitlyClosed = false
  private retryCount = 0

  public status: SignalStreamStatus = 'NOT CONNECTED'

  private getWsUrl(): string {
    const rawWs = process.env.NEXT_PUBLIC_WS_URL
    if (rawWs) {
      return rawWs.endsWith('/signals') ? rawWs : `${rawWs.replace(/\/$/, '')}/signals`
    }
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const wsBase = apiUrl.replace(/^http/, 'ws')
    return `${wsBase.replace(/\/$/, '')}/api/ws/signals`
  }

  private setStatus(newStatus: SignalStreamStatus) {
    if (this.status !== newStatus) {
      this.status = newStatus
      this.statusListeners.forEach((l) => {
        try {
          l(newStatus)
        } catch {}
      })
    }
  }

  public async connect(pairIds?: string[]): Promise<{ status: SignalStreamStatus }> {
    if (typeof window === 'undefined') {
      return { status: 'NOT CONNECTED' }
    }

    if (pairIds) {
      pairIds.forEach((id) => this.subscribedPairs.add(id))
    }

    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return { status: this.status }
    }

    this.isExplicitlyClosed = false

    return new Promise((resolve) => {
      try {
        const url = this.getWsUrl()
        this.socket = new WebSocket(url)

        const timeout = setTimeout(() => {
          if (this.status !== 'CONNECTED') {
            resolve({ status: 'NOT CONNECTED' })
          }
        }, 3000)

        this.socket.onopen = () => {
          clearTimeout(timeout)
          this.setStatus('CONNECTED')
          this.retryCount = 0

          // Subscribe to pairs if any
          if (this.subscribedPairs.size > 0) {
            this.send({
              action: 'subscribe',
              pair_ids: Array.from(this.subscribedPairs),
            })
          }

          // Start heartbeat
          this.startHeartbeat()
          resolve({ status: 'CONNECTED' })
        }

        this.socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            if (data.type === 'signal' || (data.pair && data.spread !== undefined)) {
              const streamEvent: SignalStreamEvent = {
                pair: data.pair,
                priceA: data.priceA ?? 0,
                priceB: data.priceB ?? 0,
                spread: data.spread ?? 0,
                zScore: data.zScore ?? 0,
                signal: data.signal ?? 'WATCH',
                timestamp: data.timestamp ?? new Date().toLocaleTimeString(),
              }
              this.listeners.forEach((listener) => {
                try {
                  listener(streamEvent)
                } catch {}
              })
            }
          } catch {}
        }

        this.socket.onerror = () => {
          clearTimeout(timeout)
          this.setStatus('NOT CONNECTED')
          resolve({ status: 'NOT CONNECTED' })
        }

        this.socket.onclose = () => {
          clearTimeout(timeout)
          this.stopHeartbeat()
          this.setStatus('NOT CONNECTED')
          this.socket = null

          if (!this.isExplicitlyClosed) {
            this.scheduleReconnect()
          }
        }
      } catch {
        this.setStatus('NOT CONNECTED')
        resolve({ status: 'NOT CONNECTED' })
      }
    })
  }

  public disconnect() {
    this.isExplicitlyClosed = true
    this.stopHeartbeat()
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.socket) {
      try {
        this.socket.close()
      } catch {}
      this.socket = null
    }
    this.setStatus('NOT CONNECTED')
  }

  public subscribe(listener: SignalListener): () => void {
    this.listeners.add(listener)
    // Return unsubscribe function
    return () => {
      this.listeners.delete(listener)
    }
  }

  public onStatusChange(listener: StatusListener): () => void {
    this.statusListeners.add(listener)
    listener(this.status)
    return () => {
      this.statusListeners.delete(listener)
    }
  }

  public subscribePairs(pairIds: string[]) {
    pairIds.forEach((id) => this.subscribedPairs.add(id))
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.send({
        action: 'subscribe',
        pair_ids: pairIds,
      })
    }
  }

  private send(msg: any) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      try {
        this.socket.send(JSON.stringify(msg))
      } catch {}
    }
  }

  private startHeartbeat() {
    this.stopHeartbeat()
    this.heartbeatTimer = setInterval(() => {
      this.send({ action: 'heartbeat' })
    }, 25000)
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimer || this.isExplicitlyClosed) return
    // Exponential backoff capped at 30 seconds
    const delay = Math.min(1000 * Math.pow(1.5, this.retryCount), 30000)
    this.retryCount++
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this.connect()
    }, delay)
  }
}

export const signalStream = new SignalStreamClient()
