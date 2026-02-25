'use client'

import { motion } from 'framer-motion'

export default function GradientMesh({ phase }: { phase: string }) {
    const colors = {
        idle: ['rgba(59,130,246,0.08)', 'rgba(139,92,246,0.06)', 'rgba(6,182,212,0.05)'],
        loading: ['rgba(212,175,55,0.12)', 'rgba(245,158,11,0.08)', 'rgba(212,175,55,0.06)'],
        done: ['rgba(34,197,94,0.08)', 'rgba(16,185,129,0.06)', 'rgba(6,182,212,0.05)'],
        error: ['rgba(239,68,68,0.08)', 'rgba(244,63,94,0.06)', 'rgba(239,68,68,0.04)'],
    }

    const c = colors[phase as keyof typeof colors] || colors.idle

    return (
        <div className="fixed inset-0 pointer-events-none" style={{ zIndex: 0 }}>
            <motion.div
                className="absolute inset-0"
                animate={{
                    background: [
                        `radial-gradient(ellipse 80% 60% at 20% 30%, ${c[0]}, transparent),
                         radial-gradient(ellipse 60% 80% at 80% 70%, ${c[1]}, transparent),
                         radial-gradient(ellipse 50% 50% at 50% 50%, ${c[2]}, transparent)`,
                        `radial-gradient(ellipse 80% 60% at 30% 40%, ${c[0]}, transparent),
                         radial-gradient(ellipse 60% 80% at 70% 60%, ${c[1]}, transparent),
                         radial-gradient(ellipse 50% 50% at 60% 40%, ${c[2]}, transparent)`,
                        `radial-gradient(ellipse 80% 60% at 20% 30%, ${c[0]}, transparent),
                         radial-gradient(ellipse 60% 80% at 80% 70%, ${c[1]}, transparent),
                         radial-gradient(ellipse 50% 50% at 50% 50%, ${c[2]}, transparent)`,
                    ],
                }}
                transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
            />
        </div>
    )
}
