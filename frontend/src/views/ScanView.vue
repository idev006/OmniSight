<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-start justify-between gap-3">
      <div>
        <h1 class="text-xl font-bold tracking-wide">Live Scan</h1>
        <p class="text-sm text-base-content/40 mt-0.5">Webcam face recognition</p>
      </div>
      <div class="flex items-center gap-2">
        <!-- WS status -->
        <div class="flex items-center gap-1.5 text-xs opacity-50">
          <span class="w-1.5 h-1.5 rounded-full"
            :class="wsState === 'open' ? 'bg-success animate-pulse' : 'bg-base-300'"></span>
          {{ wsState === 'open' ? 'Live' : wsState === 'connecting' ? 'Connecting…' : 'Offline' }}
        </div>
        <select v-model="selectedStation" class="select select-bordered select-sm w-56">
          <option value="">Select Station…</option>
          <option v-for="s in stations" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
      </div>
    </div>

    <!-- Video feed -->
    <div class="relative bg-black rounded-xl overflow-hidden" style="aspect-ratio: 16/9;">
      <video ref="videoEl" class="w-full h-full object-contain" autoplay playsinline muted />
      <canvas ref="canvasEl" class="absolute inset-0 w-full h-full pointer-events-none" />

      <!-- No station selected -->
      <div v-if="!selectedStation"
        class="absolute inset-0 flex flex-col items-center justify-center text-base-content/30 gap-3">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-14 w-14" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1"
            d="M3 7a1 1 0 011-1h3l2-2h6l2 2h3a1 1 0 011 1v11a1 1 0 01-1 1H4a1 1 0 01-1-1V7z"/>
          <circle cx="12" cy="13" r="3" stroke="currentColor" stroke-width="1" fill="none"/>
        </svg>
        <span>Select a station to start scanning</span>
      </div>

      <!-- FPS overlay -->
      <div v-if="streaming"
        class="absolute top-2 left-2 px-2 py-0.5 rounded-full bg-black/50 text-white text-xs font-mono">
        {{ localFps.toFixed(1) }} fps
      </div>

      <!-- Paused overlay -->
      <Transition name="fade">
        <div v-if="pausedByServer"
          class="absolute inset-0 flex flex-col items-center justify-center bg-black/70">
          <div class="text-white text-3xl mb-2">⏸</div>
          <div class="text-white font-semibold">Paused by Pilot Console</div>
        </div>
      </Transition>
    </div>

    <!-- Identity cards -->
    <div v-if="activeFaces.length > 0" class="grid grid-cols-2 md:grid-cols-4 gap-3">
      <div
        v-for="face in activeFaces" :key="face.tracking_id"
        class="card shadow-sm border"
        :class="face.status === 'match' ? 'bg-success/5 border-success/25'
                                        : 'bg-error/5 border-error/25'"
      >
        <div class="card-body p-3 gap-1">
          <div class="flex items-center gap-2">
            <div class="w-2 h-2 rounded-full shrink-0"
              :class="face.status === 'match' ? 'bg-success' : 'bg-error'"></div>
            <span class="font-semibold text-sm truncate">{{ face.full_name || 'Unknown' }}</span>
          </div>
          <div v-if="face.emp_code" class="text-xs text-base-content/40 font-mono">{{ face.emp_code }}</div>
          <div v-if="face.dept_name" class="text-xs text-base-content/40">{{ face.dept_name }}</div>
          <div class="flex items-center justify-between mt-1">
            <span v-if="face.confidence" class="text-xs text-base-content/40 font-mono">
              {{ (face.confidence * 100).toFixed(1) }}%
            </span>
            <span v-if="face.attendance_logged" class="text-xs text-success font-semibold">✓ logged</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { TOKEN_KEY } from '@/stores/auth'    // ← use shared TOKEN_KEY, never hardcode
import api from '@/api/client'

const stations       = ref([])
const selectedStation = ref('')
const activeFaces    = ref([])
const videoEl        = ref(null)
const canvasEl       = ref(null)

const wsState        = ref('disconnected')
const streaming      = ref(false)
const pausedByServer = ref(false)
const localFps       = ref(0)

let ws            = null
let mediaStream   = null
let _frameTimer   = null
let _fpsTimer     = null
let _fpsCounter   = 0
let _destroyed    = false

// ── Station loading ───────────────────────────────────────────────────────────
onMounted(async () => {
  const { data } = await api.get('/api/v1/stations')
  stations.value = data
})

onUnmounted(() => {
  _destroyed = true
  _stop()
})

// ── React to station selection ────────────────────────────────────────────────
watch(selectedStation, (id) => {
  _stop()
  if (id) _start(id)
})

// ── Start scanning ────────────────────────────────────────────────────────────
async function _start(stationId) {
  try {
    // Open webcam
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 15 } },
      audio: false,
    })
    videoEl.value.srcObject = mediaStream
    streaming.value = true
    pausedByServer.value = false

    // Connect WebSocket — use TOKEN_KEY (not hardcoded 'token')
    const token = localStorage.getItem(TOKEN_KEY)
    wsState.value = 'connecting'
    ws = new WebSocket(
      `ws://localhost:8000/api/v1/ws/scan/${stationId}?token=${token}`
    )

    ws.onopen = () => { wsState.value = 'open' }

    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data)

        // Control messages (pause/resume/disconnect from Pilot Console)
        if (data.action === 'pause') {
          pausedByServer.value = true
          _stopFrameLoop()
          return
        }
        if (data.action === 'resume') {
          pausedByServer.value = false
          _startFrameLoop()
          return
        }
        if (data.action === 'disconnect') {
          _stop()
          return
        }

        // Recognition results
        activeFaces.value = data.faces || []
        _drawBBoxes(data.faces || [])
      } catch { /* ignore */ }
    }

    ws.onclose = (e) => {
      wsState.value = 'closed'
      if (_destroyed || !selectedStation.value) return
      if (e.code === 4001 || e.code === 4003) { wsState.value = 'disconnected'; return }
      setTimeout(() => { if (!_destroyed && selectedStation.value) _start(stationId) }, 2000)
    }

    ws.onerror = () => ws?.close()

    // Start frame loop at 2 FPS
    // Backend also has its own FPS gate, so this is a best-effort client-side limit
    _startFrameLoop()

    // FPS counter
    _fpsTimer = setInterval(() => {
      localFps.value = _fpsCounter
      _fpsCounter    = 0
    }, 1000)

  } catch (e) {
    console.error('Camera/WS error:', e)
    wsState.value = 'disconnected'
  }
}

// ── Stop scanning ─────────────────────────────────────────────────────────────
function _stop() {
  streaming.value      = false
  pausedByServer.value = false
  activeFaces.value    = []

  _stopFrameLoop()
  if (_fpsTimer) { clearInterval(_fpsTimer); _fpsTimer = null }
  if (ws)          { ws.close(); ws = null }
  if (mediaStream) { mediaStream.getTracks().forEach(t => t.stop()); mediaStream = null }
  if (videoEl.value) videoEl.value.srcObject = null
  if (canvasEl.value) {
    const ctx = canvasEl.value.getContext('2d')
    ctx?.clearRect(0, 0, canvasEl.value.width, canvasEl.value.height)
  }
  wsState.value  = 'disconnected'
  localFps.value = 0
}

// ── Frame capture loop ────────────────────────────────────────────────────────
function _startFrameLoop(fps = 2) {
  _stopFrameLoop()
  _frameTimer = setInterval(_sendFrame, Math.round(1000 / fps))
}

function _stopFrameLoop() {
  if (_frameTimer) { clearInterval(_frameTimer); _frameTimer = null }
}

function _sendFrame() {
  if (!ws || ws.readyState !== WebSocket.OPEN) return
  const video = videoEl.value
  if (!video || !video.videoWidth) return

  const offscreen = document.createElement('canvas')
  offscreen.width  = 640
  offscreen.height = 480
  offscreen.getContext('2d').drawImage(video, 0, 0, 640, 480)
  offscreen.toBlob((blob) => {
    if (!blob || !ws || ws.readyState !== WebSocket.OPEN) return
    blob.arrayBuffer().then((buf) => { ws.send(buf); _fpsCounter++ })
  }, 'image/jpeg', 0.70)
}

// ── Bounding box overlay ──────────────────────────────────────────────────────
function _drawBBoxes(faces) {
  const canvas = canvasEl.value
  const video  = videoEl.value
  if (!canvas || !video) return

  canvas.width  = video.clientWidth
  canvas.height = video.clientHeight

  const scaleX = canvas.width  / (video.videoWidth  || canvas.width)
  const scaleY = canvas.height / (video.videoHeight || canvas.height)

  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  for (const face of faces) {
    const { x, y, w, h } = face.bbox
    ctx.strokeStyle = face.status === 'match' ? '#22c55e' : '#ef4444'
    ctx.lineWidth   = 2
    ctx.strokeRect(x * scaleX, y * scaleY, w * scaleX, h * scaleY)

    // Label
    if (face.full_name || face.status === 'unknown') {
      const label = face.status === 'match'
        ? `${face.full_name} ${(face.confidence * 100).toFixed(0)}%`
        : 'Unknown'
      ctx.fillStyle   = face.status === 'match' ? '#22c55e' : '#ef4444'
      ctx.font        = 'bold 13px sans-serif'
      ctx.fillText(label, x * scaleX + 2, y * scaleY - 5)
    }
  }
}
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
