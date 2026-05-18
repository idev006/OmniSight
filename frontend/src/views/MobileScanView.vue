<template>
  <!--
    Mobile Scanner — Smartphone Camera Agent (HUD Edition)
    ─────────────────────────────────────────────────────
    Philosophy: "Smartphone as a Camera Agent"
    The OPERATOR holds the phone at the gate and points the rear camera
    at people walking through. The system recognises faces and notifies
    the operator WITHOUT requiring them to look at the screen constantly.

    Key UX pillars:
      1. Wake Lock      — screen never turns off during a session
      2. Audio feedback — beep + TTS name so operator can look away
      3. HUD overlay    — large result card readable in bright sunlight
      4. Vibration      — tactile alert for unknown faces
  -->
  <div class="fixed inset-0 bg-black flex flex-col overflow-hidden select-none">

    <!-- ── Video feed ────────────────────────────────────────────────────── -->
    <div class="relative flex-1 min-h-0">
      <video ref="videoEl" class="w-full h-full object-cover" autoplay playsinline muted />
      <canvas ref="canvasEl" class="absolute inset-0 w-full h-full pointer-events-none" />

      <!-- ── HUD: top bar ──────────────────────────────────────────────── -->
      <div class="absolute top-0 left-0 right-0 flex items-center justify-between px-4 pt-safe pt-3 pb-2"
        style="background: linear-gradient(rgba(0,0,0,0.55), transparent)">

        <!-- WS status -->
        <div class="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold backdrop-blur-sm"
          :class="wsStatusClass">
          <span class="w-1.5 h-1.5 rounded-full"
            :class="wsState === 'open' ? 'bg-success animate-pulse' : 'bg-white/40'"></span>
          {{ wsStatusLabel }}
        </div>

        <!-- Station + Wake Lock indicator -->
        <div class="flex items-center gap-2">
          <span v-if="wakeLockActive" class="text-white/50 text-xs" title="Screen will not turn off">☀️</span>
          <div v-if="selectedStation"
            class="px-2.5 py-1 rounded-full text-xs font-medium bg-black/50 text-white backdrop-blur-sm">
            {{ selectedStation.name }}
          </div>
        </div>
      </div>

      <!-- ── HUD: Result overlay (MATCH) ───────────────────────────────── -->
      <Transition name="result-pop">
        <div v-if="overlay.visible && overlay.type === 'match'"
          class="absolute inset-x-4 rounded-2xl px-6 py-5 flex items-center gap-4"
          style="top: 50%; transform: translateY(-50%); background: rgba(22,163,74,0.92); backdrop-filter: blur(8px);">
          <div class="text-5xl leading-none shrink-0">✅</div>
          <div class="min-w-0 flex-1">
            <div class="text-white font-black leading-tight" style="font-size: clamp(22px,6vw,32px)">
              {{ overlay.full_name }}
            </div>
            <div v-if="overlay.dept_name" class="text-white/80 font-medium mt-0.5" style="font-size: clamp(14px,4vw,18px)">
              {{ overlay.dept_name }}
            </div>
            <div class="flex items-center gap-3 mt-2">
              <span v-if="overlay.emp_code" class="text-white/60 text-xs font-mono">{{ overlay.emp_code }}</span>
              <span v-if="overlay.confidence" class="text-white/60 text-xs font-mono">
                {{ (overlay.confidence * 100).toFixed(1) }}%
              </span>
              <span v-if="overlay.attendance_logged" class="text-white text-xs font-bold bg-white/20 px-2 py-0.5 rounded-full">
                ✓ Logged
              </span>
              <span v-else class="text-white/50 text-xs">Already logged</span>
            </div>
          </div>
        </div>
      </Transition>

      <!-- ── HUD: Result overlay (UNKNOWN) ─────────────────────────────── -->
      <Transition name="result-pop">
        <div v-if="overlay.visible && overlay.type === 'unknown'"
          class="absolute inset-x-4 rounded-2xl px-6 py-5 flex items-center gap-4"
          style="top: 50%; transform: translateY(-50%); background: rgba(220,38,38,0.92); backdrop-filter: blur(8px);">
          <div class="text-5xl leading-none shrink-0 animate-pulse">⚠️</div>
          <div>
            <div class="text-white font-black" style="font-size: clamp(20px,5.5vw,28px)">ใบหน้าไม่รู้จัก</div>
            <div class="text-white/80 mt-1" style="font-size: clamp(13px,3.5vw,16px)">กรุณาตรวจสอบ</div>
          </div>
        </div>
      </Transition>

      <!-- ── HUD: Paused overlay ────────────────────────────────────────── -->
      <Transition name="fade">
        <div v-if="paused" class="absolute inset-0 flex flex-col items-center justify-center bg-black/70">
          <div class="text-white text-5xl mb-3">⏸</div>
          <div class="text-white text-lg font-bold">Paused by Console</div>
          <div class="text-white/50 text-sm mt-1">Waiting for resume…</div>
        </div>
      </Transition>
    </div>

    <!-- ── Bottom control bar ─────────────────────────────────────────────── -->
    <div class="bg-black/95 border-t border-white/10 px-4 pt-3 pb-safe pb-4 flex flex-col gap-3">

      <!-- Station selector (pre-stream) -->
      <div v-if="!streaming" class="flex flex-col gap-2">
        <div class="text-white/40 text-xs uppercase tracking-widest">Select Station</div>
        <select v-model="selectedStationId"
          class="select select-bordered w-full text-sm bg-white/5 border-white/20 text-white">
          <option value="" class="text-black">— select a station —</option>
          <option v-for="s in stations" :key="s.id" :value="s.id" class="text-black">{{ s.name }}</option>
        </select>
      </div>

      <!-- Controls row -->
      <div class="flex items-center gap-3">

        <!-- Camera flip -->
        <button class="btn btn-circle btn-sm btn-ghost text-white/60 shrink-0"
          @click="flipCamera" :disabled="streaming" title="Flip camera">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
        </button>

        <!-- Start / Stop -->
        <button class="flex-1 btn text-base font-bold"
          :class="streaming ? 'btn-error' : (selectedStationId ? 'btn-success' : 'btn-disabled')"
          :disabled="!selectedStationId && !streaming"
          @click="streaming ? stopStream() : startStream()">
          <span v-if="starting" class="loading loading-spinner loading-sm"></span>
          <template v-else>{{ streaming ? '■ Stop' : '▶ Start' }}</template>
        </button>

        <!-- Audio toggle -->
        <button class="btn btn-circle btn-sm btn-ghost shrink-0"
          :class="audioEnabled ? 'text-success' : 'text-white/30'"
          @click="audioEnabled = !audioEnabled"
          :title="audioEnabled ? 'Sound ON' : 'Sound OFF'">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path v-if="audioEnabled" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M15.536 8.464a5 5 0 010 7.072M12 6v12m0 0l-3-3m3 3l3-3M9 9H5l-2 2v2l2 2h4l3-3V12L9 9z"/>
            <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2"/>
          </svg>
        </button>

        <!-- FPS -->
        <div class="text-right text-white/30 text-xs w-10 shrink-0">
          <div class="font-mono">{{ localFps.toFixed(1) }}</div>
          <div class="text-[10px]">fps</div>
        </div>
      </div>

      <!-- Status row -->
      <div class="flex items-center justify-between text-xs text-white/25">
        <span>{{ frameCount }} frames</span>
        <span v-if="lastMatchName" class="text-success/60 truncate ml-2">Last: {{ lastMatchName }}</span>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
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

const streaming      = ref(false)
const starting       = ref(false)
const paused         = ref(false)
const frameCount     = ref(0)
const localFps       = ref(0)
const facingMode     = ref('environment')
const audioEnabled   = ref(true)
const wakeLockActive = ref(false)
const lastMatchName  = ref('')

let ws            = null
let mediaStream   = null
let _frameTimer   = null
let _fpsTimer     = null
let _frameCounter = 0
let _destroyed    = false
let _wakeLock     = null

// ── Overlay state (HUD result card) ──────────────────────────────────────────
const overlay = ref({
  visible:          false,
  type:             'match',   // 'match' | 'unknown'
  full_name:        '',
  dept_name:        '',
  emp_code:         '',
  confidence:       0,
  attendance_logged: false,
})
let _overlayTimer = null

// ── Per-tracking_id cooldown (prevent beep spam) ──────────────────────────────
// Map<tracking_id, timestamp_ms> — cooldown 3 s per face
const _audioCooldown = new Map()
const AUDIO_COOLDOWN_MS = 3000

// ── WS status ─────────────────────────────────────────────────────────────────
const wsState = ref('disconnected')
const wsStatusLabel = computed(() => ({
  open:         'Live',
  connecting:   'Connecting…',
  closed:       'Reconnecting…',
  disconnected: 'Offline',
}[wsState.value] ?? 'Offline'))
const wsStatusClass = computed(() => {
  if (wsState.value === 'open')       return 'bg-success/20 text-success'
  if (wsState.value === 'connecting') return 'bg-warning/20 text-warning'
  return 'bg-black/50 text-white/40'
})

// ── Wake Lock ─────────────────────────────────────────────────────────────────
async function _acquireWakeLock() {
  if (!('wakeLock' in navigator)) return   // not supported (old iOS)
  try {
    _wakeLock = await navigator.wakeLock.request('screen')
    wakeLockActive.value = true
    _wakeLock.addEventListener('release', () => { wakeLockActive.value = false })
  } catch { /* denied — not critical */ }
}

async function _releaseWakeLock() {
  if (_wakeLock) { try { await _wakeLock.release() } catch {} _wakeLock = null }
  wakeLockActive.value = false
}

// Re-acquire when tab becomes visible again (OS can release it on visibility change)
function _onVisibilityChange() {
  if (document.visibilityState === 'visible' && streaming.value) _acquireWakeLock()
}

// ── Audio Engine ──────────────────────────────────────────────────────────────
// AudioContext must be created after a user gesture (browser security requirement)
let _audioCtx = null

function _getAudioCtx() {
  if (!_audioCtx) _audioCtx = new (window.AudioContext || window.webkitAudioContext)()
  if (_audioCtx.state === 'suspended') _audioCtx.resume()
  return _audioCtx
}

function _beep(freq = 880, duration = 0.12, volume = 0.4) {
  if (!audioEnabled.value) return
  try {
    const ctx = _getAudioCtx()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.connect(gain); gain.connect(ctx.destination)
    osc.frequency.value = freq
    osc.type = 'sine'
    gain.gain.setValueAtTime(volume, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration)
    osc.start(ctx.currentTime)
    osc.stop(ctx.currentTime + duration + 0.05)
  } catch { /* ignore */ }
}

function _speak(text) {
  if (!audioEnabled.value) return
  if (!window.speechSynthesis) return
  try {
    window.speechSynthesis.cancel()
    const utt = new SpeechSynthesisUtterance(text)
    utt.lang = 'th-TH'
    utt.rate = 1.1
    utt.volume = 1.0
    // Try Thai voice, fallback to any available
    const voices = window.speechSynthesis.getVoices()
    const thaiVoice = voices.find(v => v.lang.startsWith('th'))
    if (thaiVoice) utt.voice = thaiVoice
    window.speechSynthesis.speak(utt)
  } catch { /* ignore */ }
}

function _vibrate(pattern) {
  if (navigator.vibrate) navigator.vibrate(pattern)
}

// ── Audio feedback per recognition event ─────────────────────────────────────
function _handleAudioFeedback(face) {
  const now = Date.now()
  const lastPlayed = _audioCooldown.get(face.tracking_id) || 0
  if (now - lastPlayed < AUDIO_COOLDOWN_MS) return   // cooldown — skip
  _audioCooldown.set(face.tracking_id, now)

  if (face.status === 'match') {
    if (face.attendance_logged) {
      // First log today — prominent beep + TTS
      _beep(880, 0.12, 0.5)
      setTimeout(() => _speak(face.full_name || 'เข้างานแล้ว'), 100)
    } else {
      // Already logged (cooldown) — soft acknowledge
      _beep(660, 0.08, 0.25)
    }
  } else if (face.status === 'unknown') {
    // Unknown — double low beep + vibrate
    _beep(220, 0.35, 0.6)
    setTimeout(() => _beep(220, 0.35, 0.6), 450)
    _vibrate([200, 100, 200])
  }
}

// ── Result overlay ────────────────────────────────────────────────────────────
function _showOverlay(face) {
  if (_overlayTimer) clearTimeout(_overlayTimer)

  if (face.status === 'match') {
    overlay.value = {
      visible: true, type: 'match',
      full_name:         face.full_name || 'Unknown',
      dept_name:         face.dept_name || '',
      emp_code:          face.emp_code  || '',
      confidence:        face.confidence,
      attendance_logged: face.attendance_logged,
    }
    lastMatchName.value = face.full_name || ''
    // Auto-dismiss match card after 2.5 s
    _overlayTimer = setTimeout(() => { overlay.value.visible = false }, 2500)

  } else {
    overlay.value = { visible: true, type: 'unknown',
      full_name: '', dept_name: '', emp_code: '', confidence: 0, attendance_logged: false }
    // Unknown card stays until next frame clears it (handled in onmessage)
  }
}

function _clearOverlay() {
  if (_overlayTimer) clearTimeout(_overlayTimer)
  overlay.value.visible = false
}

// ── Load stations ─────────────────────────────────────────────────────────────
onMounted(async () => {
  try {
    const { data } = await api.get('/api/v1/stations')
    stations.value = data
    if (data.length === 1) selectedStationId.value = data[0].id
  } catch { toast.error('Failed to load stations') }
  document.addEventListener('visibilitychange', _onVisibilityChange)
})

onUnmounted(() => {
  _destroyed = true
  stopStream()
  document.removeEventListener('visibilitychange', _onVisibilityChange)
  _audioCooldown.clear()
})

// ── Camera ────────────────────────────────────────────────────────────────────
async function _openCamera() {
  // navigator.mediaDevices is undefined on HTTP non-localhost (browser security policy)
  // Requires HTTPS in production, or Chrome flag on dev:
  //   chrome://flags/#unsafely-treat-insecure-origin-as-secure → add http://<PC-IP>:5173
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    throw new Error(
      'Camera not available on HTTP.\n' +
      'On Android Chrome: go to chrome://flags/#unsafely-treat-insecure-origin-as-secure\n' +
      'Add http://' + window.location.hostname + ':5173 → Enable → Relaunch'
    )
  }
  if (mediaStream) { mediaStream.getTracks().forEach(t => t.stop()); mediaStream = null }
  mediaStream = await navigator.mediaDevices.getUserMedia({
    video: { facingMode: facingMode.value, width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 15 } },
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
  const token    = localStorage.getItem(TOKEN_KEY)
  const wsHost   = window.location.hostname
  const wsProto  = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const url      = `${wsProto}://${wsHost}:8000/api/v1/ws/scan/${stationId}?token=${token}`
  wsState.value = 'connecting'
  ws = new WebSocket(url)

  ws.onopen = () => { wsState.value = 'open' }

  ws.onmessage = (evt) => {
    try {
      const data = JSON.parse(evt.data)

      // Control messages from Pilot Console
      if (data.action === 'pause')      { paused.value = true;  _stopFrameLoop(); return }
      if (data.action === 'resume')     { paused.value = false; _startFrameLoop(); return }
      if (data.action === 'set_fps')    { _stopFrameLoop(); _startFrameLoop(data.fps); return }
      if (data.action === 'disconnect') {
        toast.warning('Disconnected by Pilot Console: ' + (data.reason || ''))
        stopStream(); return
      }

      // Recognition result
      const faces = data.faces || []
      drawBBoxes(faces)

      if (faces.length === 0) {
        // No faces in frame — clear unknown overlay (match auto-dismisses via timer)
        if (overlay.value.type === 'unknown') _clearOverlay()
        return
      }

      // Process each face — show overlay for the most prominent one (first)
      // Play audio for ALL faces in frame
      faces.forEach(face => _handleAudioFeedback(face))
      _showOverlay(faces[0])

    } catch { /* ignore malformed */ }
  }

  ws.onclose = (e) => {
    wsState.value = 'closed'
    if (_destroyed || !streaming.value) return
    if (e.code === 4001 || e.code === 4003) {
      wsState.value = 'disconnected'
      toast.error('WebSocket: ' + e.reason)
      stopStream(); return
    }
    setTimeout(() => { if (!_destroyed && streaming.value) _connectWS(stationId) }, 3000)
  }

  ws.onerror = () => ws?.close()
}

// ── Frame loop ────────────────────────────────────────────────────────────────
function _startFrameLoop(fps = 2) {
  _stopFrameLoop()
  _frameTimer = setInterval(_sendFrame, Math.max(33, Math.round(1000 / fps)))
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
    blob.arrayBuffer().then((buf) => { ws.send(buf); frameCount.value++; _frameCounter++ })
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
    ctx.lineWidth   = 3
    ctx.strokeRect(x * scaleX, y * scaleY, w * scaleX, h * scaleY)
  }
}

// ── Start / Stop ──────────────────────────────────────────────────────────────
async function startStream() {
  if (!selectedStationId.value) return
  starting.value = true
  try {
    await _openCamera()
    // Init AudioContext on user gesture (required by browsers)
    _getAudioCtx()
    _connectWS(selectedStationId.value)
    await _acquireWakeLock()
    streaming.value  = true
    paused.value     = false
    frameCount.value = 0
    _startFrameLoop(2)
    _fpsTimer = setInterval(() => { localFps.value = _frameCounter; _frameCounter = 0 }, 1000)
  } catch (e) {
    toast.error('Camera error: ' + (e.message || e))
  } finally {
    starting.value = false
  }
}

function stopStream() {
  streaming.value = false
  paused.value    = false
  _clearOverlay()
  _stopFrameLoop()
  _releaseWakeLock()
  if (_fpsTimer)    { clearInterval(_fpsTimer); _fpsTimer = null }
  if (ws)           { ws.close(); ws = null }
  if (mediaStream)  { mediaStream.getTracks().forEach(t => t.stop()); mediaStream = null }
  if (videoEl.value) videoEl.value.srcObject = null
  wsState.value  = 'disconnected'
  localFps.value = 0
  _frameCounter  = 0
  _audioCooldown.clear()
}
</script>

<style scoped>
/* Result overlay pop animation */
.result-pop-enter-active { transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1); }
.result-pop-leave-active { transition: all 0.25s ease-in; }
.result-pop-enter-from   { opacity: 0; transform: translateY(-50%) scale(0.85); }
.result-pop-leave-to     { opacity: 0; transform: translateY(-50%) scale(0.92); }

/* Paused overlay */
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* iOS safe area */
.pb-safe { padding-bottom: env(safe-area-inset-bottom, 1rem); }
.pt-safe { padding-top:    env(safe-area-inset-top,    0px); }
</style>
