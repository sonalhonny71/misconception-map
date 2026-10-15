/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: '#17133f',
        indigo: '#5546b8',
        lavender: '#f1edff',
        paper: '#fbfaff',
        ink: '#24243a',
        muted: '#696980',
        line: '#e6e3f0',
        teal: '#17866a',
        mint: '#e1f6ee',
        amber: '#9b5b08',
        sand: '#fff2dc',
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
      },
      borderRadius: {
        'card': '18px',
        'btn': '12px',
        'pill': '999px',
      },
      boxShadow: {
        'card': '0 8px 28px rgba(34, 24, 83, 0.07)',
      },
    },
  },
  plugins: [],
}