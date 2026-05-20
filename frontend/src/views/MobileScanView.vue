<template>
  <!--
    Mobile Scanner — 3-Panel Layout (Sprint 21)
    ────────────────────────────────────────────
    Panel 1 (top ~50vh)   — Camera feed + bbox overlay
    Panel 2 (flex-1)      — Face info panel: all detected faces with rich detail
    Panel 3 (fixed)       — Controls: station, start/stop, camera, audio

    Philosophy: "Smartphone as a Camera Agent"
    Audio (beep + TTS) is primary feedback — operator can look away.
    Face info panel replaces the old HUD center overlay + recent chips
    with a clean scrollable list showing ALL faces simultaneously.
  -->
  <div class="fixed inset-0 bg-black flex flex-col overflow-hidden select-none">

    <!-- ═══════════════════════════════════════════════════════════════════
         PANEL 1 — Camera feed
         ════════════════════════════════════════════════════════════════ -->
    <div class="relative shrink-0 bg-black overflow-hidden" style="height: 50vh; min-height: 200px">
      <video ref="videoEl" class="w-full h-full object-cover" autoplay playsinline muted />
      <canvas ref="canvasEl" class="absolute inset-0 w-full h-full pointer-events-none" />

      <!-- Top bar: WS status + station name + wake lock -->
      <div class="absolute top-0 left-0 right-0 flex items-center justify-between px-3 pt-safe pt-2 pb-2"
        style="background: linear-gradient(rgba(0,0,0,0.6), transparent)">

        <div class="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold backdrop-blur-sm"
          :class="wsStatusClass">
          <span class="w-1.5 h-1.5 rounded-full"
            :class="wsState === 'open' ? 'bg-success animate-pulse' : 'bg-white/40'"></span>
          {{ wsStatusLabel }}
        </div>

        <div class="flex items-center gap-2">
          <span v-if="wakeLockActive" class="text-white/50 text-xs" title="Screen will not turn off">☀️</span>
          <div v-if="selectedStation"
            class="px-2.5 py-1 rounded-full text-xs font-medium bg-black/50 text-white backdrop-blur-sm">
            {{ selectedStation.name }}
          </div>
        </div>
      </div>

      <!-- Paused overlay -->
      <Transition name="fade">
        <div v-if="paused" class="absolute inset-0 flex flex-col items-center justify-center bg-black/75">
          <div class="text-white text-5xl mb-3">⏸</div>
          <div class="text-white text-lg font-bold">Paused by Console</div>
          <div class="text-white/50 text-sm mt-1">Waiting for resume…</div>
        </div>
      </Transition>

      <!-- Not-streaming hint -->
      <Transition name="fade">
        <div v-if="!streaming && !starting"
          class="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-black/50">
          <div class="text-white/30 text-4xl">📷</div>
          <div class="text-white/40 text-sm">เลือก Station แล้วกด Start</div>
        </div>
      </Transition>
    </div>

    <!-- ═══════════════════════════════════════════════════════════════════
         PANEL 2 — Face info panel
         ════════════════════════════════════════════════════════════════ -->
    <div class="flex-1 min-h-0 flex flex-col bg-gray-950">

      <!-- Panel header -->
      <div class="flex items-center justify-between px-4 py-2 border-b border-white/8 shrink-0">
        <div class="text-xs font-semibold text-white/40 uppercase tracking-widest">
          {{ streaming
              ? (displayFaces.length > 0 ? `Check-ins ล่าสุด` : 'กำลังสแกน…')
              : 'ผลการสแกน' }}
        </div>
        <div class="flex items-center gap-2">
          <span v-if="frameCount > 0" class="text-white/20 text-xs font-mono">{{ frameCount }} frames</span>
          <div class="flex items-center gap-1 text-white/25 text-xs">
            <span class="font-mono">{{ localFps.toFixed(1) }}</span>
            <span>fps</span>
          </div>
        </div>
      </div>

      <!-- Face cards list -->
      <div class="flex-1 overflow-y-auto overscroll-contain">

        <!-- Empty state — no faces yet -->
        <div v-if="displayFaces.length === 0"
          class="flex flex-col items-center justify-center h-full gap-2 text-white/25 py-6">
          <div class="text-3xl opacity-60">{{ streaming ? '👁️' : '—' }}</div>
          <div class="text-sm text-center px-6">
            {{ streaming ? 'รอการสแกนครั้งถัดไป…' : 'ยังไม่ได้เริ่มสแกน' }}
          </div>
        </div>

        <!-- Face card list -->
        <TransitionGroup
          name="face-card"
          tag="div"
          class="p-3 flex flex-col gap-2"
        >
          <div
            v-for="face in displayFaces"
            :key="face.tracking_id"
            class="flex items-center gap-3 px-3 py-2.5 rounded-xl border-l-4 transition-colors"
            :class="faceCardClass(face)"
          >
            <!-- Status icon -->
            <div class="text-2xl leading-none shrink-0 w-8 text-center">
              <span v-if="face.status === 'unknown'" class="animate-pulse">⚠️</span>
              <span v-else-if="face.status === 'spoof'">🚫</span>
              <span v-else-if="face.attendance_logged">✅</span>
              <span v-else>🔁</span>
            </div>

            <!-- Main info -->
            <div class="flex-1 min-w-0">
              <div class="font-bold text-white truncate leading-tight"
                style="font-size: clamp(14px, 3.5vw, 17px)">
                {{ face.full_name || (face.status === 'spoof' ? 'Spoof detected' : 'Unknown') }}
              </div>
              <div class="flex items-center gap-2 mt-0.5 flex-wrap">
                <span v-if="face.dept_name" class="text-xs text-white/45 truncate max-w-[120px]">
                  {{ face.dept_name }}
                </span>
                <span v-if="face.emp_code" class="text-xs text-white/30 font-mono">
                  {{ face.emp_code }}
                </span>
              </div>
            </div>

            <!-- Right: status badge + confidence -->
            <div class="text-right shrink-0 flex flex-col items-end gap-0.5">
              <span class="text-xs font-semibold px-2 py-0.5 rounded-full"
                :class="faceStatusBadgeClass(face)">
                {{ faceStatusLabel(face) }}
              </span>
              <span v-if="face.confidence" class="text-xs text-white/25 font-mono">
                {{ (face.confidence * 100).toFixed(1) }}%
              </span>
            </div>
          </div>
        </TransitionGroup>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════════════════════════════
         PANEL 3 — Controls
         ════════════════════════════════════════════════════════════════ -->
    <div class="shrink-0 bg-black/95 border-t border-white/10 px-3 pt-2.5 pb-safe pb-3 flex flex-col gap-2">

      <!-- Station selector (pre-stream only) -->
      <div v-if="!streaming" class="flex flex-col gap-1.5">
        <div class="text-white/35 text-xs uppercase tracking-widest">Select Station</div>
        <select v-model="selectedStationId"
          class="select select-bordered w-full text-sm bg-white/5 border-white/20 text-white">
          <option value="" class="text-black">— select a station —</option>
          <option v-for="s in stations" :key="s.id" :value="s.id" class="text-black">{{ s.name }}</option>
        </select>
      </div>

      <!-- Controls row -->
      <div class="flex items-center gap-2.5">

        <!-- Camera selector: dropdown (3+) or flip button (2) -->
        <div class="shrink-0">
          <select v-if="cameras.length > 2"
            v-model="selectedCameraId"
            class="select select-sm bg-white/10 border-white/20 text-white text-xs w-32">
            <option v-for="(cam, idx) in cameras" :key="cam.deviceId" :value="cam.deviceId"
              class="text-black bg-white">
              {{ cam.label || `Camera ${idx + 1}` }}
            </option>
          </select>

          <button v-else-if="cameras.length === 2"
            class="btn btn-circle btn-sm btn-ghost"
            :class="switchingCamera ? 'loading text-white/30' : 'text-white/55'"
            @click="flipCamera"
            :disabled="switchingCamera"
            title="Flip camera">
            <svg v-if="!switchingCamera" xmlns="http://www.w3.org/2000/svg"
              class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
            </svg>
          </button>
        </div>

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

// ── Stations ──────────────────────────────────────────────────────────────────
const stations          = ref([])
const selectedStationId = ref('')
const selectedStation   = computed(() => stations.value.find(s => s.id === selectedStationId.value))

// ── DOM refs ──────────────────────────────────────────────────────────────────
const videoEl  = ref(null)
const canvasEl = ref(null)

// ── Stream state ──────────────────────────────────────────────────────────────
const streaming      = ref(false)
const starting       = ref(false)
const paused         = ref(false)
const frameCount     = ref(0)
const localFps       = ref(0)
const audioEnabled   = ref(true)
const wakeLockActive = ref(false)

// ── Camera selection ──────────────────────────────────────────────────────────
const cameras          = ref([])
const selectedCameraId = ref('')
const switchingCamera  = ref(false)

let ws               = null
let mediaStream      = null
let _frameTimer      = null
let _fpsTimer        = null
let _frameCounter    = 0
let _destroyed       = false
let _wakeLock        = null
let _offscreenCanvas = null
let _offscreenCtx    = null
let _bboxCtx         = null
let _geo             = null   // cached frame geometry

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

// ── Face info panel ───────────────────────────────────────────────────────────
// displayFaces: sorted list of recently-seen faces
// Each entry persists FACE_PERSIST_MS after last seen (face doesn't vanish between frames)
// Sort order: unknown first (security priority) > logged (new) > repeat match
const displayFaces   = ref([])
const _faceMap       = new Map()   // tracking_id → {face data + animKey + expiresAt}
let   _faceAnimKey   = 0
let   _facePanelTimer = null
const FACE_PERSIST_MS = 7000       // face stays in panel 7s after last seen

function _updateFacePanel(faces) {
  const now = Date.now()
  // Panel = event feed, not "who's in frame"
  // Only show actionable events:
  //   • attendance_logged = true  → fresh check-in today  (show 7s then gone)
  //   • status = 'spoof'          → security alert         (show 7s then gone)
  // Excluded (audio/bbox only, no card):
  //   • already logged (repeat)   → noise if 10 people standing still
  //   • unknown                   → too noisy, handled by audio+vibrate
  const actionable = faces.filter(f =>
    (f.status === 'match' && f.attendance_logged) || f.status === 'spoof'
  )
  for (const face of actionable) {
    const existing = _faceMap.get(face.tracking_id)
    _faceMap.set(face.tracking_id, {
      ...face,
      expiresAt: now + FACE_PERSIST_MS,
      animKey:   existing?.animKey ?? ++_faceAnimKey,
    })
  }
  _rebuildDisplayFaces()
}

function _cleanFacePanel() {
  const now = Date.now()
  let changed = false
  for (const [tid, entry] of _faceMap) {
    if (entry.expiresAt < now) { _faceMap.delete(tid); changed = true }
  }
  if (changed) _rebuildDisplayFaces()
}

function _rebuildDisplayFaces() {
  const entries = [..._faceMap.values()]
  entries.sort((a, b) => {
    // unknown = 0 (top, security), logged = 1, repeat = 2
    const p = f => f.status === 'unknown' || f.status === 'spoof' ? 0
                 : f.attendance_logged ? 1 : 2
    return p(a) - p(b)
  })
  displayFaces.value = entries
}

function _clearFacePanel() {
  _faceMap.clear()
  displayFaces.value = []
}

// ── Face card styling helpers ─────────────────────────────────────────────────
function faceCardClass(face) {
  if (face.status === 'unknown')            return 'bg-red-950/70 border-red-500'
  if (face.status === 'spoof')              return 'bg-orange-950/70 border-orange-500'
  if (face.attendance_logged)               return 'bg-green-950/70 border-green-500'
  return 'bg-gray-900/70 border-gray-600'
}

function faceStatusBadgeClass(face) {
  if (face.status === 'unknown')  return 'bg-red-500/25 text-red-300'
  if (face.status === 'spoof')    return 'bg-orange-500/25 text-orange-300'
  if (face.attendance_logged)     return 'bg-green-500/25 text-green-300'
  return 'bg-white/10 text-white/40'
}

function faceStatusLabel(face) {
  if (face.status === 'unknown')  return '⚠️ Unknown'
  if (face.status === 'spoof')    return '🚫 Spoof'
  if (face.attendance_logged)     return '✓ Logged'
  return '🔁 Already logged'
}

// ── Per-tracking_id audio cooldown (prevents beep spam) ──────────────────────
// cooldown แยกตาม event type:
//   fresh check-in → 5s   (ต้องการได้ยินทุกคนที่ผ่านใหม่)
//   already logged → 60s  (1 soft ack ต่อนาที — ไม่รำคาญถ้า 10 คนยืนแช่)
//   unknown/spoof  → 5s   (security — ยังต้องเตือนบ่อยพอ)
const _audioCooldown        = new Map()
const AUDIO_COOLDOWN_NEW    = 5_000   // ms — fresh log today
const AUDIO_COOLDOWN_REPEAT = 60_000  // ms — already logged (standing still)
const AUDIO_COOLDOWN_ALERT  = 5_000   // ms — unknown / spoof

// ── Unknown debounce — per tracking_id ───────────────────────────────────────
// Wait N frames of consecutive "unknown" before showing audio alert
// Prevents false alerts on first-frame detection before recognition completes
const _unknownFrames   = new Map()   // tracking_id → frame count
const UNKNOWN_HOLD_FRAMES = 2

// ── Wake Lock ─────────────────────────────────────────────────────────────────
async function _acquireWakeLock() {
  if (!('wakeLock' in navigator)) return
  try {
    _wakeLock = await navigator.wakeLock.request('screen')
    wakeLockActive.value = true
    _wakeLock.addEventListener('release', () => { wakeLockActive.value = false })
  } catch { /* not critical */ }
}

async function _releaseWakeLock() {
  if (_wakeLock) { try { await _wakeLock.release() } catch {} _wakeLock = null }
  wakeLockActive.value = false
}

function _onVisibilityChange() {
  if (document.visibilityState === 'visible' && streaming.value) _acquireWakeLock()
}

// ── Audio Engine ──────────────────────────────────────────────────────────────
let _audioCtx = null

function _getAudioCtx() {
  if (!_audioCtx) _audioCtx = new (window.AudioContext || window.webkitAudioContext)()
  if (_audioCtx.state === 'suspended') _audioCtx.resume()
  return _audioCtx
}

function _beep(freq = 880, duration = 0.12, volume = 0.4) {
  if (!audioEnabled.value) return
  try {
    const ctx  = _getAudioCtx()
    const osc  = ctx.createOscillator()
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
  if (!audioEnabled.value || !window.speechSynthesis) return
  try {
    window.speechSynthesis.cancel()
    const utt    = new SpeechSynthesisUtterance(text)
    utt.lang     = 'th-TH'
    utt.rate     = 1.1
    utt.volume   = 1.0
    const voices = window.speechSynthesis.getVoices()
    const thai   = voices.find(v => v.lang.startsWith('th'))
    if (thai) utt.voice = thai
    window.speechSynthesis.speak(utt)
  } catch { /* ignore */ }
}

function _vibrate(pattern) {
  if (navigator.vibrate) navigator.vibrate(pattern)
}

// ── Audio feedback per recognition event ─────────────────────────────────────
function _handleAudioFeedback(face) {
  const now      = Date.now()
  const lastPlay = _audioCooldown.get(face.tracking_id) || 0

  // Pick cooldown based on event type
  const cooldown = (face.status === 'match' && !face.attendance_logged)
    ? AUDIO_COOLDOWN_REPEAT   // already logged — 60s (ไม่รำคาญถ้ายืนแช่)
    : (face.status === 'match' && face.attendance_logged)
      ? AUDIO_COOLDOWN_NEW    // fresh check-in — 5s
      : AUDIO_COOLDOWN_ALERT  // unknown / spoof — 5s

  if (now - lastPlay < cooldown) return
  _audioCooldown.set(face.tracking_id, now)

  // Trim stale entries (prevent unbounded growth in long sessions)
  if (_audioCooldown.size > 50) {
    const cutoff = now - AUDIO_COOLDOWN_REPEAT  // use longest cooldown as TTL
    for (const [id, ts] of _audioCooldown) {
      if (ts < cutoff) _audioCooldown.delete(id)
    }
  }

  if (face.status === 'match') {
    if (face.attendance_logged) {
      _beep(880, 0.12, 0.5)
      setTimeout(() => _speak(face.full_name || 'เข้างานแล้ว'), 100)
    } else {
      _beep(660, 0.06, 0.15)   // already logged — barely audible, just acknowledge
    }
  } else if (face.status === 'unknown') {
    _beep(220, 0.35, 0.6)
    setTimeout(() => _beep(220, 0.35, 0.6), 450)
    _vibrate([200, 100, 200])
  }
}

// ── Load stations ─────────────────────────────────────────────────────────────
onMounted(async () => {
  try {
    const { data } = await api.get('/api/v1/stations')
    stations.value = data
    if (data.length === 1) selectedStationId.value = data[0].id
  } catch { toast.error('Failed to load stations') }
  await _enumerateCameras()
  document.addEventListener('visibilitychange', _onVisibilityChange)
})

onUnmounted(() => {
  _destroyed = true
  stopStream()
  document.removeEventListener('visibilitychange', _onVisibilityChange)
  _audioCooldown.clear()
})

// ── Camera enumeration ────────────────────────────────────────────────────────
async function _enumerateCameras() {
  try {
    cameras.value = (await navigator.mediaDevices.enumerateDevices())
      .filter(d => d.kind === 'videoinput')
  } catch { /* ignore */ }
}

// ── Camera open ───────────────────────────────────────────────────────────────
async function _openCamera() {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error(
      'Camera not available on HTTP.\n' +
      'On Android Chrome: chrome://flags/#unsafely-treat-insecure-origin-as-secure\n' +
      'Add http://' + window.location.hostname + ':5173 → Enable → Relaunch'
    )
  }
  if (mediaStream) { mediaStream.getTracks().forEach(t => t.stop()); mediaStream = null }

  const videoConstraints = selectedCameraId.value
    ? { deviceId: { exact: selectedCameraId.value }, width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 15 } }
    : { facingMode: 'environment',                   width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 15 } }

  mediaStream = await navigator.mediaDevices.getUserMedia({ video: videoConstraints, audio: false })
  await _enumerateCameras()
  const activeId = mediaStream.getVideoTracks()[0]?.getSettings()?.deviceId
  if (activeId) selectedCameraId.value = activeId
  videoEl.value.srcObject = mediaStream
  await new Promise(r => { videoEl.value.onloadedmetadata = r })
}

// ── Camera switch (on-the-fly while streaming) ────────────────────────────────
watch(selectedCameraId, async (newId, oldId) => {
  if (!oldId || newId === oldId || !streaming.value) return
  await _switchCamera()
})

async function _switchCamera() {
  if (switchingCamera.value) return
  switchingCamera.value = true
  try {
    _stopFrameLoop()
    if (mediaStream) { mediaStream.getTracks().forEach(t => t.stop()); mediaStream = null }
    if (videoEl.value) videoEl.value.srcObject = null
    await _openCamera()
    _startFrameLoop(2)
  } catch (e) {
    toast.error('Camera switch failed: ' + (e.message || e))
    stopStream()
  } finally {
    switchingCamera.value = false
  }
}

function flipCamera() {
  if (cameras.value.length < 2 || switchingCamera.value) return
  const idx  = cameras.value.findIndex(c => c.deviceId === selectedCameraId.value)
  const next = (idx + 1) % cameras.value.length
  selectedCameraId.value = cameras.value[next].deviceId
}

// ── WebSocket ─────────────────────────────────────────────────────────────────
function _connectWS(stationId) {
  const token   = localStorage.getItem(TOKEN_KEY)
  const wsProto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const url     = `${wsProto}://${window.location.host}/api/v1/ws/scan/${stationId}?token=${token}`
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
      _updateFacePanel(faces)

      if (faces.length === 0) {
        _unknownFrames.clear()
        return
      }

      // Unknown debounce — per tracking_id
      const newCheckIns = faces.filter(f => f.status === 'match' && f.attendance_logged)
      const unknownFaces = faces.filter(f => f.status === 'unknown')

      for (const mf of newCheckIns) _unknownFrames.delete(mf.tracking_id)

      // Audio feedback for all faces
      faces.forEach(face => {
        // For unknown faces, only fire audio after UNKNOWN_HOLD_FRAMES frames
        if (face.status === 'unknown') {
          const cnt = (_unknownFrames.get(face.tracking_id) || 0) + 1
          _unknownFrames.set(face.tracking_id, cnt)
          if (cnt >= UNKNOWN_HOLD_FRAMES) _handleAudioFeedback(face)
        } else {
          _handleAudioFeedback(face)
        }
      })

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

/**
 * Capture the exact visible portion of the video (object-fit:cover aware).
 * Sends a 640×N crop that matches what the user sees — bbox coordinates
 * from the backend map 1-to-1 back to screen pixels.
 */
function _computeGeo(video) {
  const displayW  = video.clientWidth  || 640
  const displayH  = video.clientHeight || 480
  const videoW    = video.videoWidth
  const videoH    = video.videoHeight
  const videoAR   = videoW / videoH
  const displayAR = displayW / displayH
  let sx, sy, sw, sh
  if (videoAR > displayAR) {
    sh = videoH; sw = videoH * displayAR; sx = (videoW - sw) / 2; sy = 0
  } else {
    sw = videoW; sh = videoW / displayAR; sx = 0; sy = (videoH - sh) / 2
  }
  const SEND_W = 640
  const SEND_H = Math.round(SEND_W / displayAR)
  return { sx, sy, sw, sh, SEND_W, SEND_H, displayW, displayH }
}

function _sendFrame() {
  if (!ws || ws.readyState !== WebSocket.OPEN) return
  const video = videoEl.value
  if (!video || !video.videoWidth) return

  if (!_geo
    || _geo.displayW !== video.clientWidth  || _geo.displayH !== video.clientHeight
    || _geo._videoW  !== video.videoWidth   || _geo._videoH  !== video.videoHeight) {
    _geo = { ..._computeGeo(video), _videoW: video.videoWidth, _videoH: video.videoHeight }
  }
  const { sx, sy, sw, sh, SEND_W, SEND_H } = _geo

  if (!_offscreenCanvas) {
    _offscreenCanvas = document.createElement('canvas')
    _offscreenCtx    = _offscreenCanvas.getContext('2d')
  }
  if (_offscreenCanvas.width !== SEND_W || _offscreenCanvas.height !== SEND_H) {
    _offscreenCanvas.width  = SEND_W
    _offscreenCanvas.height = SEND_H
  }
  _offscreenCtx.drawImage(video, sx, sy, sw, sh, 0, 0, SEND_W, SEND_H)

  _offscreenCanvas.toBlob((blob) => {
    if (!blob || !ws || ws.readyState !== WebSocket.OPEN) return
    ws.send(blob)
    frameCount.value++
    _frameCounter++
  }, 'image/jpeg', 0.70)
}

// ── BBox overlay ──────────────────────────────────────────────────────────────
/**
 * Draw colored bounding boxes on the camera feed.
 * Also draws a small name label below each box so the operator can
 * glance at the camera and know who's who without reading the panel.
 */
function drawBBoxes(faces) {
  const canvas = canvasEl.value
  const video  = videoEl.value
  if (!canvas || !video) return

  const displayW = video.clientWidth  || 640
  const displayH = video.clientHeight || 480
  if (canvas.width  !== displayW) canvas.width  = displayW
  if (canvas.height !== displayH) canvas.height = displayH

  const SEND_W = 640
  const SEND_H = Math.round(SEND_W / (displayW / displayH))
  const scaleX = displayW / SEND_W
  const scaleY = displayH / SEND_H

  if (!_bboxCtx || _bboxCtx.canvas !== canvas) _bboxCtx = canvas.getContext('2d')
  const ctx = _bboxCtx
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  for (const face of faces) {
    const { x, y, w, h } = face.bbox
    const sx = x * scaleX, sy = y * scaleY, sw = w * scaleX, sh = h * scaleY

    const color = face.status === 'match' ? '#22c55e'
                : face.status === 'spoof' ? '#f97316'
                : '#ef4444'

    // Box
    ctx.strokeStyle = color
    ctx.lineWidth   = 3
    ctx.strokeRect(sx, sy, sw, sh)

    // Corner accent (top-left + bottom-right)
    const cs = Math.min(sw, sh) * 0.2
    ctx.lineWidth = 4
    ctx.beginPath()
    ctx.moveTo(sx, sy + cs); ctx.lineTo(sx, sy); ctx.lineTo(sx + cs, sy)
    ctx.moveTo(sx + sw - cs, sy + sh); ctx.lineTo(sx + sw, sy + sh); ctx.lineTo(sx + sw, sy + sh - cs)
    ctx.stroke()

    // Name tag below box (first name only for readability)
    if (face.status === 'match' && face.full_name) {
      const label    = face.full_name.split(' ')[0]
      const tagH     = 20
      const tagY     = sy + sh + 2
      const tagPad   = 6
      ctx.font       = 'bold 12px system-ui, sans-serif'
      const textW    = ctx.measureText(label).width
      const tagW     = textW + tagPad * 2
      const tagX     = sx + (sw - tagW) / 2

      // Background pill
      ctx.fillStyle = 'rgba(0,0,0,0.72)'
      ctx.beginPath()
      ctx.roundRect(tagX, tagY, tagW, tagH, 4)
      ctx.fill()

      // Text
      ctx.fillStyle   = color
      ctx.textAlign   = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(label, tagX + tagW / 2, tagY + tagH / 2)
      ctx.textAlign    = 'start'
      ctx.textBaseline = 'alphabetic'
    }
  }
}

// ── Start / Stop ──────────────────────────────────────────────────────────────
async function startStream() {
  if (!selectedStationId.value) return
  starting.value = true
  try {
    await _openCamera()
    _getAudioCtx()                          // init on user gesture
    _connectWS(selectedStationId.value)
    await _acquireWakeLock()
    streaming.value  = true
    paused.value     = false
    frameCount.value = 0
    _startFrameLoop(2)
    _fpsTimer        = setInterval(() => { localFps.value = _frameCounter; _frameCounter = 0 }, 1000)
    _facePanelTimer  = setInterval(_cleanFacePanel, 1000)   // expire old face cards
  } catch (e) {
    toast.error('Camera error: ' + (e.message || e))
  } finally {
    starting.value = false
  }
}

function stopStream() {
  streaming.value       = false
  paused.value          = false
  switchingCamera.value = false
  _stopFrameLoop()
  _releaseWakeLock()
  _clearFacePanel()
  if (_fpsTimer)       { clearInterval(_fpsTimer);       _fpsTimer = null }
  if (_facePanelTimer) { clearInterval(_facePanelTimer); _facePanelTimer = null }
  if (ws)          { ws.close(); ws = null }
  if (mediaStream) { mediaStream.getTracks().forEach(t => t.stop()); mediaStream = null }
  if (videoEl.value) videoEl.value.srcObject = null
  _offscreenCanvas = null
  _offscreenCtx    = null
  _bboxCtx         = null
  _geo             = null
  wsState.value  = 'disconnected'
  localFps.value = 0
  _frameCounter  = 0
  _unknownFrames.clear()
  _audioCooldown.clear()
}
</script>

<style scoped>
/* iOS safe area */
.pb-safe { padding-bottom: env(safe-area-inset-bottom, 0.75rem); }
.pt-safe { padding-top:    env(safe-area-inset-top,    0px); }

/* Face card enter/leave transitions */
.face-card-enter-active { transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1); }
.face-card-leave-active { transition: all 0.2s ease-in; }
.face-card-enter-from   { opacity: 0; transform: translateX(-12px) scale(0.96); }
.face-card-leave-to     { opacity: 0; transform: translateX(8px) scale(0.97); }
.face-card-move         { transition: transform 0.3s ease; }

/* Generic fade */
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
