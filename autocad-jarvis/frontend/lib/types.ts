/** Shared TypeScript interfaces — mirrors backend models. */

// ── Existing types (FAZ 1-2) ──────────────────────────────

export interface RoomModel {
    id: string
    name: string
    area_m2: number
    width: number
    height: number
    x: number
    y: number
    layer: string
}

export interface ProjectModel {
    filename: string
    filepath: string
    parsed_at: string
    total_area_m2: number
    room_count: number
    rooms: RoomModel[]
    wall_count: number
    total_wall_length_m: number
    door_count: number
    window_count: number
    layers: string[]
    parse_duration_ms: number
}

export interface AnalysisResult {
    summary_tr: string
    quick_stats: Record<string, unknown>
    generated_at: string
    model_used: string
    tokens_used: number
}

export type MessageType =
    | 'project_update'
    | 'ai_analysis'
    | 'watcher_status'
    | 'error'
    | 'ping'
    | 'pong'

export interface WebSocketMessage {
    type: MessageType
    timestamp: string
    payload: Record<string, unknown>
}

export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected' | 'error'


// ── Sprint 4 API Types ────────────────────────────────────

export interface DXFFileInfo {
    filename: string
    size_bytes: number
    download_url: string
}

export interface ComplianceItem {
    label: string
    parameter: string
    actual: number
    limit: number
    unit: string
    status: 'pass' | 'fail'
}

export interface ComplianceRatio {
    actual: number
    limit?: number
    max?: number
    required?: number
    provided?: number
}

export interface ComplianceResult {
    is_compliant: boolean
    error_count: number
    warning_count: number
    taks?: ComplianceRatio
    kaks?: ComplianceRatio
    height?: ComplianceRatio
    parking?: ComplianceRatio
    violations?: Array<{ code: string; severity: string; message: string }>
    summary_tr?: string
    [key: string]: unknown
}

export interface CostEstimate {
    total_area_m2: number
    unit_costs_tl: { low: number; mid: number; high: number }
    estimates_tl: { low: number; mid: number; high: number }
    currency: string
    note: string
    [key: string]: unknown
}

export interface StaircaseInfo {
    riser_count: number
    riser_height_cm: number
    tread_depth_cm: number
    stair_width_m: number
    formula: string
    total_area_m2: number
}

export interface GeneratedProject {
    project_id: string
    project_name: string
    building_type: string
    created_at: string
    file_count: number
    files: string[]
    zip_available: boolean
    download_url: string
    compliance: ComplianceResult
    cost: CostEstimate
    area_table: Record<string, unknown>
    staircase: StaircaseInfo
    dxf_files: Record<string, DXFFileInfo>
}

export interface GenerateFormResponse {
    status: 'success' | 'error'
    project_id: string
    project: GeneratedProject
    message_tr: string
}

export type GenerationPhase =
    | 'idle'
    | 'parsing'
    | 'checking'
    | 'planning'
    | 'generating'
    | 'packaging'
    | 'done'
    | 'error'

export interface GenerationStep {
    id: GenerationPhase
    label: string
    description: string
    icon: string
    duration?: number
}

export const GENERATION_STEPS: GenerationStep[] = [
    { id: 'parsing', label: 'Proje Analizi', description: 'Mimari gereksinimler çıkarılıyor...', icon: '🔍' },
    { id: 'checking', label: 'Mevzuat Kontrolü', description: 'İmar yönetmeliği doğrulanıyor...', icon: '📋' },
    { id: 'planning', label: 'Kat Planlaması', description: 'Oda yerleşimleri hesaplanıyor...', icon: '📐' },
    { id: 'generating', label: 'DXF Üretimi', description: '13 pafta çiziliyor...', icon: '⚙️' },
    { id: 'packaging', label: 'Paketleme', description: 'Proje paketi hazırlanıyor...', icon: '📦' },
]
