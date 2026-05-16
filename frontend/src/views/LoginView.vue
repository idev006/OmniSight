<template>
  <div class="min-h-screen flex items-center justify-center bg-base-300">
    <div class="card w-96 bg-base-100 shadow-xl">
      <div class="card-body">
        <h2 class="card-title text-2xl justify-center mb-4">OmniSight</h2>
        <form @submit.prevent="handleLogin">
          <div class="form-control mb-3">
            <label class="label"><span class="label-text">Username</span></label>
            <input v-model="form.username" type="text" class="input input-bordered" required />
          </div>
          <div class="form-control mb-6">
            <label class="label"><span class="label-text">Password</span></label>
            <input v-model="form.password" type="password" class="input input-bordered" required />
          </div>
          <div v-if="error" class="alert alert-error mb-4 text-sm">{{ error }}</div>
          <button type="submit" class="btn btn-primary w-full" :class="{ loading: loading }">
            Login
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const form = ref({ username: '', password: '' })
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(form.value.username, form.value.password)
    router.push('/scan')
  } catch {
    error.value = 'Invalid username or password'
  } finally {
    loading.value = false
  }
}
</script>
