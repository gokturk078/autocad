'use client'

import { AnimatePresence } from 'framer-motion'

import GradientMesh from '@/components/GradientMesh'
import PromptHero from '@/components/PromptHero'
import GenerationTimeline from '@/components/GenerationTimeline'
import ResultsDashboard from '@/components/ResultsDashboard'
import { useGenerateProject } from '@/hooks/useGenerateProject'

export default function JarvisPage() {
    const { phase, project, error, prompt, generate, reset } = useGenerateProject()

    const isLoading = !['idle', 'done', 'error'].includes(phase)

    return (
        <main className="min-h-screen relative" style={{ background: 'var(--bg-primary)' }}>
            {/* Animated gradient background */}
            <GradientMesh phase={isLoading ? 'loading' : phase} />

            <AnimatePresence mode="wait">
                {/* ── IDLE: Prompt input ─────────────────────── */}
                {phase === 'idle' && (
                    <PromptHero
                        key="prompt"
                        onSubmit={generate}
                    />
                )}

                {/* ── LOADING: Generation timeline ──────────── */}
                {isLoading && (
                    <GenerationTimeline
                        key="timeline"
                        currentPhase={phase}
                        prompt={prompt}
                    />
                )}

                {/* ── DONE: Results + DXF Viewer ────────────── */}
                {phase === 'done' && project && (
                    <ResultsDashboard
                        key="results"
                        project={project}
                        onNewProject={reset}
                    />
                )}

                {/* ── ERROR ──────────────────────────────────── */}
                {phase === 'error' && (
                    <div
                        key="error"
                        className="flex flex-col items-center justify-center min-h-screen gap-4"
                        style={{ position: 'relative', zIndex: 1 }}
                    >
                        <div className="glass-card p-6 max-w-md text-center space-y-4"
                            style={{ borderColor: 'rgba(239,68,68,0.2)' }}>
                            <span className="text-4xl">⚠</span>
                            <h2 className="text-lg font-semibold" style={{ color: 'var(--red)' }}>
                                Üretim Başarısız
                            </h2>
                            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                                {error || 'Bilinmeyen bir hata oluştu'}
                            </p>
                            <div className="flex gap-3 justify-center">
                                <button className="btn-primary" onClick={() => generate(prompt)}>
                                    Tekrar Dene
                                </button>
                                <button className="btn-ghost" onClick={reset}>
                                    Geri Dön
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </AnimatePresence>
        </main>
    )
}
