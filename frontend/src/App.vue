<template>
  <RouterView />
  <AppToast />
  <ConfirmModal />
</template>

<script setup>
import { onMounted } from 'vue'
import AppToast from '@/components/AppToast.vue'
import ConfirmModal from '@/components/ConfirmModal.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

// On every app load: verify session with backend
// Catches deactivated accounts even if JWT is still valid
onMounted(async () => {
  if (auth.token) {
    await auth.verifySession()
    // If session invalid, verifySession() clears state
    // Router guard will redirect to /login on next navigation
  }
})
</script>
