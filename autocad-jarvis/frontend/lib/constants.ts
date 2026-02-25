/** Application-wide constants. */

export const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8765/ws'
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8765'
export const RECONNECT_DELAY_MS = 3000
export const MAX_RECONNECT_ATTEMPTS = 10
export const PING_INTERVAL_MS = 15000
