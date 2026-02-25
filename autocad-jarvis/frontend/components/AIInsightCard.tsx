'use client'

import { useProjectState } from '@/hooks/useProjectState'

function ShimmerLine({ width }: { width: string }) {
    return (
        <div
            className="h-4 rounded animate-shimmer"
            style={{
                width,
                background:
                    'linear-gradient(90deg, transparent 25%, rgba(255,255,255,0.06) 50%, transparent 75%)',
                backgroundSize: '200% 100%',
            }}
        />
    )
}

export default function AIInsightCard() {
    const { analysis, isAnalyzing } = useProjectState()

    // Placeholder — no data yet
    if (!analysis && !isAnalyzing) {
        return (
            <div className="glass-card gold-border p-4">
                <div className="flex items-center gap-2 mb-3">
                    <span className="gold-text font-semibold text-sm">⬡ AI Analiz</span>
                </div>
                <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                    AutoCAD&apos;de bir .dxf dosyası kaydedin — AI analizi burada görünecek.
                </p>
            </div>
        )
    }

    // Loading skeleton
    if (isAnalyzing) {
        return (
            <div className="glass-card gold-border p-4 animate-pulse-gold">
                <div className="flex items-center gap-2 mb-3">
                    <span className="gold-text font-semibold text-sm">⬡ AI Analiz</span>
                    <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                        analiz ediliyor...
                    </span>
                </div>
                <div className="space-y-2">
                    <ShimmerLine width="100%" />
                    <ShimmerLine width="85%" />
                    <ShimmerLine width="60%" />
                </div>
            </div>
        )
    }

    // Analysis ready
    const timeStr = analysis
        ? new Date(analysis.generated_at).toLocaleTimeString('tr-TR')
        : ''

    return (
        <div className="glass-card gold-border p-4 animate-slide-up">
            <div className="flex items-center gap-2 mb-3">
                <span className="gold-text font-semibold text-sm">⬡ AI Analiz</span>
            </div>
            <p
                className="text-sm leading-relaxed mb-3"
                style={{ color: 'rgba(203, 213, 225, 0.9)' }}
            >
                {analysis?.summary_tr}
            </p>
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                {analysis?.model_used} · {analysis?.tokens_used} token · {timeStr}
            </p>
        </div>
    )
}
