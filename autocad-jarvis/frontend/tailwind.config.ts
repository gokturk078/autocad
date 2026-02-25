import type { Config } from 'tailwindcss'

const config: Config = {
    content: [
        './app/**/*.{js,ts,jsx,tsx,mdx}',
        './components/**/*.{js,ts,jsx,tsx,mdx}',
    ],
    darkMode: 'class',
    theme: {
        extend: {
            colors: {
                jarvis: {
                    bg: '#0D1117',
                    surface: '#161B22',
                    gold: '#D4AF37',
                    cyan: '#00BCD4',
                    green: '#39D353',
                    red: '#E53E3E',
                },
            },
            animation: {
                'slide-up': 'slide-up 0.3s ease forwards',
                'pulse-gold': 'pulse-gold 2s ease-in-out infinite',
                'shimmer': 'shimmer 1.5s ease-in-out infinite',
            },
            keyframes: {
                'slide-up': {
                    '0%': { opacity: '0', transform: 'translateY(8px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
                'pulse-gold': {
                    '0%, 100%': { opacity: '1', boxShadow: '0 0 8px rgba(212, 175, 55, 0.2)' },
                    '50%': { opacity: '0.6', boxShadow: '0 0 20px rgba(212, 175, 55, 0.2)' },
                },
                'shimmer': {
                    '0%': { backgroundPosition: '-200% 0' },
                    '100%': { backgroundPosition: '200% 0' },
                },
            },
        },
    },
    plugins: [],
}

export default config
