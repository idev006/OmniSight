<template>
  <div class="min-h-screen flex items-center justify-center bg-base-200 px-4">

    <!-- Theme picker (top-right) -->
    <div class="fixed top-4 right-4 z-50">
      <div class="dropdown dropdown-end">
        <div tabindex="0" role="button" class="btn btn-ghost btn-sm border border-base-300 bg-base-100">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
          </svg>
          Theme
        </div>
        <ul tabindex="0" class="dropdown-content menu p-1 shadow-2xl bg-base-100 rounded-box w-52 max-h-80 overflow-y-auto border border-base-300 z-50 flex-nowrap">
          <li v-for="t in themes" :key="t.name">
            <button
              class="text-sm flex items-center gap-2"
              :class="{ 'active font-semibold': themeStore.current === t.name }"
              @click="themeStore.setTheme(t.name)"
            >
              <span>{{ t.icon }}</span>
              <span>{{ t.label }}</span>
              <span v-if="themeStore.current === t.name" class="ml-auto">✓</span>
            </button>
          </li>
        </ul>
      </div>
    </div>

    <!-- Login card -->
    <div class="card w-full max-w-md bg-base-100 shadow-2xl border border-base-300">
      <div class="card-body p-8">

        <!-- Logo / brand -->
        <div class="text-center mb-8">
          <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary/10 border border-primary/20 mb-4">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
          </div>
          <h1 class="font-bold text-2xl tracking-[0.15em] text-primary">OMNISIGHT</h1>
          <p class="text-xs text-base-content/40 tracking-widest uppercase mt-1">Face Recognition System</p>
        </div>

        <!-- Form -->
        <form @submit.prevent="handleLogin" class="flex flex-col gap-4">

          <label class="form-control">
            <div class="label pb-1">
              <span class="label-text font-medium">Username</span>
            </div>
            <input
              v-model="form.username"
              type="text"
              placeholder="Enter username"
              class="input input-bordered w-full"
              autocomplete="username"
              autocapitalize="off"
              autocorrect="off"
              spellcheck="false"
              required
              autofocus
            />
          </label>

          <label class="form-control">
            <div class="label pb-1">
              <span class="label-text font-medium">Password</span>
            </div>
            <input
              v-model="form.password"
              type="password"
              placeholder="Enter password"
              class="input input-bordered w-full"
              autocomplete="current-password"
              autocapitalize="off"
              autocorrect="off"
              required
            />
          </label>

          <!-- Session expired / deactivated banner -->
          <div v-if="sessionMessage" role="alert" class="alert alert-warning py-2.5">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span class="text-sm">{{ sessionMessage }}</span>
          </div>

          <!-- Error alert -->
          <div v-if="error" role="alert" class="alert alert-error py-2.5">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span class="text-sm">{{ error }}</span>
          </div>

          <button
            type="submit"
            class="btn btn-primary w-full mt-2"
            :disabled="loading"
          >
            <span v-if="loading" class="loading loading-spinner loading-sm"></span>
            <span v-else>Sign In</span>
          </button>

        </form>

        <p class="text-center text-xs text-base-content/25 mt-6">v0.2.0 — Sprint 8</p>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore, THEMES } from '@/stores/theme'

const router     = useRouter()
const route      = useRoute()
const auth       = useAuthStore()
const themeStore = useThemeStore()
const themes     = THEMES

const form    = ref({ username: '', password: '' })
const error   = ref('')
const loading = ref(false)

// Session reason message (from ?reason= query param set by router/interceptor)
const sessionMessage = computed(() => {
  const r = route.query.reason
  if (r === 'expired')     return 'Your session has expired. Please sign in again.'
  if (r === 'deactivated') return 'Your account has been deactivated. Contact an administrator.'
  return ''
})

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(form.value.username, form.value.password)
    // Redirect to originally requested page (if any) or default to scan
    const redirect = route.query.redirect
    router.replace(typeof redirect === 'string' ? redirect : '/scan')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Invalid username or password'
  } finally {
    loading.value = false
  }
}
</script>
