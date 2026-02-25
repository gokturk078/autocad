'use client'

import { useState, useRef, useCallback, useEffect } from 'react'

// Web Speech API types (not included in default TS lib)
interface SpeechRecognitionEvent extends Event {
    readonly resultIndex: number
    readonly results: SpeechRecognitionResultList
}
interface SpeechRecognitionErrorEvent extends Event {
    readonly error: string
    readonly message: string
}
interface SpeechRecognition extends EventTarget {
    lang: string
    continuous: boolean
    interimResults: boolean
    maxAlternatives: number
    onstart: ((this: SpeechRecognition, ev: Event) => void) | null
    onresult: ((this: SpeechRecognition, ev: SpeechRecognitionEvent) => void) | null
    onerror: ((this: SpeechRecognition, ev: SpeechRecognitionErrorEvent) => void) | null
    onend: ((this: SpeechRecognition, ev: Event) => void) | null
    start(): void
    stop(): void
    abort(): void
}

export type VoiceState = 'idle' | 'listening' | 'processing' | 'error'

interface UseVoiceCommandReturn {
    voiceState: VoiceState
    transcript: string
    isSupported: boolean
    startListening: () => void
    stopListening: () => void
    resetTranscript: () => void
}

export function useVoiceCommand(
    onFinalResult: (text: string) => void
): UseVoiceCommandReturn {
    const [voiceState, setVoiceState] = useState<VoiceState>('idle')
    const [transcript, setTranscript] = useState('')
    const [isSupported, setIsSupported] = useState(false)
    const recognitionRef = useRef<SpeechRecognition | null>(null)
    const isMountedRef = useRef(true)

    useEffect(() => {
        isMountedRef.current = true
        const supported =
            typeof window !== 'undefined' &&
            ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)
        setIsSupported(supported)
        return () => {
            isMountedRef.current = false
        }
    }, [])

    const stopListening = useCallback(() => {
        recognitionRef.current?.stop()
        setVoiceState('idle')
    }, [])

    const startListening = useCallback(() => {
        if (!isSupported) {
            console.warn('[VOICE] Web Speech API desteklenmiyor')
            setVoiceState('error')
            return
        }

        /* eslint-disable @typescript-eslint/no-explicit-any */
        const SpeechRecognitionAPI =
            (window as any).SpeechRecognition ||
            (window as any).webkitSpeechRecognition

        const recognition = new SpeechRecognitionAPI() as SpeechRecognition
        /* eslint-enable @typescript-eslint/no-explicit-any */

        recognition.lang = 'tr-TR'
        recognition.continuous = false
        recognition.interimResults = true
        recognition.maxAlternatives = 1

        recognition.onstart = () => {
            if (!isMountedRef.current) return
            setVoiceState('listening')
            setTranscript('')
            console.log('[VOICE] INFO: Dinleniyor...')
        }

        recognition.onresult = (event: SpeechRecognitionEvent) => {
            if (!isMountedRef.current) return

            let interimTranscript = ''
            let finalTranscript = ''

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const result = event.results[i]
                if (result.isFinal) {
                    finalTranscript += result[0].transcript
                } else {
                    interimTranscript += result[0].transcript
                }
            }

            setTranscript(finalTranscript || interimTranscript)

            if (finalTranscript) {
                setVoiceState('processing')
                console.log(`[VOICE] INFO: Algılanan: "${finalTranscript.trim()}"`)
                onFinalResult(finalTranscript.trim())
            }
        }

        recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
            if (!isMountedRef.current) return
            console.error('[VOICE] Hata:', event.error)
            if (event.error === 'not-allowed') {
                setVoiceState('error')
            } else {
                setVoiceState('idle')
            }
        }

        recognition.onend = () => {
            if (!isMountedRef.current) return
            setVoiceState((prev: VoiceState) => (prev === 'listening' ? 'idle' : prev))
        }

        recognitionRef.current = recognition
        recognition.start()
    }, [isSupported, onFinalResult])

    const resetTranscript = useCallback(() => {
        setTranscript('')
        setVoiceState('idle')
    }, [])

    return {
        voiceState,
        transcript,
        isSupported,
        startListening,
        stopListening,
        resetTranscript,
    }
}
