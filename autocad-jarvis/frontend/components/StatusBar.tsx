'use client'

import ConnectionDot from '@/components/ConnectionDot'
import { useProjectState } from '@/hooks/useProjectState'

export default function StatusBar() {
    const { project, wsStatus } = useProjectState()

    const filename = project?.filename ?? 'Dosya bekleniyor...'
    const area = project ? `${project.total_area_m2.toFixed(1)} m²` : '─'

    return (
        <header
            className="glass-card gold-border flex items-center justify-between px-4 py-3"
            style={{
                borderRadius: 0,
                borderTop: 'none',
                borderLeft: 'none',
                borderRight: 'none',
                minHeight: 56,
            }}
        >
            {/* Logo & brand */}
            <div className="flex items-center gap-2">
                <span className="text-lg gold-text font-bold tracking-wide">⬡ JARVIS</span>
            </div>

            {/* File + area */}
            <div className="flex items-center gap-2 text-sm" style={{ color: 'var(--text-secondary)' }}>
                <span className="max-w-[140px] truncate" title={project?.filepath ?? ''}>
                    {filename}
                </span>
                <span className="opacity-40">|</span>
                <span className="gold-text font-medium">{area}</span>
            </div>

            {/* Connection status */}
            <ConnectionDot status={wsStatus} />
        </header>
    )
}
