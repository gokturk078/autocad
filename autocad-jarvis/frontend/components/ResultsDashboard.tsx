'use client'

import { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import DXFViewerCanvas from './DXFViewerCanvas'
import StatCard from './StatCard'
import ComplianceCard from './ComplianceCard'
import DownloadGrid from './DownloadGrid'
import type { GeneratedProject } from '@/lib/types'

interface ResultsDashboardProps {
    project: GeneratedProject
    onNewProject: () => void
}

export default function ResultsDashboard({ project, onNewProject }: ResultsDashboardProps) {
    const files = project.dxf_files || {}
    const fileEntries = Object.entries(files)
    const firstFileUrl = fileEntries.length > 0 ? fileEntries[0][1].download_url : null
    const firstFileLabel = fileEntries.length > 0 ? fileEntries[0][0] : ''

    const [activeUrl, setActiveUrl] = useState<string | null>(firstFileUrl)
    const [activeLabel, setActiveLabel] = useState<string>(firstFileLabel)

    const handleSelectFile = useCallback((url: string, label: string) => {
        setActiveUrl(url)
        setActiveLabel(label)
    }, [])

    // Build compliance items from backend taks/kaks/height format
    const compliance = project.compliance
    const isCompliant = compliance?.is_compliant !== false
    const complianceItems = [
        compliance?.taks && { label: 'TAKS', actual: compliance.taks.actual || 0, limit: compliance.taks.limit || 0.4, unit: '', status: (compliance.taks.actual || 0) <= (compliance.taks.limit || 0.4) ? 'pass' as const : 'fail' as const },
        compliance?.kaks && { label: 'KAKS', actual: compliance.kaks.actual || 0, limit: compliance.kaks.limit || 2.0, unit: '', status: (compliance.kaks.actual || 0) <= (compliance.kaks.limit || 2.0) ? 'pass' as const : 'fail' as const },
        compliance?.height && { label: 'Bina Yüksekliği', actual: compliance.height.actual || 0, limit: compliance.height.max || 15.5, unit: 'm', status: (compliance.height.actual || 0) <= (compliance.height.max || 15.5) ? 'pass' as const : 'fail' as const },
    ].filter(Boolean) as { label: string; actual: number; limit: number; unit: string; status: string }[]

    // Cost from backend
    const costMid = project.cost?.estimates_tl?.mid || 0

    // Area table
    const area = project.area_table || {}

    // Tab options for quick file switching
    const tabFiles = fileEntries.filter(([label]) =>
        label.includes('Kat') || label.includes('Kesit') || label.includes('Görünüş') || label.includes('Vaziyet')
    ).slice(0, 6)

    return (
        <motion.div
            className="flex flex-col h-screen"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{ position: 'relative', zIndex: 1 }}
        >
            {/* ── Header ─────────────────────────────────────── */}
            <motion.div
                className="flex items-center justify-between px-6 py-4"
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                style={{ borderBottom: '1px solid var(--border-glass)' }}
            >
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center"
                        style={{
                            background: 'linear-gradient(135deg, rgba(212,175,55,0.15), rgba(212,175,55,0.05))',
                            border: '1px solid rgba(212,175,55,0.2)',
                        }}>
                        <span className="text-sm">⬡</span>
                    </div>
                    <div>
                        <h1 className="text-lg font-semibold" style={{ color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
                            {project.project_name || 'Proje'}
                        </h1>
                        <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                            {project.file_count} pafta · {project.building_type}
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <span
                        className="text-xs font-medium px-3 py-1.5 rounded-full"
                        style={{
                            background: isCompliant ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
                            color: isCompliant ? 'var(--green)' : 'var(--red)',
                            border: `1px solid ${isCompliant ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}`,
                        }}
                    >
                        {isCompliant ? '✓ Mevzuata Uygun' : '✗ İhlal Mevcut'}
                    </span>
                    <button className="btn-ghost" onClick={onNewProject}>
                        + Yeni Proje
                    </button>
                </div>
            </motion.div>

            {/* ── Main Content ────────────────────────────────── */}
            <div className="flex-1 flex overflow-hidden">
                {/* Left: DXF Viewer (60%) */}
                <div className="flex-[3] flex flex-col p-4 gap-3">
                    {/* Tab bar */}
                    <div className="tab-bar">
                        {tabFiles.map(([label, info]) => (
                            <button
                                key={label}
                                className={`tab-item ${activeUrl === info.download_url ? 'active' : ''}`}
                                onClick={() => handleSelectFile(info.download_url, label)}
                            >
                                {label}
                            </button>
                        ))}
                    </div>

                    {/* Canvas */}
                    <DXFViewerCanvas
                        dxfUrl={activeUrl}
                        label={activeLabel}
                        className="flex-1"
                    />
                </div>

                {/* Right: Dashboard panels (40%) */}
                <div className="flex-[2] overflow-y-auto p-4 space-y-4"
                    style={{ borderLeft: '1px solid var(--border-glass)' }}>

                    {/* Stats */}
                    <div className="grid grid-cols-2 gap-3">
                        <StatCard
                            label="Toplam Alan" value={Number(area.total_construction_area) || 0}
                            unit="m²" icon="📐" delay={0.1}
                        />
                        <StatCard
                            label="Kat Sayısı" value={Number(area.floor_count) || 0}
                            unit="kat" icon="🏢" delay={0.15}
                        />
                        <StatCard
                            label="Daire Sayısı" value={Number(area.total_units) || 0}
                            unit="adet" icon="🏠" delay={0.2}
                        />
                        <StatCard
                            label="Tahmini Maliyet" value={costMid}
                            unit="" icon="💰" delay={0.25} format="currency"
                        />
                    </div>

                    {/* Compliance */}
                    {complianceItems.length > 0 && (
                        <ComplianceCard
                            items={complianceItems}
                            isCompliant={isCompliant}
                            delay={0.3}
                        />
                    )}

                    {/* Downloads */}
                    <div>
                        <p className="text-xs font-medium mb-2 px-1" style={{ color: 'var(--text-secondary)' }}>
                            Pafta İndirme
                        </p>
                        <DownloadGrid
                            files={files}
                            projectId={project.project_id}
                            onSelectFile={handleSelectFile}
                            activeFile={activeUrl || undefined}
                            delay={0.4}
                        />
                    </div>
                </div>
            </div>
        </motion.div>
    )
}
