'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'

interface StatCardProps {
    label: string
    value: number
    unit: string
    icon: string
    delay?: number
    format?: 'number' | 'currency'
}

export default function StatCard({ label, value, unit, icon, delay = 0, format = 'number' }: StatCardProps) {
    const [display, setDisplay] = useState(0)

    useEffect(() => {
        const duration = 1200
        const steps = 40
        const increment = value / steps
        let current = 0
        const timer = setInterval(() => {
            current += increment
            if (current >= value) {
                setDisplay(value)
                clearInterval(timer)
            } else {
                setDisplay(Math.floor(current))
            }
        }, duration / steps)
        return () => clearInterval(timer)
    }, [value])

    const formatted = format === 'currency'
        ? new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY', maximumFractionDigits: 0 }).format(display)
        : display.toLocaleString('tr-TR')

    return (
        <motion.div
            className="glass-card p-4 flex flex-col gap-1"
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ delay, type: 'spring', stiffness: 300, damping: 30 }}
        >
            <div className="flex items-center gap-2">
                <span className="text-sm">{icon}</span>
                <span className="text-xs font-medium" style={{ color: 'var(--text-tertiary)' }}>
                    {label}
                </span>
            </div>
            <div className="flex items-baseline gap-1.5">
                <span className="text-2xl font-bold" style={{ color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
                    {formatted}
                </span>
                <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                    {unit}
                </span>
            </div>
        </motion.div>
    )
}
