/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0B0E13',
        panel: { DEFAULT: '#12161D', '2': '#171D26' },
        line: { DEFAULT: '#262E39', '2': '#39434F' },
        ink: { DEFAULT: '#E8EDF4', dim: '#8C96A3' },
        accent: '#F0A83E',
        imminent: '#FF5C5C',
        near: '#F0A83E',
        watch: '#4FA3C7',
        unknown: '#6B7682',
        ok: '#43C989',
      },
      fontFamily: {
        sans: ['IBM Plex Sans', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['IBM Plex Mono', 'ui-monospace', 'SF Mono', 'Menlo', 'monospace'],
      },
      fontSize: {
        micro: ['10px', { lineHeight: '1.4' }],
        xs: ['11px', { lineHeight: '1.45' }],
        sm: ['12px', { lineHeight: '1.45' }],
        base: ['13px', { lineHeight: '1.45' }],
        md: ['14px', { lineHeight: '1.45' }],
        lg: ['16px', { lineHeight: '1.4' }],
        xl: ['18px', { lineHeight: '1.35' }],
        '2xl': ['20px', { lineHeight: '1.3' }],
      },
      spacing: {
        '0.5': '2px', '1': '4px', '1.5': '6px', '2': '8px', '2.5': '10px',
        '3': '12px', '3.5': '14px', '4': '16px', '5': '20px', '6': '24px', '8': '32px',
      },
      borderRadius: {
        sm: '4px', DEFAULT: '6px', md: '8px', lg: '12px',
      },
      transitionDuration: {
        fast: '150ms', DEFAULT: '200ms', slow: '300ms',
      },
    },
  },
  plugins: [require('@tailwindcss/forms')],
}
