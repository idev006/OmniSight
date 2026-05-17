/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts}'],
  theme: {
    extend: {},
  },
  plugins: [require('daisyui')],
  daisyui: {
    themes: [
      'light', 'dark', 'cupcake', 'bumblebee', 'emerald', 'corporate',
      'synthwave', 'retro', 'cyberpunk', 'valentine', 'halloween', 'garden',
      'forest', 'aqua', 'lofi', 'pastel', 'fantasy', 'wireframe', 'black',
      'luxury', 'dracula', 'cmyk', 'autumn', 'business', 'acid', 'lemon',
      'night', 'coffee', 'winter', 'dim', 'nord', 'sunset',
    ],
    darkTheme: 'dark',
    logs: false,
  },
}
