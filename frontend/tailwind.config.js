/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        'dark-bg': '#09090B',
        'dark-card': '#141417',
        'dark-sidebar-active': '#1C1C20',
        'dark-border': 'rgba(255,255,255,.09)',
        'dark-border-soft': 'rgba(255,255,255,.055)',
        'dark-border-strong': 'rgba(255,255,255,.16)',
        'dark-text': '#F5F5F7',
        'dark-muted': '#9A9AA2',
        'dark-faint': '#6E6E78',
        'dark-accent': '#0A84FF',
        'dark-accent-bg': 'rgba(10,132,255,.14)',
        'light-bg': '#FAFAFA',
        'light-card': '#FFFFFF',
        'light-text': '#1D1D1F',
        'light-muted': '#6E6E73',
      },
    },
  },
  plugins: [],
}
