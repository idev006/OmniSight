<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-start justify-between gap-3">
      <div>
        <h1 class="text-xl font-bold tracking-wide">Live Scan</h1>
        <p class="text-sm text-base-content/40 mt-0.5">Webcam face recognition</p>
      </div>
      <div class="flex items-center gap-2 flex-wrap justify-end">
        <!-- WS status -->
        <div class="flex items-center gap-1.5 text-xs opacity-50">
          <span class="w-1.5 h-1.5 rounded-full"
            :class="wsState === 'open' ? 'bg-success animate-pulse' : 'bg-base-300'"></span>
          {{ wsState === 'open' ? 'Live' : wsState === 'connecting' ? 'Connecting…' : 'Offline' }}
        </div>

        <!-- Camera selector (แสดงเมื่อมีกล้องมากกว่า 1 ตัว) -->
        <select v-if="cameras.length > 1"
          v-model="selectedCamera"
          class="select select-bordered select-sm w-48"
          :disabled="streaming"
          title="เลือกกล้อง">
          <option v-for="cam in cameras" :key="cam.deviceId" :value="cam.deviceId">
            {{ cam.label || `Camera ${cameras.indexOf(cam) + 1}` }}
          </option>
        </select>

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

const stations        = ref([])
const selectedStation = ref('')
const activeFaces     = ref([])
const videoEl         = ref(null)
const canvasEl        = ref(null)

const wsState        = ref('disconnected')
const streaming      = ref(false)
const pausedByServer = ref(false)
const localFps       = ref(0)

// ── Camera selection ──────────────────────────────────────────────────────────
const cameras        = ref([])   // MediaDeviceInfo[] — videoInput devices
const selectedCamera = ref('')   // deviceId ที่เลือก

let ws            = null
let mediaStream   = null
let _frameTimer   = null
let _fpsTimer     = null
let _rafHandle    = null   // requestAnimationFrame handle for overlay render loop
let _fpsCounter   = 0
let _lastFaceTs   = 0      // timestamp of last recognition result
let _destroyed    = false

// Overlay fade config — boxes stay sharp for FADE_START ms, then fade to 0 by FADE_END ms
const FADE_START_MS = 1200
const FADE_END_MS   = 2400

// ── Camera enumeration ────────────────────────────────────────────────────────
async function _enumerateCameras() {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices()
    cameras.value = devices.filter(d => d.kind === 'videoinput')
    // ถ้ายังไม่ได้เลือก → ใช้ตัวแรก
    if (!selectedCamera.value && cameras.value.length > 0) {
      selectedCamera.value = cameras.value[0].deviceId
    }
  } catch { /* permission denied or not supported */ }
}

// ── Station loading ───────────────────────────────────────────────────────────
onMounted(async () => {
  const { data } = await api.get('/api/v1/stations')
  stations.value = data
  await _enumerateCameras()
})

onUnmounted(() => {
  _destroyed = true
  _stop()
})

// ── React to station or camera selection ─────────────────────────────────────
watch(selectedStation, (id) => {
  _stop()
  if (id) _start(id)
})

// เมื่อเปลี่ยนกล้องระหว่าง streaming → restart stream
watch(selectedCamera, (newId, oldId) => {
  if (!oldId || !streaming.value) return   // ยังไม่ได้ stream อยู่ → ไม่ต้องทำอะไร
  _stop()
  if (selectedStation.value) _start(selectedStation.value)
})

// ── Start scanning ────────────────────────────────────────────────────────────
async function _start(stationId) {
  try {
    // Open webcam — ใช้ deviceId ที่เลือก (ถ้ามี)
    const videoConstraints = {
      width: { ideal: 640 },
      height: { ideal: 480 },
      frameRate: { ideal: 15 },
    }
    if (selectedCamera.value) videoConstraints.deviceId = { exact: selectedCamera.value }
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: videoConstraints,
      audio: false,
    })
    // Re-enumerate หลังได้ permission → ได้ label ที่ถูกต้อง
    await _enumerateCameras()
    // อัปเดต selectedCamera ให้ตรงกับกล้องที่ stream จริง
    const activeDeviceId = mediaStream.getVideoTracks()[0]?.getSettings()?.deviceId
    if (activeDeviceId) selectedCamera.value = activeDeviceId
    videoEl.value.srcObject = mediaStream
    streaming.value = true
    pausedByServer.value = false

    // Connect WebSocket — use TOKEN_KEY (not hardcoded 'token')
    // ใช้ window.location.hostname แทน localhost — ทำงานได้ทั้งจาก PC และมือถือ
    const token   = localStorage.getItem(TOKEN_KEY)
    const wsProto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    wsState.value = 'connecting'
    ws = new WebSocket(
      `${wsProto}://${window.location.host}/api/v1/ws/scan/${stationId}?token=${token}`
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

        // Recognition results — store timestamp; render loop handles drawing
        activeFaces.value = data.faces || []
        _lastFaceTs = Date.now()
      } catch { /* ignore */ }
    }

    ws.onclose = (e) => {
      wsState.value = 'closed'
      if (_destroyed || !selectedStation.value) return
      if (e.code === 4001 || e.code === 4003) { wsState.value = 'disconnected'; return }
      setTimeout(() => { if (!_destroyed && selectedStation.value) _start(stationId) }, 2000)
    }

    ws.onerror = () => ws?.close()

    // Start frame send loop (2 fps) and continuous overlay render loop
    _startFrameLoop()
    _startRenderLoop()

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
  _lastFaceTs          = 0

  _stopFrameLoop()
  _stopRenderLoop()
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

// ── Continuous overlay render loop (requestAnimationFrame) ───────────────────
// Runs independently of WebSocket — draws the latest known faces every frame.
// Boxes fade out gradually after FADE_START_MS ms without a new result,
// so the UI never "snaps" black between recognition responses.
function _startRenderLoop() {
  _stopRenderLoop()
  function loop() {
    const faces = activeFaces.value
    if (faces.length > 0) {
      const age = _lastFaceTs ? Date.now() - _lastFaceTs : 0
      let opacity = 1
      if (age > FADE_START_MS) {
        opacity = Math.max(0, 1 - (age - FADE_START_MS) / (FADE_END_MS - FADE_START_MS))
      }
      _drawBBoxes(faces, opacity)
    } else if (canvasEl.value) {
      const ctx = canvasEl.value.getContext('2d')
      ctx?.clearRect(0, 0, canvasEl.value.width, canvasEl.value.height)
    }
    _rafHandle = requestAnimationFrame(loop)
  }
  _rafHandle = requestAnimationFrame(loop)
}

function _stopRenderLoop() {
  if (_rafHandle) { cancelAnimationFrame(_rafHandle); _rafHandle = null }
}

// ── Bounding box overlay ──────────────────────────────────────────────────────
/**
 * ScanView ส่ง frame แบบ fixed 640×480 เสมอ
 * Video element ใช้ object-contain → อาจมี letterbox/pillarbox
 *
 * ต้องคำนวณ:
 *   1. rendered area ของ video จริงภายใน container (object-contain)
 *   2. offset ของ letterbox / pillarbox
 *   3. scale จาก sent frame (640×480) → rendered area
 */
function _drawBBoxes(faces, opacity = 1) {
  const canvas = canvasEl.value
  const video  = videoEl.value
  if (!canvas || !video) return

  const cW = video.clientWidth
  const cH = video.clientHeight
  canvas.width  = cW
  canvas.height = cH

  // Native video AR vs container AR
  const videoAR     = (video.videoWidth  || 640) / (video.videoHeight || 480)
  const containerAR = cW / cH

  let renderedW, renderedH, offsetX, offsetY
  if (videoAR > containerAR) {
    renderedW = cW
    renderedH = cW / videoAR
    offsetX   = 0
    offsetY   = (cH - renderedH) / 2
  } else {
    renderedH = cH
    renderedW = cH * videoAR
    offsetX   = (cW - renderedW) / 2
    offsetY   = 0
  }

  const scaleX = renderedW / 640
  const scaleY = renderedH / 480

  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, cW, cH)
  ctx.globalAlpha = opacity

  for (const face of faces) {
    const { x, y, w, h } = face.bbox
    const dx = offsetX + x * scaleX
    const dy = offsetY + y * scaleY
    const dw = w * scaleX
    const dh = h * scaleY

    const color = face.status === 'match' ? '#22c55e' : '#ef4444'
    ctx.strokeStyle = color
    ctx.lineWidth   = 2
    ctx.strokeRect(dx, dy, dw, dh)

    // Label background + text
    if (face.full_name || face.status === 'unknown') {
      const label = face.status === 'match'
        ? `${face.full_name} ${(face.confidence * 100).toFixed(0)}%`
        : 'Unknown'
      ctx.font = 'bold 13px sans-serif'
      const textW = ctx.measureText(label).width
      ctx.fillStyle = color
      ctx.fillRect(dx, dy - 18, textW + 6, 18)
      ctx.fillStyle = '#fff'
      ctx.fillText(label, dx + 3, dy - 4)
    }
  }

  ctx.globalAlpha = 1
}
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
