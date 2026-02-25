'use client'

import type { ConnectionStatus } from '@/lib/types'

const CONFIG: Record<ConnectionStatus, { color: string; label: string; animClass: string }> = {
    connected: { color: 'bg-jarvis-green', label: 'Bağlı', animClass: 'animate-pulse' },
    connecting: { color: 'bg-yellow-400', label: 'Bağlanıyor', animClass: 'animate-ping' },
    disconnected: { color: 'bg-gray-500', label: 'Bağlantı Yok', animClass: '' },
    error: { color: 'bg-jarvis-red', label: 'Hata', animClass: 'animate-pulse' },
}

interface ConnectionDotProps {
    status: ConnectionStatus
    showLabel?: boolean
}

export default function ConnectionDot({ status, showLabel = true }: ConnectionDotProps) {
    const cfg = CONFIG[status]

    return (
        <div className="flex items-center gap-2">
            <span className="relative flex h-3 w-3">
                {cfg.animClass && (
                    <span
                        className={`absolute inline-flex h-full w-full rounded-full opacity-75 ${cfg.color} ${cfg.animClass}`}
                    />
                )}
                <span
                    className={`relative inline-flex h-3 w-3 rounded-full ${cfg.color}`}
                />
            </span>
            {showLabel && (
                <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                    {cfg.label}
                </span>
            )}
        </div>
    )
}
