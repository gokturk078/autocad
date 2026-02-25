'use client'

import { motion } from 'framer-motion'
import { GENERATION_STEPS, type GenerationPhase } from '@/lib/types'

interface GenerationTimelineProps {
    currentPhase: GenerationPhase
    prompt: string
}

export default function GenerationTimeline({ currentPhase, prompt }: GenerationTimelineProps) {
    const phaseOrder: GenerationPhase[] = ['parsing', 'checking', 'planning', 'generating', 'packaging']
    const currentIdx = phaseOrder.indexOf(currentPhase)

    return (
        <motion.div
            className="flex flex-col items-center justify-center min-h-screen px-6"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            style={{ position: 'relative', zIndex: 1 }}
        >
            {/* Spinning icon */}
            <motion.div
                className="mb-8"
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', stiffness: 200, damping: 20 }}
            >
                <div
                    className="w-20 h-20 rounded-full flex items-center justify-center animate-spin-slow"
                    style={{
                        background: 'conic-gradient(from 0deg, rgba(212,175,55,0.3), transparent, rgba(212,175,55,0.3))',
                        border: '2px solid rgba(212,175,55,0.2)',
                    }}
                >
                    <div className="w-14 h-14 rounded-full flex items-center justify-center"
                        style={{ background: 'var(--bg-primary)' }}>
                        <span className="text-2xl" style={{ animation: 'none' }}>⬡</span>
                    </div>
                </div>
            </motion.div>

            {/* Prompt text */}
            <motion.p
                className="text-sm mb-8 text-center max-w-lg glass-card px-5 py-3"
                style={{ color: 'var(--text-secondary)', borderRadius: 12 }}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
            >
                &quot;{prompt}&quot;
            </motion.p>

            {/* Steps */}
            <motion.div
                className="w-full max-w-md space-y-3"
                initial="hidden"
                animate="show"
                variants={{
                    hidden: {},
                    show: { transition: { staggerChildren: 0.15 } },
                }}
            >
                {GENERATION_STEPS.map((step, i) => {
                    const isDone = currentIdx > i
                    const isActive = currentIdx === i
                    const isPending = currentIdx < i

                    return (
                        <motion.div
                            key={step.id}
                            className="glass-card flex items-center gap-4 px-5 py-4"
                            variants={{
                                hidden: { opacity: 0, x: -20 },
                                show: { opacity: 1, x: 0 },
                            }}
                            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                            style={{
                                borderColor: isActive
                                    ? 'rgba(212,175,55,0.3)'
                                    : isDone
                                        ? 'rgba(34,197,94,0.2)'
                                        : undefined,
                                opacity: isPending ? 0.4 : 1,
                            }}
                        >
                            {/* Icon */}
                            <div className="w-10 h-10 rounded-xl flex items-center justify-center text-lg shrink-0"
                                style={{
                                    background: isDone
                                        ? 'rgba(34,197,94,0.12)'
                                        : isActive
                                            ? 'rgba(212,175,55,0.12)'
                                            : 'rgba(255,255,255,0.03)',
                                }}>
                                {isDone ? (
                                    <motion.span
                                        initial={{ scale: 0, rotate: -90 }}
                                        animate={{ scale: 1, rotate: 0 }}
                                        transition={{ type: 'spring', stiffness: 400 }}
                                        style={{ color: 'var(--green)' }}
                                    >
                                        ✓
                                    </motion.span>
                                ) : isActive ? (
                                    <motion.span
                                        animate={{ scale: [1, 1.15, 1] }}
                                        transition={{ duration: 1.5, repeat: Infinity }}
                                    >
                                        {step.icon}
                                    </motion.span>
                                ) : (
                                    <span style={{ opacity: 0.3 }}>{step.icon}</span>
                                )}
                            </div>

                            {/* Text */}
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium" style={{
                                    color: isDone ? 'var(--green)' : isActive ? 'var(--gold)' : 'var(--text-secondary)',
                                }}>
                                    {step.label}
                                </p>
                                <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                                    {step.description}
                                </p>
                            </div>

                            {/* Status */}
                            {isActive && (
                                <motion.div
                                    className="w-5 h-5 rounded-full"
                                    style={{
                                        border: '2px solid var(--gold)',
                                        borderTopColor: 'transparent',
                                    }}
                                    animate={{ rotate: 360 }}
                                    transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                                />
                            )}
                            {isDone && (
                                <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                                    ✓
                                </span>
                            )}
                        </motion.div>
                    )
                })}
            </motion.div>
        </motion.div>
    )
}
