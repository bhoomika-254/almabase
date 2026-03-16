/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#5B4B8A',
        'primary-hover': '#6B5BA3',
        'primary-light': '#F5F0FF',
        'text-primary': '#1A1A1A',
        'text-secondary': '#666666',
        'text-tertiary': '#999999',
        border: '#E0E0E0',
        'border-dashed': '#CCCCCC',
        success: '#27AE60',
        error: '#E74C3C',
        warning: '#F39C12',
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'sans-serif'],
      },
      borderRadius: {
        pill: '24px',
      },
      boxShadow: {
        card: '0 2px 8px rgba(0, 0, 0, 0.06)',
        'btn-primary': '0 4px 12px rgba(91, 75, 138, 0.25)',
        'btn-primary-hover': '0 6px 16px rgba(91, 75, 138, 0.35)',
      },
    },
  },
  plugins: [],
}
