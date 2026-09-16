export type SignalStreamEvent = { pair: string; priceA: number; priceB: number; spread: number; zScore: number; signal: string; timestamp: string }
export type SignalStreamStatus = 'NOT CONNECTED' | 'CONNECTED'
export const signalStream = { status: 'NOT CONNECTED' as SignalStreamStatus, connect: async () => ({ status: 'NOT CONNECTED' as SignalStreamStatus }), disconnect: () => undefined, subscribe: (_listener: (event: SignalStreamEvent) => void) => () => undefined }
// This intentionally does not simulate streaming. Wire connect/subscribe to FastAPI WebSocket or SSE later.
