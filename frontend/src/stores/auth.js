/**
 * Auth Store — SSOT for authentication state
 *
 * Design decisions:
 * - Token stored in localStorage under TOKEN_KEY (same key used everywhere)
 * - `user` computed: derived from token BUT checks expiry → null if expired
 * - `isLoggedIn` based on `user` (not raw token) → covers expiry automatically
 * - `forceLogout()` called by API interceptor on 401 (no confirm dialog)
 * - `logout()` called by user action (confirm dialog handled in AppLayout)
 * - On app load, `verifySession()` calls /me to ensure user still active in DB
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api/client'

export const TOKEN_KEY = 'omnisight-token'

// Legacy keys from previous versions — removed on first load
const LEGACY_KEYS = ['token']

// ── JWT helpers ────────────────────────────────────────────────────────────

function parseJwt(token) {
  try {
    const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    return JSON.parse(atob(base64))
  } catch {
    return null
  }
}

/** Returns true if token is expired or malformed (10-second clock-skew buffer) */
function isTokenExpired(token) {
  const p = parseJwt(token)
  if (!p?.exp) return true
  return (Date.now() / 1000) >= (p.exp - 10)
}

// ── Store ──────────────────────────────────────────────────────────────────

export const useAuthStore = defineStore('auth', () => {

  // Clean up any legacy storage keys from older versions
  LEGACY_KEYS.forEach(k => localStorage.removeItem(k))

  // ── Raw token (persisted in localStorage) ───────────────────────────────
  const token = ref(localStorage.getItem(TOKEN_KEY) || '')

  // ── SSOT: all user state derived from token ──────────────────────────────
  // Returns null when: no token | token expired | token malformed | role missing
  const user = computed(() => {
    if (!token.value) return null
    if (isTokenExpired(token.value)) return null
    const p = parseJwt(token.value)
    // Require both sub and role to be present — no fallback defaults
    if (!p?.sub || !p?.role) return null
    return {
      username:    p.sub,
      role:        p.role,            // 'ADMIN' | 'HR' | 'OPERATOR'
      user_id:     p.user_id  || '',
      station_ids: p.station_ids || [],
      exp:         p.exp,
      full_name:   _fullName.value,   // enriched from /me after login
    }
  })

  // full_name is not in JWT; populated by verifySession() calling /me
  const _fullName = ref('')

  const isLoggedIn = computed(() => !!user.value)
  const isAdmin    = computed(() => user.value?.role === 'ADMIN')
  const isHR       = computed(() => ['ADMIN', 'HR'].includes(user.value?.role ?? ''))

  /** Seconds until token expires (0 = expired/no token) */
  const expiresIn = computed(() => {
    if (!token.value) return 0
    const p = parseJwt(token.value)
    return p?.exp ? Math.max(0, Math.floor(p.exp - Date.now() / 1000)) : 0
  })

  // ── Actions ───────────────────────────────────────────────────────────────

  async function login(username, password) {
    const { data } = await api.post('/api/v1/auth/login', { username, password })
    const t = data.access_token
    // Validate before storing — never store a token we can't trust
    if (!t || isTokenExpired(t)) throw new Error('Server returned invalid or expired token')
    token.value = t
    localStorage.setItem(TOKEN_KEY, t)
    // Fetch live user info (full_name, confirm user is active)
    await verifySession()
  }

  /**
   * Verify session with the backend (/me).
   * Called on app load and after login.
   * Clears state if user has been deactivated or token is invalid.
   * @returns {boolean} true if session is valid
   */
  async function verifySession() {
    if (!token.value || isTokenExpired(token.value)) {
      _clearState()
      return false
    }
    try {
      const { data } = await api.get('/api/v1/auth/me')
      _fullName.value = data.full_name || ''
      return true
    } catch {
      // 401 = user deactivated or token invalid — clear everything
      _clearState()
      return false
    }
  }

  /** Normal logout — called by user action (AppLayout confirm dialog) */
  function logout() {
    _clearState()
    window.location.replace('/login')
  }

  /**
   * Force logout — called by API interceptor on 401 (no confirm dialog).
   * @param {string} reason  'expired' | 'deactivated' | ''
   */
  function forceLogout(reason = '') {
    _clearState()
    const url = reason ? `/login?reason=${reason}` : '/login'
    window.location.replace(url)
  }

  /** Internal: clears all auth state */
  function _clearState() {
    token.value   = ''
    _fullName.value = ''
    localStorage.removeItem(TOKEN_KEY)
  }

  return {
    token,
    user,
    isLoggedIn,
    isAdmin,
    isHR,
    expiresIn,
    login,
    logout,
    forceLogout,
    verifySession,
  }
})
