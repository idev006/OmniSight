import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api/client'

function parseJwt(token) {
  try {
    const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    return JSON.parse(atob(base64))
  } catch {
    return {}
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')

  const isLoggedIn = computed(() => !!token.value)

  const user = computed(() => {
    if (!token.value) return null
    const p = parseJwt(token.value)
    return {
      username: p.sub,
      role: p.role || 'OPERATOR',
      user_id: p.user_id,
      station_ids: p.station_ids || [],
    }
  })

  const isAdmin = computed(() => user.value?.role === 'ADMIN')
  const isHR    = computed(() => ['ADMIN', 'HR'].includes(user.value?.role))

  async function login(username, password) {
    const { data } = await api.post('/api/v1/auth/login', { username, password })
    token.value = data.access_token
    localStorage.setItem('token', data.access_token)
  }

  function logout() {
    token.value = ''
    localStorage.removeItem('token')
    window.location.href = '/login'
  }

  return { token, isLoggedIn, user, isAdmin, isHR, login, logout }
})
