<template>
  <!--
    Mobile Scanner — Smartphone Camera Agent
    • Works as a WebSocket camera agent running in the mobile browser
    • Captures frames from the device camera → sends binary JPEG to backend
    • Receives recognition results → shows overlay
    • Respects pause/resume commands from Pilot Console
    • Design: portrait-first, full-screen video, touch-friendly controls
  -->
  <div class="fixed inset-0 bg-black flex flex-col overflow-hidden">

    <!-- Video + canvas overlay -->
    <div class="relative flex-1 min-h-0">
      <video ref="videoEl"
        class="w-full h-full object-cover"
        autoplay playsinline muted />
      <canvas ref="canvasEl"
        class="absolute inset-0 w-full h-full pointer-events-none" />

      <!-- Paused overlay -->
      <Transition name="fade">
        <div v-if="paused" class="absolute inset-0 flex flex-col items-center justify-center bg-black/70">
          <div class="text-white text-4xl mb-3">⏸</div>
          <div class="text-white text-lg font-semibold">Paused by Console</div>
          <div class="text-white/50 text-sm mt-1">Waiting for resume…</div>
        </div>
      </Transition>

      <!-- WS status badge -->
      <div class="absolute top-safe top-4 left-4 flex items-center gap-1.5
                  px-2.5 py-1 rounded-full text-xs font-semibold backdrop-blur-sm"
        :class="wsStatusClass">
        <span class="w-1.5 h-1.5 rounded-full"
          :class="wsState === 'open' ? 'bg-success animate-pulse' : 'bg-base-300'"></span>
        {{ wsStatusLabel }}
      </div>

      <!-- Station name badge -->
      <div v-if="selectedStation"
        class="absolute top-4 right-4 px-2.5 py-1 rounded-full text-xs font-medium
               bg-black/50 text-white backdrop-blur-sm">
        {{ selectedStation.name }}
      </div>

      <!-- Face recognition result cards (bottom overlay) -->
      <div class="absolute bottom-0 left-0 right-0 p-3 flex flex-col gap-2 pointer-events-none"
        style="background: linear-gradient(transparent, rgba(0,0,0,0.7))">
        <TransitionGroup name="face-slide">
          <div
            v-for="face in activeFaces" :key="face.tracking_id"
            class="flex items-center gap-2 px-3 py-2 rounded-xl backdrop-blur-sm"
            :class="face.status === 'match' ? 'bg-success/25 border border-success/40'
                                            : 'bg-error/25 border border-error/40'"
          >
            <div class="w-2 h-2 rounded-full shrink-0"
              :class="face.status === 'match' ? 'bg-success' : 'bg-error'"></div>
            <div class="flex-1 min-w-0">
              <div class="text-white font-semibold text-sm truncate">
                {{ face.full_name || 'Unknown' }}
              </div>
              <div v-if="face.dept_name" class="text-white/60 text-xs truncate">
                {{ face.dept_name }}
              </div>
            </div>
            <div class="text-right shrink-0">
              <div v-if="face.confidence" class="text-white/80 text-xs font-mono">
                {{ (face.confidence * 100).toFixed(1) }}%
              </div>
              <div v-if="face.attendance_logged" class="text-success text-xs font-semibold">
                ✓ logged
              </div>
            </div>
          </div>
        </TransitionGroup>
      </div>
    </div>

    <!-- Bottom control bar -->
    <div class="bg-black/90 border-t border-white/10 px-4 pt-3 pb-safe pb-4 flex flex-col gap-3">

      <!-- Station selector (shown when not streaming) -->
      <div v-if="!streaming" class="flex flex-col gap-2">
        <div class="text-white/50 text-xs uppercase tracking-widest">Select Station</div>
        <select v-model="selectedStationId"
          class="select select-bordered w-full text-sm bg-white/5 border-white/20 text-white">
          <option value="" class="text-black">— select a station —</option>
          <option v-for="s in stations" :key="s.id" :value="s.id" class="text-black">
            {{ s.name }}
          </option>
        </select>
      </div>

      <!-- Stream controls -->
      <div class="flex items-center gap-3">

        <!-- Camera flip (front/back) -->
        <button class="btn btn-circle btn-sm btn-ghost text-white/60"
          @click="flipCamera" :disabled="streaming" title="Flip camera">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
        </button>

        <!-- Main START/STOP button -->
        <button
          class="flex-1 btn text-base font-bold"
          :class="streaming
            ? 'btn-error'
            : (selectedStationId ? 'btn-success' : 'btn-disabled')"
          :disabled="!selectedStationId && !streaming"
          @click="streaming ? stopStream() : startStream()"
        >
          <span v-if="starting" class="loading loading-spinner loading-sm"></span>
          <template v-else>
            {{ streaming ? '■ Stop' : '▶ Start' }}
          </template>
        </button>

        <!-- FPS indicator -->
        <div class="text-right text-white/40 text-xs w-12">
          <div class="font-mono">{{ localFps.toFixed(1) }}</div>
          <div class="text-[10px]">fps</div>
        </div>

      </div>

      <!-- Status row -->
      <div class="flex items-center justify-between text-xs text-white/30">
        <span>{{ frameCount }} frames sent</span>
        <span v-if="streaming">{{ selectedStation?.name }}</span>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { TOKEN_KEY } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import api from '@/api/client'

const toast = useToast()

// ── State ─────────────────────────────────────────────────────────────────────
const stations          = ref([])
const selectedStationId = ref('')
const selectedStation   = computed(() => stations.value.find(s => s.id === selectedStationId.value))

const videoEl  = ref(null)
const canvasEl = ref(null)

const streaming   = ref(false)
const starting    = ref(false)
const paused      = ref(false)
const activeFaces = ref([])
const frameCount  = ref(0)
const localFps    = ref(0)
const facingMode  = ref('environment')  // 'environment' = rear, 'user' = front

let ws            = null
let mediaStream   = null
let _frameTimer   = null
let _fpsTimer     = null
let _frameCounter = 0
let _destroyed    = false
let _reconnecting = false

// ── WebSocket state ────────────────────────────────────────────────────────────
const wsState = ref('disconnected')

const wsStatusLabel = computed(() => ({
  open:          'Live',
  connecting:    'Connecting…',
  closed:        'Reconnecting…',
  disconnected:  'Offline',
}[wsState.value] ?? 'Offline'))

const wsStatusClass = computed(() => {
  if (wsState.value === 'open')       return 'bg-success/20 text-success'
  if (wsState.value === 'connecting') return 'bg-warning/20 text-warning'
  return 'bg-black/50 text-white/40'
})

// ── Load stations ─────────────────────────────────────────────────────────────
onMounted(async () => {
  try {
    const { data } = await api.get('/api/v1/stations')
    stations.value = data
    if (data.length === 1) selectedStationId.value = data[0].id
  } catch {
    toast.error('Failed to load stations')
  }
})

onUnmounted(() => {
  _destroyed = true
  stopStream()
})

// ── Camera ────────────────────────────────────────────────────────────────────
async function _openCamera() {
  if (mediaStream) {
    mediaStream.getTracks().forEach(t => t.stop())
    mediaStream = null
  }
  mediaStream = await navigator.mediaDevices.getUserMedia({
    video: {
      facingMode: facingMode.value,
      width:  { ideal: 640 },
      height: { ideal: 480 },
      frameRate: { ideal: 15, max: 30 },
    },
    audio: false,
  })
  videoEl.value.srcObject = mediaStream
  await new Promise(r => { videoEl.value.onloadedmetadata = r })
}

function flipCamera() {
  facingMode.value = facingMode.value === 'environment' ? 'user' : 'environment'
}

// ── WebSocket ─────────────────────────────────────────────────────────────────
function _connectWS(stationId) {
  const token = localStorage.getItem(TOKEN_KEY)
  const url   = `ws://localhost:8000/api/v1/ws/scan/${stationId}?token=${token}`

  wsState.value = 'connecting'
  ws = new WebSocket(url)

  ws.onopen  = () => { wsState.value = 'open' }

  ws.onmessage = (evt) => {
    try {
      const data = JSON.parse(evt.data)

      // Control messages from Pilot Console via CameraManager
      if (data.action === 'pause') {
        paused.value = true
        _stopFrameLoop()
        return
      }
      if (data.action === 'resume') {
        paused.value = false
        _startFrameLoop()
        return
      }
      if (data.action === 'set_fps') {
        // Restart frame loop at new FPS
        _stopFrameLoop()
        _startFrameLoop(data.fps)
        return
      }
      if (data.action === 'disconnect') {
        toast.warning('Disconnected by Pilot Console: ' + (data.reason || ''))
        stopStream()
        return
      }

      // Recognition result
      activeFaces.value = data.faces || []
      drawBBoxes(data.faces || [])

    } catch { /* ignore malformed messages */ }
  }

  ws.onclose = (e) => {
    wsState.value = 'closed'
    if (_destroyed || !streaming.value) return
    if (e.code === 4001 || e.code === 4003) {
      wsState.value = 'disconnected'
      toast.error('WebSocket: ' + e.reason)
      stopStream()
      return
    }
    // Auto-reconnect
    setTimeout(() => {
      if (!_destroyed && streaming.value) _connectWS(stationId)
    }, 3000)
  }

  ws.onerror = () => ws?.close()
}

// ── Frame loop ────────────────────────────────────────────────────────────────
function _startFrameLoop(fps = 2) {
  _stopFrameLoop()
  const interval = Math.max(33, Math.round(1000 / fps))
  _frameTimer = setInterval(_sendFrame, interval)
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
  offscreen.height = Math.round(640 * video.videoHeight / video.videoWidth)
  offscreen.getContext('2d').drawImage(video, 0, 0, offscreen.width, offscreen.height)

  offscreen.toBlob((blob) => {
    if (!blob || !ws || ws.readyState !== WebSocket.OPEN) return
    blob.arrayBuffer().then((buf) => {
      ws.send(buf)
      frameCount.value++
      _frameCounter++
    })
  }, 'image/jpeg', 0.70)
}

// ── BBox overlay ──────────────────────────────────────────────────────────────
function drawBBoxes(faces) {
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
  }
}

// ── Start / Stop ──────────────────────────────────────────────────────────────
async function startStream() {
  if (!selectedStationId.value) return
  starting.value = true
  try {
    await _openCamera()
    _connectWS(selectedStationId.value)
    streaming.value = true
    paused.value    = false
    frameCount.value = 0
    _startFrameLoop(2)   // start at 2 FPS — backend also gates at max_fps_per_camera
    // FPS counter
    _fpsTimer = setInterval(() => {
      localFps.value   = _frameCounter
      _frameCounter    = 0
    }, 1000)
  } catch (e) {
    toast.error('Camera error: ' + (e.message || e))
  } finally {
    starting.value = false
  }
}

function stopStream() {
  streaming.value = false
  paused.value    = false
  activeFaces.value = []
  _stopFrameLoop()
  if (_fpsTimer) { clearInterval(_fpsTimer); _fpsTimer = null }
  if (ws) { ws.close(); ws = null }
  if (mediaStream) { mediaStream.getTracks().forEach(t => t.stop()); mediaStream = null }
  if (videoEl.value) videoEl.value.srcObject = null
  wsState.value = 'disconnected'
  localFps.value = 0
  _frameCounter  = 0
}
</script>

<style scoped>
.face-slide-enter-active { transition: all 0.2s ease; }
.face-slide-enter-from   { opacity: 0; transform: translateY(8px); }
.face-slide-leave-active { transition: all 0.15s ease; }
.face-slide-leave-to     { opacity: 0; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.pb-safe { padding-bottom: env(safe-area-inset-bottom, 1rem); }
.top-safe { top: env(safe-area-inset-top, 1rem); }
</style>
