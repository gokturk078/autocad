'use client'

import {
    createContext,
    useCallback,
    useContext,
    useEffect,
    useMemo,
    useState,
    type ReactNode,
} from 'react'

import { useWebSocket } from '@/hooks/useWebSocket'
import type {
    AnalysisResult,
    ConnectionStatus,
    ProjectModel,
    WebSocketMessage,
} from '@/lib/types'

interface ProjectStateContextValue {
    project: ProjectModel | null
    analysis: AnalysisResult | null
    wsStatus: ConnectionStatus
    lastUpdated: Date | null
    isAnalyzing: boolean
    error: string | null
    reconnect: () => void
}

const ProjectStateContext = createContext<ProjectStateContextValue>({
    project: null,
    analysis: null,
    wsStatus: 'disconnected',
    lastUpdated: null,
    isAnalyzing: false,
    error: null,
    reconnect: () => { },
})

export function ProjectStateProvider({ children }: { children: ReactNode }) {
    const { status, lastMessage, reconnect } = useWebSocket()

    const [project, setProject] = useState<ProjectModel | null>(null)
    const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
    const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
    const [isAnalyzing, setIsAnalyzing] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const handleMessage = useCallback((msg: WebSocketMessage) => {
        switch (msg.type) {
            case 'project_update': {
                const proj = msg.payload as unknown as ProjectModel
                setProject(proj)
                setLastUpdated(new Date())
                setIsAnalyzing(true)
                setError(null)
                break
            }
            case 'ai_analysis': {
                const result = msg.payload as unknown as AnalysisResult
                setAnalysis(result)
                setIsAnalyzing(false)
                setLastUpdated(new Date())
                break
            }
            case 'error': {
                const errMsg =
                    (msg.payload as Record<string, string>).message ?? 'Bilinmeyen hata'
                setError(errMsg)
                setIsAnalyzing(false)
                break
            }
            default:
                break
        }
    }, [])

    useEffect(() => {
        if (lastMessage) {
            handleMessage(lastMessage)
        }
    }, [lastMessage, handleMessage])

    const value = useMemo<ProjectStateContextValue>(
        () => ({
            project,
            analysis,
            wsStatus: status,
            lastUpdated,
            isAnalyzing,
            error,
            reconnect,
        }),
        [project, analysis, status, lastUpdated, isAnalyzing, error, reconnect]
    )

    return (
        <ProjectStateContext.Provider value={value}>
            {children}
        </ProjectStateContext.Provider>
    )
}

export function useProjectState(): ProjectStateContextValue {
    return useContext(ProjectStateContext)
}
