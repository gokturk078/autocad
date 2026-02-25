'use client'

import { useCallback } from 'react'
import type { VoiceState } from '@/hooks/useVoiceCommand'

interface VoiceOrbProps {
    voiceState: VoiceState
    transcript: string
    isSupported: boolean
    onStart: () => void
    onStop: () => void
}

export default function VoiceOrb({
    voiceState,
    transcript,
    isSupported,
    onStart,
    onStop,
}: VoiceOrbProps) {
    const handleClick = useCallback(() => {
        if (voiceState === 'listening') {
            onStop()
        } else if (voiceState === 'idle' || voiceState === 'error') {
            onStart()
        }
    }, [voiceState, onStart, onStop])

    if (!isSupported) {
        return (
            <div className="text-xs text-center px-3" style={{ color: 'var(--text-secondary)' }}>
                Ses komutları bu tarayıcıda desteklenmiyor.
                <br />
                Chrome veya Edge kullanın.
            </div>
        )
    }

    const iconMap: Record<VoiceState, string> = {
        idle: '🎙️',
        listening: '⬡',
        processing: '⟳',
        error: '⚠️',
    }

    return (
        <div className="flex flex-col items-center gap-3">
            <button
                className={`
          relative w-16 h-16 rounded-full cursor-pointer
          flex items-center justify-center
          backdrop-blur-xl border
          transition-all duration-500 ease-out select-none
          ${voiceState === 'idle' ? 'bg-white/[0.04] border-white/10 hover:bg-white/[0.08] hover:border-[var(--gold)]/40 shadow-[0_0_16px_rgba(212,175,55,0.15)] hover:shadow-[0_0_24px_rgba(212,175,55,0.35)]' : ''}
          ${voiceState === 'listening' ? 'bg-cyan-500/20 border-[var(--cyan)]/50 shadow-[0_0_32px_rgba(0,188,212,0.5)] scale-110' : ''}
          ${voiceState === 'processing' ? 'bg-[var(--gold)]/10 border-[var(--gold)]/50 shadow-[0_0_28px_rgba(212,175,55,0.4)]' : ''}
          ${voiceState === 'error' ? 'bg-red-500/10 border-red-500/40' : ''}
        `}
                onClick={handleClick}
                disabled={voiceState === 'processing'}
                title={voiceState === 'listening' ? 'Durdur' : 'Sesli Komut'}
            >
                <span
                    className={`text-2xl ${voiceState === 'processing' ? 'animate-spin' : ''}`}
                    style={{ display: 'inline-block' }}
                >
                    {iconMap[voiceState]}
                </span>

                {voiceState === 'listening' && (
                    <>
                        <span className="absolute inset-0 rounded-full border border-[var(--cyan)]/30 animate-ping" />
                        <span className="absolute inset-[-6px] rounded-full border border-[var(--cyan)]/20 animate-ping" style={{ animationDelay: '0.3s' }} />
                    </>
                )}
            </button>

            <div className="min-h-[20px] text-center px-2">
                {voiceState === 'listening' && (
                    <p className="text-xs animate-pulse" style={{ color: 'var(--cyan)' }}>
                        {transcript || 'Dinleniyor...'}
                    </p>
                )}
                {voiceState === 'processing' && (
                    <p className="text-xs" style={{ color: 'var(--gold)' }}>İşleniyor...</p>
                )}
                {voiceState === 'idle' && !transcript && (
                    <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>Sesli komut için tıkla</p>
                )}
            </div>
        </div>
    )
}
