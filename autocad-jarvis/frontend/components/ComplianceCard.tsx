'use client'

import { motion } from 'framer-motion'

interface ComplianceItem {
    label: string
    actual: number
    limit: number
    unit: string
    status: string
}

interface ComplianceCardProps {
    items: ComplianceItem[]
    isCompliant: boolean
    delay?: number
}

export default function ComplianceCard({ items, isCompliant, delay = 0 }: ComplianceCardProps) {
    return (
        <motion.div
            className="glass-card p-4 space-y-3"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay, type: 'spring', stiffness: 300, damping: 30 }}
        >
            <div className="flex items-center justify-between">
                <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                    Mevzuat Uyumu
                </span>
                <span
                    className="text-xs font-semibold px-2.5 py-1 rounded-full"
                    style={{
                        background: isCompliant ? 'rgba(34,197,94,0.12)' : 'rgba(239,68,68,0.12)',
                        color: isCompliant ? 'var(--green)' : 'var(--red)',
                        border: `1px solid ${isCompliant ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}`,
                    }}
                >
                    {isCompliant ? '✓ Uygun' : '✗ İhlal Var'}
                </span>
            </div>

            <div className="space-y-2.5">
                {items.map((item, i) => {
                    const ratio = Math.min(item.actual / item.limit, 1.2)
                    const pass = item.status === 'pass'

                    return (
                        <motion.div
                            key={i}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: delay + 0.1 + i * 0.08 }}
                        >
                            <div className="flex items-center justify-between mb-1">
                                <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                                    {item.label}
                                </span>
                                <span className="text-xs font-medium" style={{
                                    color: pass ? 'var(--green)' : 'var(--red)',
                                }}>
                                    {item.actual.toFixed(2)}{item.unit} / {item.limit.toFixed(2)}{item.unit}
                                </span>
                            </div>
                            <div className="progress-bar">
                                <motion.div
                                    className={`progress-bar-fill ${pass ? 'green' : 'red'}`}
                                    initial={{ width: 0 }}
                                    animate={{ width: `${Math.min(ratio * 100, 100)}%` }}
                                    transition={{ delay: delay + 0.2 + i * 0.1, duration: 0.6, ease: 'easeOut' }}
                                />
                            </div>
                        </motion.div>
                    )
                })}
            </div>
        </motion.div>
    )
}
