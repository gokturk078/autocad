'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { API_URL } from '@/lib/constants'

interface DXFViewerCanvasProps {
    dxfUrl: string | null
    label?: string
    className?: string
}

interface DXFEntity {
    type: string
    vertices?: { x: number; y: number }[]
    center?: { x: number; y: number }
    radius?: number
    startPoint?: { x: number; y: number }
    endPoint?: { x: number; y: number }
    layer?: string
}

interface ParsedDXF {
    entities: DXFEntity[]
}

export default function DXFViewerCanvas({ dxfUrl, label, className }: DXFViewerCanvasProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null)
    const containerRef = useRef<HTMLDivElement>(null)
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [entities, setEntities] = useState<DXFEntity[]>([])

    // Pan / zoom state
    const viewRef = useRef({ offsetX: 0, offsetY: 0, scale: 1 })
    const dragRef = useRef({ isDragging: false, startX: 0, startY: 0 })

    // Parse DXF and extract drawable entities
    const loadDXF = useCallback(async (url: string) => {
        setIsLoading(true)
        setError(null)
        try {
            const res = await fetch(`${API_URL}${url}`)
            if (!res.ok) throw new Error('Dosya indirilemedi')
            const text = await res.text()
            const parsed = parseDXFText(text)
            setEntities(parsed)
        } catch (err) {
            setError(err instanceof Error ? err.message : 'DXF yüklenemedi')
        } finally {
            setIsLoading(false)
        }
    }, [])

    // DXF text parser — pair-based (group code, value) with trimming
    function parseDXFText(text: string): DXFEntity[] {
        const result: DXFEntity[] = []
        const rawLines = text.split('\n')

        // DXF files are structured as pairs: [group_code, value]
        // Build pair array for reliable parsing
        const pairs: { code: number; value: string }[] = []
        for (let i = 0; i < rawLines.length - 1; i += 2) {
            const code = parseInt(rawLines[i].trim(), 10)
            const value = rawLines[i + 1]?.trim() ?? ''
            if (!isNaN(code)) {
                pairs.push({ code, value })
            }
        }

        let p = 0
        while (p < pairs.length) {
            // Entity start: code 0
            if (pairs[p].code === 0) {
                const entityType = pairs[p].value

                if (entityType === 'LINE') {
                    const entity: DXFEntity = { type: 'LINE', startPoint: { x: 0, y: 0 }, endPoint: { x: 0, y: 0 } }
                    p++
                    while (p < pairs.length && pairs[p].code !== 0) {
                        const { code, value } = pairs[p]
                        if (code === 10) entity.startPoint!.x = parseFloat(value)
                        else if (code === 20) entity.startPoint!.y = parseFloat(value)
                        else if (code === 11) entity.endPoint!.x = parseFloat(value)
                        else if (code === 21) entity.endPoint!.y = parseFloat(value)
                        else if (code === 8) entity.layer = value
                        p++
                    }
                    result.push(entity)

                } else if (entityType === 'CIRCLE') {
                    const entity: DXFEntity = { type: 'CIRCLE', center: { x: 0, y: 0 }, radius: 0 }
                    p++
                    while (p < pairs.length && pairs[p].code !== 0) {
                        const { code, value } = pairs[p]
                        if (code === 10) entity.center!.x = parseFloat(value)
                        else if (code === 20) entity.center!.y = parseFloat(value)
                        else if (code === 40) entity.radius = parseFloat(value)
                        else if (code === 8) entity.layer = value
                        p++
                    }
                    result.push(entity)

                } else if (entityType === 'ARC') {
                    const entity: DXFEntity = { type: 'ARC', center: { x: 0, y: 0 }, radius: 0 }
                    let startAngle = 0, endAngle = 360
                    p++
                    while (p < pairs.length && pairs[p].code !== 0) {
                        const { code, value } = pairs[p]
                        if (code === 10) entity.center!.x = parseFloat(value)
                        else if (code === 20) entity.center!.y = parseFloat(value)
                        else if (code === 40) entity.radius = parseFloat(value)
                        else if (code === 50) startAngle = parseFloat(value)
                        else if (code === 51) endAngle = parseFloat(value)
                        else if (code === 8) entity.layer = value
                        p++
                    }
                    // Convert ARC to vertices for rendering
                    const sa = (startAngle * Math.PI) / 180
                    const ea = (endAngle * Math.PI) / 180
                    const r = entity.radius || 0
                    const cx = entity.center!.x
                    const cy = entity.center!.y
                    let end = ea
                    if (end <= sa) end += Math.PI * 2
                    const steps = Math.max(8, Math.ceil(((end - sa) / (Math.PI * 2)) * 36))
                    const verts: { x: number; y: number }[] = []
                    for (let s = 0; s <= steps; s++) {
                        const a = sa + (end - sa) * (s / steps)
                        verts.push({ x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) })
                    }
                    result.push({ type: 'LWPOLYLINE', vertices: verts, layer: entity.layer })

                } else if (entityType === 'LWPOLYLINE') {
                    const entity: DXFEntity = { type: 'LWPOLYLINE', vertices: [] }
                    let currentX = 0
                    p++
                    while (p < pairs.length && pairs[p].code !== 0) {
                        const { code, value } = pairs[p]
                        if (code === 10) currentX = parseFloat(value)
                        else if (code === 20) entity.vertices!.push({ x: currentX, y: parseFloat(value) })
                        else if (code === 8) entity.layer = value
                        p++
                    }
                    if (entity.vertices!.length > 0) result.push(entity)

                } else {
                    p++
                }
            } else {
                p++
            }
        }
        return result
    }

    // Fit to view
    const fitToView = useCallback(() => {
        if (!entities.length || !canvasRef.current) return
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity

        for (const e of entities) {
            if (e.type === 'LINE') {
                minX = Math.min(minX, e.startPoint!.x, e.endPoint!.x)
                minY = Math.min(minY, e.startPoint!.y, e.endPoint!.y)
                maxX = Math.max(maxX, e.startPoint!.x, e.endPoint!.x)
                maxY = Math.max(maxY, e.startPoint!.y, e.endPoint!.y)
            } else if (e.type === 'CIRCLE') {
                minX = Math.min(minX, e.center!.x - e.radius!)
                minY = Math.min(minY, e.center!.y - e.radius!)
                maxX = Math.max(maxX, e.center!.x + e.radius!)
                maxY = Math.max(maxY, e.center!.y + e.radius!)
            } else if (e.type === 'LWPOLYLINE' && e.vertices?.length) {
                for (const v of e.vertices) {
                    minX = Math.min(minX, v.x)
                    minY = Math.min(minY, v.y)
                    maxX = Math.max(maxX, v.x)
                    maxY = Math.max(maxY, v.y)
                }
            }
        }

        if (!isFinite(minX)) return

        const canvas = canvasRef.current
        const w = canvas.width
        const h = canvas.height
        const dw = maxX - minX || 1
        const dh = maxY - minY || 1
        const scale = Math.min(w / dw, h / dh) * 0.85
        const cx = (minX + maxX) / 2
        const cy = (minY + maxY) / 2

        viewRef.current = {
            offsetX: w / 2 - cx * scale,
            offsetY: h / 2 + cy * scale,
            scale,
        }
        draw()
    }, [entities])

    // Draw
    const draw = useCallback(() => {
        const canvas = canvasRef.current
        if (!canvas) return
        const ctx = canvas.getContext('2d')
        if (!ctx) return

        const { offsetX, offsetY, scale } = viewRef.current

        ctx.clearRect(0, 0, canvas.width, canvas.height)
        ctx.fillStyle = '#0a0a0a'
        ctx.fillRect(0, 0, canvas.width, canvas.height)

        // Grid
        ctx.strokeStyle = 'rgba(255,255,255,0.03)'
        ctx.lineWidth = 1
        const gridSize = 50
        for (let x = offsetX % gridSize; x < canvas.width; x += gridSize) {
            ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke()
        }
        for (let y = offsetY % gridSize; y < canvas.height; y += gridSize) {
            ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke()
        }

        // Transform: DXF Y is up, canvas Y is down
        const tx = (x: number) => x * scale + offsetX
        const ty = (y: number) => -y * scale + offsetY

        ctx.lineWidth = 1.2
        ctx.lineCap = 'round'
        ctx.lineJoin = 'round'

        for (const e of entities) {
            // Color by layer
            if (e.layer?.includes('WALL')) ctx.strokeStyle = 'rgba(255,255,255,0.9)'
            else if (e.layer?.includes('DOOR')) ctx.strokeStyle = 'rgba(212,175,55,0.8)'
            else if (e.layer?.includes('GLAZ') || e.layer?.includes('WIND')) ctx.strokeStyle = 'rgba(6,182,212,0.7)'
            else if (e.layer?.includes('DIM')) ctx.strokeStyle = 'rgba(34,197,94,0.5)'
            else if (e.layer?.includes('TEXT') || e.layer?.includes('TITLE')) ctx.strokeStyle = 'rgba(255,255,255,0.3)'
            else if (e.layer?.includes('FURN')) ctx.strokeStyle = 'rgba(139,92,246,0.5)'
            else ctx.strokeStyle = 'rgba(255,255,255,0.6)'

            if (e.type === 'LINE' && e.startPoint && e.endPoint) {
                ctx.beginPath()
                ctx.moveTo(tx(e.startPoint.x), ty(e.startPoint.y))
                ctx.lineTo(tx(e.endPoint.x), ty(e.endPoint.y))
                ctx.stroke()
            } else if (e.type === 'CIRCLE' && e.center && e.radius) {
                ctx.beginPath()
                ctx.arc(tx(e.center.x), ty(e.center.y), e.radius * scale, 0, Math.PI * 2)
                ctx.stroke()
            } else if (e.type === 'LWPOLYLINE' && e.vertices?.length) {
                ctx.beginPath()
                ctx.moveTo(tx(e.vertices[0].x), ty(e.vertices[0].y))
                for (let k = 1; k < e.vertices.length; k++) {
                    ctx.lineTo(tx(e.vertices[k].x), ty(e.vertices[k].y))
                }
                ctx.stroke()
            }
        }

        // Crosshair at center
        const cw = canvas.width / 2
        const ch = canvas.height / 2
        ctx.strokeStyle = 'rgba(212,175,55,0.15)'
        ctx.lineWidth = 0.5
        ctx.setLineDash([4, 4])
        ctx.beginPath(); ctx.moveTo(cw - 20, ch); ctx.lineTo(cw + 20, ch); ctx.stroke()
        ctx.beginPath(); ctx.moveTo(cw, ch - 20); ctx.lineTo(cw, ch + 20); ctx.stroke()
        ctx.setLineDash([])
    }, [entities])

    // Resize canvas
    useEffect(() => {
        const container = containerRef.current
        const canvas = canvasRef.current
        if (!container || !canvas) return

        const ro = new ResizeObserver(() => {
            const dpr = window.devicePixelRatio || 1
            canvas.width = container.clientWidth * dpr
            canvas.height = container.clientHeight * dpr
            canvas.style.width = `${container.clientWidth}px`
            canvas.style.height = `${container.clientHeight}px`
            const ctx = canvas.getContext('2d')
            if (ctx) ctx.scale(dpr, dpr)
            if (entities.length) fitToView()
            else draw()
        })
        ro.observe(container)
        return () => ro.disconnect()
    }, [entities, fitToView, draw])

    // Load DXF when URL changes
    useEffect(() => {
        if (dxfUrl) loadDXF(dxfUrl)
    }, [dxfUrl, loadDXF])

    // Fit to view when entities change
    useEffect(() => {
        if (entities.length) fitToView()
    }, [entities, fitToView])

    // Mouse handlers
    const handleWheel = useCallback((e: React.WheelEvent) => {
        e.preventDefault()
        const factor = e.deltaY < 0 ? 1.12 : 0.88
        viewRef.current.scale *= factor
        // Zoom toward mouse
        const rect = canvasRef.current!.getBoundingClientRect()
        const mx = e.clientX - rect.left
        const my = e.clientY - rect.top
        viewRef.current.offsetX = mx - (mx - viewRef.current.offsetX) * factor
        viewRef.current.offsetY = my - (my - viewRef.current.offsetY) * factor
        draw()
    }, [draw])

    const handleMouseDown = useCallback((e: React.MouseEvent) => {
        dragRef.current = { isDragging: true, startX: e.clientX, startY: e.clientY }
    }, [])

    const handleMouseMove = useCallback((e: React.MouseEvent) => {
        if (!dragRef.current.isDragging) return
        const dx = e.clientX - dragRef.current.startX
        const dy = e.clientY - dragRef.current.startY
        viewRef.current.offsetX += dx
        viewRef.current.offsetY += dy
        dragRef.current.startX = e.clientX
        dragRef.current.startY = e.clientY
        draw()
    }, [draw])

    const handleMouseUp = useCallback(() => {
        dragRef.current.isDragging = false
    }, [])

    const handleDoubleClick = useCallback(() => {
        fitToView()
    }, [fitToView])

    return (
        <motion.div
            className={`dxf-canvas-container relative ${className || ''}`}
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ type: 'spring', stiffness: 200, damping: 25 }}
            style={{ minHeight: 400 }}
        >
            {/* Label */}
            {label && (
                <div className="absolute top-3 left-3 z-10 px-3 py-1.5 rounded-lg text-xs font-medium"
                    style={{
                        background: 'rgba(0,0,0,0.6)',
                        backdropFilter: 'blur(8px)',
                        color: 'var(--gold)',
                        border: '1px solid rgba(212,175,55,0.2)',
                    }}>
                    {label}
                </div>
            )}

            {/* Canvas */}
            <div ref={containerRef} className="w-full h-full" style={{ minHeight: 400 }}>
                <canvas
                    ref={canvasRef}
                    onWheel={handleWheel}
                    onMouseDown={handleMouseDown}
                    onMouseMove={handleMouseMove}
                    onMouseUp={handleMouseUp}
                    onMouseLeave={handleMouseUp}
                    onDoubleClick={handleDoubleClick}
                    style={{ cursor: dragRef.current.isDragging ? 'grabbing' : 'grab' }}
                />
            </div>

            {/* Toolbar */}
            <div className="dxf-toolbar">
                <button onClick={() => { viewRef.current.scale *= 1.3; draw() }} title="Yakınlaştır">+</button>
                <button onClick={() => { viewRef.current.scale *= 0.7; draw() }} title="Uzaklaştır">−</button>
                <button onClick={fitToView} title="Ekrana Sığdır">⊞</button>
            </div>

            {/* Loading */}
            {isLoading && (
                <div className="absolute inset-0 flex items-center justify-center" style={{ background: 'rgba(10,10,10,0.8)' }}>
                    <motion.div
                        className="w-10 h-10 rounded-full"
                        style={{ border: '2px solid var(--gold)', borderTopColor: 'transparent' }}
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                    />
                </div>
            )}

            {/* Error */}
            {error && (
                <div className="absolute inset-0 flex items-center justify-center" style={{ background: 'rgba(10,10,10,0.8)' }}>
                    <p className="text-sm" style={{ color: 'var(--red)' }}>⚠ {error}</p>
                </div>
            )}

            {/* Empty state */}
            {!isLoading && !error && !entities.length && !dxfUrl && (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-2">
                    <span className="text-3xl" style={{ opacity: 0.2 }}>⬡</span>
                    <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                        Bir pafta seçin
                    </p>
                </div>
            )}
        </motion.div>
    )
}
