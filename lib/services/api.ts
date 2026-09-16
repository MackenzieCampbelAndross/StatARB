import * as demo from '@/lib/demo'
export type DataAdapter = typeof demo.serviceContract
export const api: DataAdapter = demo.serviceContract
export const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? ''
// Replace this binding with a FastAPI implementation that matches DataAdapter.
export const adapterMode = apiBaseUrl ? 'production' : 'demo'
