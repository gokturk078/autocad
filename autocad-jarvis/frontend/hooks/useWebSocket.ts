'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { WS_URL, RECONNECT_DELAY_MS, MAX_RECONNECT_ATTEMPTS, PING_INTERVAL_MS } from '@/lib/constants'
import type { WebSocketMessage, ConnectionStatus } from '@/lib/types'

interface UseWebSocketReturn {
    status: ConnectionStatus
    lastMessage: WebSocketMessage | null
    send: (data: Record<string, unknown>) => void
    reconnect: () => void
}

export function useWebSocket(): UseWebSocketReturn {
    const [status, setStatus] = useState<ConnectionStatus>('disconnected')
    const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)

    const socketRef = useRef<WebSocket | null>(null)
    const reconnectCountRef = useRef(0)
    const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
    const pingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
    const mountedRef = useRef(false)

    const clearTimers = useCallback(() => {
        if (reconnectTimerRef.current) {
            clearTimeout(reconnectTimerRef.current)
            reconnectTimerRef.current = null
        }
        if (pingTimerRef.current) {
            clearInterval(pingTimerRef.current)
            pingTimerRef.current = null
        }
    }, [])

    const cleanup = useCallback(() => {
        clearTimers()
        const ws = socketRef.current
        if (ws) {
            ws.onopen = null
            ws.onmessage = null
            ws.onclose = null
            ws.onerror = null
            if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
                ws.close()
            }
            socketRef.current = null
        }
    }, [clearTimers])

    const connect = useCallback(() => {
        // Don't connect if not mounted (React Strict Mode unmount)
        if (!mountedRef.current) return

        cleanup()
        setStatus('connecting')

        const attempt = reconnectCountRef.current + 1
        console.log(`[WS] Bağlanıyor: ${WS_URL} (deneme ${attempt})`)

        const ws = new WebSocket(WS_URL)
        socketRef.current = ws

        ws.onopen = () => {
            if (!mountedRef.current) {
                ws.close()
                return
            }
            reconnectCountRef.current = 0
            setStatus('connected')
            console.log('[WS] ✓ Bağlantı kuruldu')

            // Start ping heartbeat
            pingTimerRef.current = setInterval(() => {
                if (ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({ type: 'ping' }))
                }
            }, PING_INTERVAL_MS)
        }

        ws.onmessage = (event: MessageEvent) => {
            if (!mountedRef.current) return
            try {
                const msg = JSON.parse(event.data as string) as WebSocketMessage
                if (msg.type !== 'pong') {
                    setLastMessage(msg)
                }
            } catch {
                // ignore invalid messages
            }
        }

        ws.onclose = () => {
            clearTimers()
            if (!mountedRef.current) return
            setStatus('disconnected')

            if (reconnectCountRef.current < MAX_RECONNECT_ATTEMPTS) {
                const delay = RECONNECT_DELAY_MS * Math.min(reconnectCountRef.current + 1, 5)
                reconnectCountRef.current++
                console.log(`[WS] Yeniden bağlanılıyor... (${reconnectCountRef.current}/${MAX_RECONNECT_ATTEMPTS}) ${delay}ms`)
                reconnectTimerRef.current = setTimeout(() => {
                    if (mountedRef.current) connect()
                }, delay)
            } else {
                setStatus('error')
                console.error('[WS] Maksimum deneme aşıldı')
            }
        }

        ws.onerror = () => {
            // onclose fires after this
        }
    }, [cleanup, clearTimers])

    useEffect(() => {
        mountedRef.current = true

        // Small delay to avoid React Strict Mode double-connect race
        const initTimer = setTimeout(() => {
            if (mountedRef.current) {
                connect()
            }
        }, 100)

        return () => {
            mountedRef.current = false
            clearTimeout(initTimer)
            cleanup()
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    const send = useCallback((data: Record<string, unknown>) => {
        if (socketRef.current?.readyState === WebSocket.OPEN) {
            socketRef.current.send(JSON.stringify(data))
        }
    }, [])

    const reconnect = useCallback(() => {
        reconnectCountRef.current = 0
        connect()
    }, [connect])

    return { status, lastMessage, send, reconnect }
}
