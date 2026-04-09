/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        brand: {
          bg:      '#0A0F1E',
          surface: '#111827',
          border:  'rgba(255,255,255,0.08)',
        },
      },
      animation: {
        'spin-slow':  'spin 3s linear infinite',
        'float':      'float 6s ease-in-out infinite',
        'fade-in':    'fadeIn 0.4s ease-out',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%':      { transform: 'translateY(-16px)' },
        },
        fadeIn: {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
      },
      backgroundImage: {
        'gradient-cta':  'linear-gradient(135deg, #6366F1, #8B5CF6)',
        'gradient-hero': 'radial-gradient(ellipse at top, #1e1b4b 0%, #0A0F1E 70%)',
      },
    },
  },
  plugins: [],
}
