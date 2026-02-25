'use client'

import { useCallback, useState } from 'react'
import { motion } from 'framer-motion'
import { API_URL } from '@/lib/constants'
import type { DXFFileInfo } from '@/lib/types'

interface DownloadGridProps {
    files: Record<string, DXFFileInfo>
    projectId: string
    onSelectFile?: (url: string, label: string) => void
    activeFile?: string
    delay?: number
}

function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`
    return `${(bytes / 1024).toFixed(0)} KB`
}

const FILE_ICONS: Record<string, string> = {
    'Vaziyet': '🏗️',
    'Kat': '📐',
    'Kesit': '✂️',
    'Görünüş': '🏠',
    'Çatı': '🏛️',
    'Alan': '📊',
}

function getIcon(label: string): string {
    for (const [key, icon] of Object.entries(FILE_ICONS)) {
        if (label.includes(key)) return icon
    }
    return '📄'
}

export default function DownloadGrid({ files, projectId, onSelectFile, activeFile, delay = 0 }: DownloadGridProps) {
    const [downloading, setDownloading] = useState<string | null>(null)

    const handleDownload = useCallback(async (url: string, filename: string) => {
        setDownloading(filename)
        try {
            const res = await fetch(`${API_URL}${url}`)
            const blob = await res.blob()
            const a = document.createElement('a')
            a.href = URL.createObjectURL(blob)
            a.download = filename
            document.body.appendChild(a)
            a.click()
            document.body.removeChild(a)
            URL.revokeObjectURL(a.href)
        } catch (err) {
            console.error('Download failed:', err)
        } finally {
            setDownloading(null)
        }
    }, [])

    const handleZipDownload = useCallback(async () => {
        setDownloading('zip')
        try {
            const res = await fetch(`${API_URL}/project/download-zip/${projectId}`)
            const blob = await res.blob()
            const a = document.createElement('a')
            a.href = URL.createObjectURL(blob)
            a.download = `proje_${projectId}.zip`
            document.body.appendChild(a)
            a.click()
            document.body.removeChild(a)
            URL.revokeObjectURL(a.href)
        } catch (err) {
            console.error('ZIP download failed:', err)
        } finally {
            setDownloading(null)
        }
    }, [projectId])

    const entries = Object.entries(files)

    return (
        <motion.div
            className="space-y-3"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay, type: 'spring', stiffness: 300, damping: 30 }}
        >
            {/* ZIP download button */}
            <button
                className="w-full btn-primary flex items-center justify-center gap-2 gold-glow"
                onClick={handleZipDownload}
                disabled={downloading === 'zip'}
                style={{ padding: '12px 24px', borderRadius: 14, fontSize: 14 }}
            >
                {downloading === 'zip' ? (
                    <motion.span
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                    >⟳</motion.span>
                ) : (
                    <span>📥</span>
                )}
                <span>{downloading === 'zip' ? 'İndiriliyor...' : 'Tüm Projeyi İndir (ZIP)'}</span>
            </button>

            {/* File list */}
            <div className="space-y-1.5 max-h-[280px] overflow-y-auto pr-1">
                {entries.map(([label, info], i) => {
                    const isActive = activeFile === info.download_url

                    return (
                        <motion.div
                            key={label}
                            className="glass-card flex items-center gap-3 px-3 py-2.5 cursor-pointer group"
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: delay + 0.05 + i * 0.04 }}
                            onClick={() => onSelectFile?.(info.download_url, label)}
                            style={{
                                borderColor: isActive ? 'rgba(212,175,55,0.3)' : undefined,
                                borderRadius: 12,
                            }}
                        >
                            <span className="text-sm">{getIcon(label)}</span>

                            <div className="flex-1 min-w-0">
                                <p className="text-xs font-medium truncate" style={{
                                    color: isActive ? 'var(--gold)' : 'var(--text-primary)',
                                }}>
                                    {label}
                                </p>
                                <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                                    {info.filename} · {formatSize(info.size_bytes)}
                                </p>
                            </div>

                            <button
                                className="opacity-0 group-hover:opacity-100 transition-opacity text-xs px-2 py-1 rounded-md"
                                style={{
                                    background: 'rgba(255,255,255,0.06)',
                                    color: 'var(--text-secondary)',
                                }}
                                onClick={(e) => {
                                    e.stopPropagation()
                                    handleDownload(info.download_url, info.filename)
                                }}
                            >
                                {downloading === info.filename ? '⟳' : '↓'}
                            </button>
                        </motion.div>
                    )
                })}
            </div>
        </motion.div>
    )
}
