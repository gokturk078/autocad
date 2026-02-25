import type { Metadata } from 'next'
import type { ReactNode } from 'react'

import './globals.css'

export const metadata: Metadata = {
    title: 'JARVIS Copilot',
    description:
        'AutoCAD JARVIS AI Copilot — Mimarlar için gerçek zamanlı DXF analiz ve yapay zeka destekli tasarım asistanı.',
}

export default function RootLayout({ children }: { children: ReactNode }) {
    return (
        <html lang="tr" className="dark">
            <body className="min-h-screen" style={{ background: '#0D1117' }}>
                {children}
            </body>
        </html>
    )
}
