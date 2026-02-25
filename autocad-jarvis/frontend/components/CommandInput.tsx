'use client'

import { useState, useCallback, useRef } from 'react'
import VoiceOrb from './VoiceOrb'
import { useVoiceCommand } from '@/hooks/useVoiceCommand'
import { API_URL } from '@/lib/constants'

interface CommandHistoryItem {
    id: string
    text: string
    timestamp: Date
    status: 'pending' | 'success' | 'error'
    result?: string
}

export default function CommandInput() {
    const [inputText, setInputText] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [history, setHistory] = useState<CommandHistoryItem[]>([])
    const inputRef = useRef<HTMLInputElement>(null)

    const handleCommand = useCallback(async (text: string) => {
        if (!text.trim()) return

        const id = crypto.randomUUID()
        setHistory((prev) => [
            { id, text, timestamp: new Date(), status: 'pending' },
            ...prev.slice(0, 9),
        ])

        setIsLoading(true)
        setInputText('')

        try {
            const response = await fetch(`${API_URL}/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: text }),
            })

            if (!response.ok) {
                const err = await response.json()
                throw new Error(err.error || 'Bilinmeyen hata')
            }

            const data = await response.json()
            const filename = data.output_path?.split('/').pop() ?? 'dxf'
            setHistory((prev) =>
                prev.map((item) =>
                    item.id === id
                        ? { ...item, status: 'success' as const, result: `✓ ${filename}` }
                        : item
                )
            )
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Bilinmeyen hata'
            setHistory((prev) =>
                prev.map((item) =>
                    item.id === id
                        ? { ...item, status: 'error' as const, result: `✗ ${message}` }
                        : item
                )
            )
        } finally {
            setIsLoading(false)
            resetTranscript()
        }
    }, [])

    const {
        voiceState,
        transcript,
        isSupported,
        startListening,
        stopListening,
        resetTranscript,
    } = useVoiceCommand(handleCommand)

    const handleSubmit = useCallback(
        (e: React.FormEvent) => {
            e.preventDefault()
            if (inputText.trim()) handleCommand(inputText.trim())
        },
        [inputText, handleCommand]
    )

    const handleRerun = useCallback(
        (text: string) => {
            handleCommand(text)
        },
        [handleCommand]
    )

    return (
        <div className="space-y-3">
            {/* VoiceOrb */}
            <div className="glass-card p-4 flex flex-col items-center gap-2">
                <p className="text-xs mb-1" style={{ color: 'var(--text-secondary)' }}>
                    Sesli veya yazılı komut ver
                </p>
                <VoiceOrb
                    voiceState={voiceState}
                    transcript={transcript}
                    isSupported={isSupported}
                    onStart={startListening}
                    onStop={stopListening}
                />
            </div>

            {/* Text input */}
            <form onSubmit={handleSubmit} className="glass-card p-3 flex gap-2">
                <input
                    ref={inputRef}
                    type="text"
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    placeholder="120m² 3+1 modern konut planı oluştur..."
                    disabled={isLoading}
                    className="flex-1 bg-transparent text-sm outline-none disabled:opacity-50"
                    style={{
                        color: 'var(--text-primary)',
                    }}
                />
                <button
                    type="submit"
                    disabled={isLoading || !inputText.trim()}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed"
                    style={{
                        background: 'rgba(212, 175, 55, 0.2)',
                        color: 'var(--gold)',
                        border: '1px solid rgba(212, 175, 55, 0.3)',
                    }}
                >
                    {isLoading ? '⟳' : '↵'}
                </button>
            </form>

            {/* Command history */}
            {history.length > 0 && (
                <div className="glass-card p-3 space-y-2">
                    <p className="text-xs mb-2" style={{ color: 'var(--text-secondary)' }}>
                        Son Komutlar
                    </p>
                    {history.map((item) => (
                        <div
                            key={item.id}
                            className="flex items-start gap-2 cursor-pointer hover:opacity-80 transition-opacity"
                            onClick={() => handleRerun(item.text)}
                            title="Tekrar çalıştır"
                        >
                            <span className="text-xs mt-0.5">
                                {item.status === 'pending' && '⟳'}
                                {item.status === 'success' && '✓'}
                                {item.status === 'error' && '✗'}
                            </span>
                            <div className="flex-1 min-w-0">
                                <p className="text-xs truncate" style={{ color: 'var(--text-primary)' }}>
                                    {item.text}
                                </p>
                                {item.result && (
                                    <p
                                        className="text-xs"
                                        style={{
                                            color: item.status === 'error' ? 'var(--red)' : 'var(--green)',
                                        }}
                                    >
                                        {item.result}
                                    </p>
                                )}
                            </div>
                            <span className="text-xs shrink-0" style={{ color: 'var(--text-secondary)' }}>
                                {item.timestamp.toLocaleTimeString('tr-TR', {
                                    hour: '2-digit',
                                    minute: '2-digit',
                                })}
                            </span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
