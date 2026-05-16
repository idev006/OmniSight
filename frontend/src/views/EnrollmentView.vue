<template>
  <div class="flex flex-col gap-6 max-w-2xl">
    <div class="flex items-center gap-3">
      <RouterLink to="/employees" class="btn btn-ghost btn-sm">← Back</RouterLink>
      <h1 class="text-2xl font-bold">Face Enrollment</h1>
    </div>

    <div v-if="employee" class="alert alert-info">
      <span>Enrolling: <strong>{{ employee.full_name }}</strong> ({{ employee.emp_code }})</span>
    </div>

    <!-- 6 sample slots -->
    <div class="grid grid-cols-3 gap-4">
      <div
        v-for="slot in 6"
        :key="slot"
        class="relative aspect-square rounded-lg border-2 flex items-center justify-center cursor-pointer"
        :class="slots[slot - 1] ? 'border-success' : 'border-base-300 border-dashed hover:border-primary'"
        @click="captureSlot(slot - 1)"
      >
        <img
          v-if="slots[slot - 1]"
          :src="slots[slot - 1].preview"
          class="w-full h-full object-cover rounded-lg"
        />
        <div v-else class="flex flex-col items-center text-base-content/40">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span class="text-xs mt-1">Sample {{ slot }}</span>
        </div>

        <button
          v-if="slots[slot - 1]"
          class="absolute top-1 right-1 btn btn-circle btn-xs btn-error opacity-70"
          @click.stop="slots[slot - 1] = null"
        >✕</button>
      </div>
    </div>

    <!-- Camera preview (hidden capture) -->
    <video ref="videoEl" class="hidden" autoplay playsinline muted />
    <canvas ref="captureCanvas" class="hidden" width="640" height="480" />

    <div class="flex gap-3">
      <button class="btn btn-primary flex-1" :disabled="enrolledCount < 6 || submitting" @click="submitEnrollment">
        {{ submitting ? 'Saving...' : `Submit (${enrolledCount}/6)` }}
      </button>
    </div>

    <div v-if="message" class="alert" :class="messageType === 'success' ? 'alert-success' : 'alert-error'">
      {{ message }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api/client'

const route = useRoute()
const employee = ref(null)
const slots = ref(Array(6).fill(null))
const videoEl = ref(null)
const captureCanvas = ref(null)
const submitting = ref(false)
const message = ref('')
const messageType = ref('success')

let stream = null
let activeSlot = -1

const enrolledCount = computed(() => slots.value.filter(Boolean).length)

async function captureSlot(index) {
  activeSlot = index
  if (!stream) {
    stream = await navigator.mediaDevices.getUserMedia({ video: true })
    videoEl.value.srcObject = stream
    await new Promise((r) => (videoEl.value.onloadedmetadata = r))
  }
  const canvas = captureCanvas.value
  const ctx = canvas.getContext('2d')
  ctx.drawImage(videoEl.value, 0, 0, 640, 480)
  canvas.toBlob((blob) => {
    const preview = URL.createObjectURL(blob)
    slots.value[activeSlot] = { blob, preview }
  }, 'image/jpeg', 0.9)
}

async function submitEnrollment() {
  submitting.value = true
  message.value = ''
  try {
    for (let i = 0; i < 6; i++) {
      if (!slots.value[i]) continue
      const fd = new FormData()
      fd.append('sample_index', i)
      fd.append('file', slots.value[i].blob, `sample_${i}.jpg`)
      await api.post(`/api/v1/employees/${route.params.id}/enroll`, fd)
    }
    messageType.value = 'success'
    message.value = 'Enrollment complete! Employee is now active.'
  } catch (e) {
    messageType.value = 'error'
    message.value = e.response?.data?.detail || 'Upload failed'
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  const { data } = await api.get(`/api/v1/employees/${route.params.id}`)
  employee.value = data
})

onUnmounted(() => {
  if (stream) stream.getTracks().forEach((t) => t.stop())
})
</script>
