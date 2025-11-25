/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#3B82F6',
          100: '#60A5FA',
          200: '#2563EB',
        },
        secondary: '#9333EA',
        bgDark: '#0B1120',
        glass: 'rgba(255, 255, 255, 0.05)',
      },
      fontFamily: {
        sans: ['Pretendard', 'Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        glass: '0 0 20px rgba(59,130,246,0.15)',
      },
    },
  },
  plugins: [],
}
