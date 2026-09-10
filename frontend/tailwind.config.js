/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        dark: {
          bg: '#080a0f',
          surface: '#0e121a',
          surfaceRaised: '#121722',
          surfaceSunken: '#090d14',
          border: 'rgba(255, 255, 255, 0.06)',
          borderHover: 'rgba(147, 197, 253, 0.25)',
        },
        brand: {
          blue: '#7dd3fc',
          cyan: '#38bdf8',
          glow: 'rgba(56, 189, 248, 0.15)',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        'neu-flat': '5px 5px 12px rgba(0, 0, 0, 0.6), -3px -3px 8px rgba(255, 255, 255, 0.03)',
        'neu-raised': '8px 8px 18px rgba(0, 0, 0, 0.7), -4px -4px 12px rgba(255, 255, 255, 0.04)',
        'neu-sunken': 'inset 4px 4px 8px rgba(0, 0, 0, 0.75), inset -2px -2px 6px rgba(255, 255, 255, 0.04)',
        'neu-sunken-sm': 'inset 2px 2px 5px rgba(0, 0, 0, 0.7), inset -1px -1px 3px rgba(255, 255, 255, 0.03)',
        'neu-button': '4px 4px 10px rgba(0, 0, 0, 0.6), -2px -2px 6px rgba(255, 255, 255, 0.04)',
        'neu-glow': '0 0 25px rgba(125, 211, 252, 0.22), 4px 4px 12px rgba(0, 0, 0, 0.6)',
      }
    },
  },
  plugins: [],
}
