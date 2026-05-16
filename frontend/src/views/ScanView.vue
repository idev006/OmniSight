<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold">Live Scan</h1>
      <select v-model="selectedStation" class="select select-bordered select-sm w-64">
        <option value="">Select Station</option>
        <option v-for="s in stations" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>
    </div>

    <div class="relative bg-black rounded-lg overflow-hidden" style="aspect-ratio: 16/9;">
      <video ref="videoEl" class="w-full h-full object-contain" autoplay playsinline muted />
      <canvas ref="canvasEl" class="absolute inset-0 w-full h-full" />

      <div v-if="!selectedStation" class="absolute inset-0 flex items-center justify-center text-base-content/50">
        <span class="text-lg">Select a station to start scanning</span>
      </div>
    </div>

    <!-- Identity cards from scan results -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
      <div
        v-for="face in activeFaces"
        :key="face.tracking_id"
        class="card bg-base-200 shadow"
        :class="face.status === 'match' ? 'border border-success' : face.status === 'unknown' ? 'border border-error' : ''"
      >
        <div class="card-body p-3">
          <div class="flex items-center gap-2">
            <div
              class="w-3 h-3 rounded-full flex-shrink-0"
              :class="face.status === 'match' ? 'bg-success' : face.status === 'unknown' ? 'bg-error' : 'bg-warning'"
            />
            <span class="font-semibold text-sm truncate">
              {{ face.full_name || 'Unknown' }}
            </span>
          </div>
          <div v-if="face.emp_code" class="text-xs text-base-content/60">{{ face.emp_code }}</div>
          <div v-if="face.dept_name" class="text-xs text-base-content/60">{{ face.dept_name }}</div>
          <div v-if="face.confidence" class="text-xs text-base-content/50">
            {{ (face.confidence * 100).toFixed(1) }}%
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onUnmounted } from 'vue'
import api from '@/api/client'

const stations = ref([])
const selectedStation = ref('')
const activeFaces = ref([])
const videoEl = ref(null)
const canvasEl = ref(null)

let ws = null
let stream = null
let frameInterval = null

async function loadStations() {
  const { data } = await api.get('/api/v1/stations')
  stations.value = data
}

function connectWS(stationId) {
  const token = localStorage.getItem('token')
  ws = new WebSocket(`ws://localhost:8000/api/v1/ws/scan/${stationId}?token=${token}`)
  ws.binaryType = 'arraybuffer'

  ws.onmessage = (event) => {
    const result = JSON.parse(event.data)
    activeFaces.value = result.faces
    drawBBoxes(result.faces)
  }

  ws.onclose = () => {
    if (selectedStation.value) {
      setTimeout(() => connectWS(stationId), 2000)
    }
  }
}

function drawBBoxes(faces) {
  const canvas = canvasEl.value
  const video = videoEl.value
  if (!canvas || !video) return
  canvas.width = video.videoWidth || video.clientWidth
  canvas.height = video.videoHeight || video.clientHeight
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  for (const face of faces) {
    const { x, y, w, h } = face.bbox
    ctx.strokeStyle = face.status === 'match' ? '#00ff88' : face.status === 'unknown' ? '#ff4444' : '#ffaa00'
    ctx.lineWidth = 2
    ctx.strokeRect(x, y, w, h)
  }
}

async function startCamera() {
  stream = await navigator.mediaDevices.getUserMedia({ video: true })
  videoEl.value.srcObject = stream

  frameInterval = setInterval(() => {
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    const canvas = document.createElement('canvas')
    canvas.width = 640
    canvas.height = 480
    const ctx = canvas.getContext('2d')
    ctx.drawImage(videoEl.value, 0, 0, 640, 480)
    canvas.toBlob((blob) => {
      blob.arrayBuffer().then((buf) => ws.send(buf))
    }, 'image/jpeg', 0.7)
  }, 200)
}

function stopAll() {
  clearInterval(frameInterval)
  if (ws) { ws.close(); ws = null }
  if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null }
  activeFaces.value = []
}

watch(selectedStation, (id) => {
  stopAll()
  if (id) {
    connectWS(id)
    startCamera()
  }
})

onUnmounted(stopAll)
loadStations()
</script>
