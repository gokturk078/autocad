'use client'

import { useState, useCallback, useRef } from 'react'
import { API_URL } from '@/lib/constants'
import type { GeneratedProject, GenerationPhase, GenerateFormResponse } from '@/lib/types'

interface UseGenerateProjectReturn {
    phase: GenerationPhase
    project: GeneratedProject | null
    error: string | null
    prompt: string
    aiModel: string | null
    generate: (prompt: string) => Promise<void>
    reset: () => void
}

/**
 * Sprint 6: Prompt → GPT-4.1 AI Architect → ProjectBuilder → DXF
 * Uses /project/generate-nlp endpoint (no more regex parsing!)
 */
export function useGenerateProject(): UseGenerateProjectReturn {
    const [phase, setPhase] = useState<GenerationPhase>('idle')
    const [project, setProject] = useState<GeneratedProject | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [prompt, setPrompt] = useState('')
    const [aiModel, setAiModel] = useState<string | null>(null)
    const abortRef = useRef(false)

    const generate = useCallback(async (userPrompt: string) => {
        setPrompt(userPrompt)
        setError(null)
        setProject(null)
        setAiModel(null)
        abortRef.current = false

        // Phase simulation: show timeline steps while GPT + backend work
        const phases: GenerationPhase[] = ['parsing', 'checking', 'planning', 'generating', 'packaging']
        const phaseDurations = [600, 600, 800, 1000, 500] // Gemini 2.5 Pro: ~3-5s total

        let phaseIdx = 0
        setPhase(phases[0])

        const phaseTimer = setInterval(() => {
            phaseIdx++
            if (phaseIdx < phases.length && !abortRef.current) {
                setPhase(phases[phaseIdx])
            } else {
                clearInterval(phaseTimer)
            }
        }, phaseDurations[phaseIdx] || 1500)

        try {
            // ─── Send prompt directly to GPT-powered NLP endpoint ───
            const res = await fetch(`${API_URL}/project/generate-nlp`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: userPrompt }),
            })

            clearInterval(phaseTimer)

            if (!res.ok) {
                const err = await res.json()
                throw new Error(err.error || err.message_tr || 'Bilinmeyen hata')
            }

            const data: GenerateFormResponse & { ai_model?: string } = await res.json()

            if (data.status !== 'success') {
                throw new Error(data.message_tr || 'Üretim başarısız')
            }

            // Show all phases as complete before transitioning
            for (const p of phases) {
                if (abortRef.current) return
                setPhase(p)
                await sleep(250)
            }

            setProject(data.project)
            setAiModel(data.ai_model || null)
            setPhase('done')
        } catch (err) {
            clearInterval(phaseTimer)
            setError(err instanceof Error ? err.message : 'Bilinmeyen hata')
            setPhase('error')
        }
    }, [])

    const reset = useCallback(() => {
        abortRef.current = true
        setPhase('idle')
        setProject(null)
        setError(null)
        setPrompt('')
        setAiModel(null)
    }, [])

    return { phase, project, error, prompt, aiModel, generate, reset }
}

function sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms))
}
