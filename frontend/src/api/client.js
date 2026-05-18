/**
 * Axios client — central HTTP instance for all API calls.
 *
 * Request interceptor: reads token from localStorage using TOKEN_KEY (same key as auth store).
 * Response interceptor: on 401, calls auth.forceLogout() to clear ALL state consistently.
 *
 * Note: We read from localStorage (not the Pinia store directly) to avoid a circular
 * dependency: auth.js imports api, so api cannot import auth.js at module load time.
 * The TOKEN_KEY constant ensures both files use the same storage key (SSOT for the key).
 */
import axios from 'axios'
import { TOKEN_KEY } from '@/stores/auth'

const api = axios.create({
  // ใช้ relative URL — Vite proxy (/api → localhost:8000) จัดการเอง
  // ทำงานได้ทั้งจาก localhost และจาก IP address บนมือถือ
  baseURL: import.meta.env.VITE_API_URL || '/',
  timeout: 10000,
})

// ── Request: attach token ──────────────────────────────────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ── Response: handle 401 consistently ─────────────────────────────────────
// Guard flag prevents multiple concurrent 401s from firing multiple redirects
let _isRedirecting = false

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && !_isRedirecting) {
      _isRedirecting = true

      // Determine reason for better UX on login page
      const detail = err.response?.data?.detail || ''
      const reason = detail.toLowerCase().includes('deactivat') ? 'deactivated'
                   : detail.toLowerCase().includes('expired')   ? 'expired'
                   : localStorage.getItem(TOKEN_KEY)            ? 'expired'
                   : ''

      // Clear state — import lazily to avoid circular dependency at module init
      localStorage.removeItem(TOKEN_KEY)
      window.location.replace(reason ? `/login?reason=${reason}` : '/login')
    }
    return Promise.reject(err)
  },
)

export default api
