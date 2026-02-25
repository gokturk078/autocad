'use client'

import { useState, useCallback } from 'react'
import { motion } from 'framer-motion'

const EXAMPLES = [
    'İstanbul, 600m² arsa, 5 katlı 3+1 konut, asansörlü',
    'Ankara, 400m² arsa, 3 katlı 2+1 konut',
    '25x20m arsa, 4 kat, 2 adet 3+1 daire, asansör',
]

interface PromptHeroProps {
    onSubmit: (prompt: string) => void
    isDisabled?: boolean
}

export default function PromptHero({ onSubmit, isDisabled }: PromptHeroProps) {
    const [input, setInput] = useState('')

    const handleSubmit = useCallback(
        (e: React.FormEvent) => {
            e.preventDefault()
            if (input.trim() && !isDisabled) {
                onSubmit(input.trim())
            }
        },
        [input, isDisabled, onSubmit]
    )

    const handleExample = useCallback(
        (text: string) => {
            setInput(text)
        },
        []
    )

    return (
        <motion.div
            className="flex flex-col items-center justify-center min-h-screen px-6"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -30, scale: 0.95 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            style={{ position: 'relative', zIndex: 1 }}
        >
            {/* Logo */}
            <motion.div
                className="mb-6"
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: 0.1, type: 'spring', stiffness: 200 }}
            >
                <div className="w-16 h-16 rounded-2xl flex items-center justify-center animate-float"
                    style={{
                        background: 'linear-gradient(135deg, rgba(212,175,55,0.15), rgba(212,175,55,0.05))',
                        border: '1px solid rgba(212,175,55,0.2)',
                    }}>
                    <span className="text-3xl">⬡</span>
                </div>
            </motion.div>

            {/* Title */}
            <motion.h1
                className="text-5xl font-bold mb-3 gradient-text text-center"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
                style={{ letterSpacing: '-0.02em' }}
            >
                Ne inşa edelim?
            </motion.h1>

            {/* Subtitle */}
            <motion.p
                className="text-base mb-10 text-center max-w-md"
                style={{ color: 'var(--text-secondary)' }}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
            >
                Doğal dille mimari projenizi tanımlayın. Yapay zeka saniyeler içinde
                profesyonel DXF paftaları üretsin.
            </motion.p>

            {/* Input */}
            <motion.form
                onSubmit={handleSubmit}
                className="w-full max-w-2xl mb-6"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
            >
                <div
                    className="glass-card gold-border flex items-center gap-3 px-5 py-4"
                    style={{ borderRadius: 20 }}
                >
                    <span className="text-lg" style={{ color: 'var(--gold-dim)' }}>✦</span>
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Örn: İstanbul, 25x20m arsa, 4 katlı 3+1 konut, asansörlü..."
                        disabled={isDisabled}
                        className="flex-1 bg-transparent text-base outline-none disabled:opacity-40"
                        style={{ color: 'var(--text-primary)' }}
                        autoFocus
                    />
                    <button
                        type="submit"
                        disabled={isDisabled || !input.trim()}
                        className="btn-primary disabled:opacity-30 disabled:cursor-not-allowed"
                        style={{ padding: '8px 20px', borderRadius: 12 }}
                    >
                        Üret →
                    </button>
                </div>
            </motion.form>

            {/* Example chips */}
            <motion.div
                className="flex flex-wrap gap-2 justify-center max-w-2xl"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.6 }}
            >
                <span className="text-xs mr-1" style={{ color: 'var(--text-tertiary)' }}>
                    Örnekler:
                </span>
                {EXAMPLES.map((ex, i) => (
                    <button
                        key={i}
                        onClick={() => handleExample(ex)}
                        className="btn-ghost text-xs"
                        style={{ padding: '5px 12px', borderRadius: 20 }}
                    >
                        {ex.length > 40 ? ex.slice(0, 38) + '...' : ex}
                    </button>
                ))}
            </motion.div>

            {/* Footer hint */}
            <motion.p
                className="mt-16 text-xs"
                style={{ color: 'var(--text-tertiary)' }}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.8 }}
            >
                AutoCA JARVIS v4.0 — Powered by GPT-4o
            </motion.p>
        </motion.div>
    )
}
