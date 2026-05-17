import { defineStore } from 'pinia'
import { ref } from 'vue'

export const THEMES = [
  { name: 'dark',      label: 'Dark',       icon: '🌑' },
  { name: 'light',     label: 'Light',      icon: '☀️' },
  { name: 'night',     label: 'Night',      icon: '🌃' },
  { name: 'dim',       label: 'Dim',        icon: '🌒' },
  { name: 'nord',      label: 'Nord',       icon: '❄️' },
  { name: 'synthwave', label: 'Synthwave',  icon: '🌆' },
  { name: 'cyberpunk', label: 'Cyberpunk',  icon: '🤖' },
  { name: 'dracula',   label: 'Dracula',    icon: '🧛' },
  { name: 'luxury',    label: 'Luxury',     icon: '💎' },
  { name: 'black',     label: 'Black',      icon: '⬛' },
  { name: 'coffee',    label: 'Coffee',     icon: '☕' },
  { name: 'business',  label: 'Business',   icon: '💼' },
  { name: 'corporate', label: 'Corporate',  icon: '🏢' },
  { name: 'forest',    label: 'Forest',     icon: '🌲' },
  { name: 'emerald',   label: 'Emerald',    icon: '💚' },
  { name: 'garden',    label: 'Garden',     icon: '🌸' },
  { name: 'aqua',      label: 'Aqua',       icon: '🌊' },
  { name: 'sunset',    label: 'Sunset',     icon: '🌅' },
  { name: 'autumn',    label: 'Autumn',     icon: '🍂' },
  { name: 'halloween', label: 'Halloween',  icon: '🎃' },
  { name: 'retro',     label: 'Retro',      icon: '📺' },
  { name: 'valentine', label: 'Valentine',  icon: '💕' },
  { name: 'cupcake',   label: 'Cupcake',    icon: '🧁' },
  { name: 'bumblebee', label: 'Bumblebee',  icon: '🐝' },
  { name: 'pastel',    label: 'Pastel',     icon: '🎨' },
  { name: 'fantasy',   label: 'Fantasy',    icon: '🧝' },
  { name: 'lofi',      label: 'Lo-Fi',      icon: '🎵' },
  { name: 'wireframe', label: 'Wireframe',  icon: '📐' },
  { name: 'cmyk',      label: 'CMYK',       icon: '🖨️' },
  { name: 'acid',      label: 'Acid',       icon: '🧪' },
  { name: 'lemon',     label: 'Lemon',      icon: '🍋' },
  { name: 'winter',    label: 'Winter',     icon: '⛄' },
]

const STORAGE_KEY = 'omnisight-theme'

export const useThemeStore = defineStore('theme', () => {
  const current = ref(localStorage.getItem(STORAGE_KEY) || 'dark')

  function setTheme(name) {
    current.value = name
    document.documentElement.setAttribute('data-theme', name)
    localStorage.setItem(STORAGE_KEY, name)
  }

  // Apply on init (in case store is loaded after the inline script)
  setTheme(current.value)

  return { current, setTheme, themes: THEMES }
})
