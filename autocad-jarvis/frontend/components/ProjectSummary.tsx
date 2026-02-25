'use client'

import { useProjectState } from '@/hooks/useProjectState'

function StatBox({
    value,
    label,
    loading,
}: {
    value: string
    label: string
    loading: boolean
}) {
    return (
        <div className="glass-card flex flex-col items-center justify-center p-3 text-center">
            {loading ? (
                <div
                    className="h-6 w-16 rounded animate-shimmer"
                    style={{
                        background:
                            'linear-gradient(90deg, transparent 25%, rgba(255,255,255,0.06) 50%, transparent 75%)',
                        backgroundSize: '200% 100%',
                    }}
                />
            ) : (
                <span className="text-xl font-bold gold-text">{value}</span>
            )}
            <span className="mt-1 text-xs" style={{ color: 'var(--text-secondary)' }}>
                {label}
            </span>
        </div>
    )
}

export default function ProjectSummary() {
    const { project, isAnalyzing } = useProjectState()

    const loading = isAnalyzing && !project

    return (
        <div className="animate-slide-up">
            {/* 2×2 stat grid */}
            <div className="grid grid-cols-2 gap-3 mb-4">
                <StatBox
                    value={project ? `${project.total_area_m2.toFixed(1)} m²` : '─'}
                    label="Toplam Alan"
                    loading={loading}
                />
                <StatBox
                    value={project ? `${project.room_count}` : '─'}
                    label="Oda Sayısı"
                    loading={loading}
                />
                <StatBox
                    value={project ? `${project.door_count}` : '─'}
                    label="Kapı"
                    loading={loading}
                />
                <StatBox
                    value={project ? `${project.total_wall_length_m.toFixed(1)} m` : '─'}
                    label="Duvar"
                    loading={loading}
                />
            </div>

            {/* Room badges */}
            {project && project.rooms.length > 0 && (
                <div className="mb-2">
                    <p className="text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
                        Odalar
                    </p>
                    <div className="flex flex-wrap gap-2">
                        {project.rooms.map((room) => (
                            <span
                                key={room.id}
                                className="glass-card px-2.5 py-1 text-xs font-medium"
                                style={{ borderRadius: 8 }}
                            >
                                {room.name}{' '}
                                <span className="gold-text">{room.area_m2.toFixed(1)}m²</span>
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {/* Parse performance */}
            {project && (
                <p className="text-xs mt-3" style={{ color: 'var(--text-secondary)' }}>
                    Parse süresi: {project.parse_duration_ms.toFixed(0)}ms ·{' '}
                    {project.wall_count} duvar segmenti · {project.window_count} pencere
                </p>
            )}
        </div>
    )
}
