<template>
  <!--
    Pilot Console — Control Tower design
    Philosophy: Glanceability · Density · Alerting · Control in-place · Station grouping
    Admin sees EVERYTHING and controls EVERYTHING from one screen without navigating away.
  -->
  <div class="flex flex-col gap-0 h-[calc(100vh-6rem)]">

    <!-- ── Top Bar ──────────────────────────────────────────────────────── -->
    <div class="flex items-center justify-between px-1 pb-3 gap-4 shrink-0">
      <div class="flex items-center gap-3">
        <h1 class="text-lg font-bold tracking-wide">Pilot Console</h1>
        <!-- WS connection badge -->
        <div class="flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium border"
          :class="wsBadge">
          <span class="w-1.5 h-1.5 rounded-full" :class="wsDot"></span>
          {{ wsLabel }}
        </div>
        <!-- Unknown face alert badge -->
        <Transition name="fade">
          <div v-if="unknownAlertCount > 0"
            class="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-error text-error-content animate-pulse cursor-pointer"
            @click="scrollToUnknown">
            ⚠ {{ unknownAlertCount }} UNKNOWN
          </div>
        </Transition>
      </div>
      <div class="flex items-center gap-2">
        <!-- Today stats pills -->
        <div class="hidden sm:flex items-center gap-1.5 text-xs text-base-content/50">
          <span class="font-mono font-semibold text-success">{{ todayStats.present }}</span>
          <span>present today</span>
        </div>
        <button class="btn btn-ghost btn-xs" @click="clearAlerts" title="Clear alerts">Clear alerts</button>
        <button class="btn btn-ghost btn-xs" @click="reconnect" :disabled="wsState === 'connecting'">Reconnect</button>
      </div>
    </div>

    <!-- ── Main 3-column layout ─────────────────────────────────────────── -->
    <div class="flex gap-4 flex-1 min-h-0">

      <!-- ── Column 1: Station Tree + Stats (narrow) ─────────────────── -->
      <div class="w-48 shrink-0 flex flex-col gap-3 overflow-y-auto pr-0.5">

        <!-- Today Summary -->
        <div class="rounded-xl border border-base-300 bg-base-100 p-3 flex flex-col gap-2">
          <div class="text-[10px] uppercase tracking-widest opacity-40 font-bold">Today</div>
          <div class="flex justify-between items-center text-xs">
            <span class="text-base-content/60">Present</span>
            <span class="font-bold text-success font-mono">{{ todayStats.present }}</span>
          </div>
          <div class="flex justify-between items-center text-xs">
            <span class="text-base-content/60">Total scans</span>
            <span class="font-bold font-mono">{{ todayStats.total }}</span>
          </div>
          <div class="flex justify-between items-center text-xs">
            <span class="text-base-content/60">Cameras live</span>
            <span class="font-bold text-success font-mono">{{ liveCount }}</span>
          </div>
        </div>

        <!-- Station Tree -->
        <div class="rounded-xl border border-base-300 bg-base-100 p-3 flex flex-col gap-2">
          <div class="text-[10px] uppercase tracking-widest opacity-40 font-bold">Stations</div>
          <div v-if="stationGroups.length === 0" class="text-xs text-base-content/25">No stations</div>
          <div v-for="grp in stationGroups" :key="grp.station_id"
            class="cursor-pointer rounded-lg px-2 py-1.5 transition-colors"
            :class="selectedStation === grp.station_id ? 'bg-primary/10 text-primary' : 'hover:bg-base-200'"
            @click="toggleStation(grp.station_id)">
            <div class="flex items-center justify-between gap-1">
              <span class="text-xs font-medium truncate">{{ grp.station_name }}</span>
              <span class="badge badge-xs shrink-0"
                :class="grp.live > 0 ? 'badge-success' : 'badge-ghost'">
                {{ grp.live }}/{{ grp.total }}
              </span>
            </div>
          </div>
        </div>

        <!-- Camera type legend -->
        <div class="rounded-xl border border-base-300 bg-base-100 p-3 flex flex-col gap-1.5">
          <div class="text-[10px] uppercase tracking-widest opacity-40 font-bold mb-1">Types</div>
          <div class="flex items-center gap-1.5 text-[10px] text-base-content/50">
            <span class="badge badge-xs badge-info badge-outline">WEBCAM</span>
          </div>
          <div class="flex items-center gap-1.5 text-[10px] text-base-content/50">
            <span class="badge badge-xs badge-primary badge-outline">IP_CAMERA</span>
          </div>
          <div class="flex items-center gap-1.5 text-[10px] text-base-content/50">
            <span class="badge badge-xs badge-secondary badge-outline">CCTV</span>
          </div>
          <div class="flex items-center gap-1.5 text-[10px] text-base-content/50">
            <span class="badge badge-xs badge-accent badge-outline">SMARTPHONE</span>
          </div>
        </div>
      </div>

      <!-- ── Column 2: Camera Grid ────────────────────────────────────── -->
      <div class="flex-1 min-w-0 overflow-y-auto pr-0.5">

        <div v-if="filteredGroups.length === 0 && wsState === 'open'"
          class="flex flex-col items-center justify-center h-full text-base-content/25">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1"
              d="M3 7a1 1 0 011-1h3l2-2h6l2 2h3a1 1 0 011 1v11a1 1 0 01-1 1H4a1 1 0 01-1-1V7z" />
            <circle cx="12" cy="13" r="3" stroke="currentColor" stroke-width="1" fill="none" />
          </svg>
          <p class="text-sm">No cameras connected</p>
          <p class="text-xs mt-1 opacity-60">Connect a camera at <RouterLink to="/scan" class="link">Live Scan</RouterLink></p>
        </div>

        <div v-else class="flex flex-col gap-5">
          <!-- Each station section -->
          <div v-for="grp in filteredGroups" :key="grp.station_id">
            <!-- Station header -->
            <div class="flex items-center gap-2 mb-2">
              <div class="w-1.5 h-1.5 rounded-full"
                :class="grp.live > 0 ? 'bg-success' : 'bg-base-300'"></div>
              <span class="text-xs font-semibold uppercase tracking-wider opacity-50">
                {{ grp.station_name }}
              </span>
              <div class="flex-1 h-px bg-base-300/50"></div>
              <span class="text-[10px] text-base-content/30">
                {{ grp.live }} live / {{ grp.cameras.length }} cameras
              </span>
            </div>

            <!-- Camera tiles for this station -->
            <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2.5">
              <div
                v-for="cam in grp.cameras" :key="cam.camera_id"
                class="rounded-xl border transition-all duration-300"
                :class="[tileBorder(cam.status), cam._alert ? 'ring-2 ring-error/50 ring-offset-1' : '']"
              >
                <div class="p-3 flex flex-col gap-2">

                  <!-- Header row: dot + name + type badge -->
                  <div class="flex items-start gap-2">
                    <div class="w-2 h-2 rounded-full shrink-0 mt-1"
                      :class="statusDot(cam.status)"></div>
                    <div class="flex-1 min-w-0">
                      <div class="font-semibold text-sm leading-tight truncate">
                        {{ cam.camera_name || cam.camera_id }}
                      </div>
                      <div v-if="cam.camera_name" class="text-[10px] text-base-content/25 font-mono truncate">
                        {{ cam.camera_id.slice(0, 12) }}…
                      </div>
                    </div>
                    <span class="badge badge-xs shrink-0" :class="typeBadge(cam.camera_type)">
                      {{ cam.camera_type }}
                    </span>
                  </div>

                  <!-- Last matched person (if any) -->
                  <div v-if="cam._lastPerson" class="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-success/8 border border-success/20">
                    <div class="avatar placeholder shrink-0">
                      <div class="bg-success/20 text-success rounded-full w-6 text-[10px] font-bold">
                        <span>{{ cam._lastPerson.full_name?.[0] || '?' }}</span>
                      </div>
                    </div>
                    <div class="flex-1 min-w-0">
                      <div class="text-xs font-semibold truncate text-success-content/80">
                        {{ cam._lastPerson.full_name }}
                      </div>
                      <div class="text-[10px] text-success/60">
                        {{ (cam._lastPerson.confidence * 100).toFixed(1) }}% · {{ cam._lastPerson.time }}
                      </div>
                    </div>
                  </div>

                  <!-- Unknown face alert banner -->
                  <div v-if="cam._alert"
                    class="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-error/10 border border-error/30 animate-pulse"
                    ref="alertTiles">
                    <span class="text-error text-xs font-bold">⚠ Unknown face</span>
                    <button class="btn btn-xs btn-ghost text-error ml-auto" @click="cam._alert = false">✕</button>
                  </div>

                  <!-- FPS + frames metrics -->
                  <div class="flex items-center gap-3 text-[10px] text-base-content/35">
                    <span class="font-mono">{{ (cam.fps || 0).toFixed(1) }} fps</span>
                    <span>·</span>
                    <span class="font-mono">{{ cam.frame_count || 0 }} frames</span>
                    <span v-if="cam.status === 'paused'" class="text-warning font-semibold">■ PAUSED</span>
                    <span v-else-if="cam.status === 'offline'" class="text-base-content/25">offline</span>
                  </div>

                  <!-- Controls -->
                  <div class="flex gap-1.5 pt-2 border-t border-base-300/40">
                    <template v-if="cam.status === 'active'">
                      <button class="btn btn-xs btn-warning flex-1"
                        @click="sendCmd('pause_camera', cam.camera_id)">⏸ Pause</button>
                    </template>
                    <template v-else-if="cam.status === 'paused'">
                      <button class="btn btn-xs btn-success flex-1"
                        @click="sendCmd('resume_camera', cam.camera_id)">▶ Resume</button>
                    </template>
                    <template v-else>
                      <div class="flex-1"></div>
                    </template>
                    <button class="btn btn-xs btn-ghost text-error/70 hover:text-error hover:bg-error/10"
                      title="Disconnect" @click="confirmDisconnect(cam)">
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── Column 3: Event Feed ────────────────────────────────────── -->
      <div class="w-64 shrink-0 flex flex-col gap-2 min-h-0">
        <div class="flex items-center justify-between shrink-0">
          <div class="text-[10px] uppercase tracking-widest opacity-40 font-bold">Live Events</div>
          <button class="btn btn-ghost btn-xs opacity-30 hover:opacity-70" @click="events = []">
            Clear
          </button>
        </div>

        <div class="flex-1 overflow-y-auto flex flex-col gap-1 min-h-0" ref="feedEl">
          <div v-if="events.length === 0"
            class="text-[11px] text-base-content/20 text-center py-8">
            Waiting for events…
          </div>

          <TransitionGroup name="feed-slide">
            <div
              v-for="ev in events" :key="ev._key"
              class="rounded-lg px-2.5 py-2 text-xs border flex-shrink-0"
              :class="eventStyle(ev)"
            >
              <div class="flex items-center justify-between mb-1">
                <span class="font-bold uppercase tracking-wider text-[10px]">
                  {{ eventLabel(ev) }}
                </span>
                <span class="opacity-30 font-mono text-[9px]">{{ ev._time }}</span>
              </div>

              <!-- Attendance logged -->
              <template v-if="ev.event === 'attendance_logged'">
                <div class="font-semibold truncate leading-tight">{{ ev.full_name || ev.employee_id }}</div>
                <div class="opacity-50 mt-0.5 flex items-center gap-1 text-[10px]">
                  <span class="font-mono truncate">{{ ev.camera_id?.slice(0,12) }}</span>
                  <span>· {{ (ev.confidence * 100).toFixed(1) }}%</span>
                </div>
              </template>

              <!-- Unknown face -->
              <template v-else-if="ev.event === 'unknown_face'">
                <div class="font-semibold">Unknown face</div>
                <div class="opacity-60 text-[10px] truncate mt-0.5">{{ ev.camera_id?.slice(0,12) }}</div>
              </template>

              <!-- Cooldown -->
              <template v-else-if="ev.event === 'attendance_cooldown'">
                <div class="truncate opacity-70 leading-tight">{{ ev.full_name || ev.employee_id }}</div>
                <div class="opacity-35 text-[10px]">within cooldown</div>
              </template>

              <!-- Camera connect/disconnect -->
              <template v-else>
                <div class="truncate opacity-60 text-[10px] font-mono">{{ ev.camera_id }}</div>
              </template>

            </div>
          </TransitionGroup>
        </div>
      </div>

    </div><!-- end main 3-col -->
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, reactive } from 'vue'
import { TOKEN_KEY, useAuthStore } from '@/stores/auth'
import { useConfirm } from '@/composables/useConfirm'
import { useToast } from '@/composables/useToast'
import api from '@/api/client'

const auth  = useAuthStore()
const { confirm } = useConfirm()
const toast = useToast()

// ── WebSocket ─────────────────────────────────────────────────────────────────
let ws = null
let _evKey = 0
let _destroyed = false
let _reconnectTimer = null
const wsState = ref('disconnected')

const wsDot = computed(() => ({
  'bg-success animate-pulse': wsState.value === 'open',
  'bg-warning animate-pulse': wsState.value === 'connecting',
  'bg-base-300':              wsState.value !== 'open' && wsState.value !== 'connecting',
}))
const wsLabel = computed(() => ({
  open: 'LIVE', connecting: 'Connecting', closed: 'Reconnecting', disconnected: 'Offline',
})[wsState.value] || 'Offline')
const wsBadge = computed(() => ({
  'border-success/30 text-success bg-success/5': wsState.value === 'open',
  'border-warning/30 text-warning bg-warning/5': wsState.value === 'connecting',
  'border-base-300 text-base-content/30':        wsState.value !== 'open' && wsState.value !== 'connecting',
}))

// ── Runtime state ─────────────────────────────────────────────────────────────
/**
 * cameras: map of camera_id → runtime camera object
 * camera_name + station_id are enriched from DB (camerasDB)
 */
const cameras = reactive({})       // { camera_id: { ...live, camera_name, _lastPerson, _alert } }
const camerasDB = ref([])          // DB records: { id, name, station_id, camera_type }
const stationsDB = ref([])         // DB records: { id, name }

const events = ref([])
const feedEl = ref(null)
const MAX_EVENTS = 300

const unknownAlertCount = ref(0)
const todayStats = ref({ present: 0, total: 0 })

// ── Station grouping ──────────────────────────────────────────────────────────
const selectedStation = ref('')    // '' = show all

function toggleStation(station_id) {
  selectedStation.value = selectedStation.value === station_id ? '' : station_id
}

const liveCount = computed(() =>
  Object.values(cameras).filter(c => c.status === 'active').length
)

/**
 * stationGroups: list of { station_id, station_name, cameras[], live, total }
 * Built from active cameras (registered via WS) enriched with DB names
 */
const stationGroups = computed(() => {
  // Group all cameras (active + DB registered that are offline) by station
  const map = {}

  // Seed from DB cameras
  for (const dbCam of camerasDB.value) {
    const sid  = String(dbCam.station_id)
    const sname = stationsDB.value.find(s => s.id === sid)?.name || sid.slice(0,8)
    if (!map[sid]) map[sid] = { station_id: sid, station_name: sname, cameras: [], live: 0, total: 0 }
  }

  // Overlay with live camera state
  for (const [cam_id, cam] of Object.entries(cameras)) {
    const dbCam = camerasDB.value.find(c => c.id === cam_id)
    const sid   = dbCam?.station_id ? String(dbCam.station_id) : cam.station_id
    const sname = stationsDB.value.find(s => s.id === sid)?.name || sid?.slice(0,8) || 'Unknown'

    if (!map[sid]) map[sid] = { station_id: sid, station_name: sname, cameras: [], live: 0, total: 0 }

    // Check if already in this station's cameras
    if (!map[sid].cameras.find(c => c.camera_id === cam_id)) {
      map[sid].cameras.push(cam)
    }

    if (cam.status === 'active') map[sid].live++
    map[sid].total = map[sid].cameras.length
  }

  return Object.values(map).filter(g => g.cameras.length > 0)
})

const filteredGroups = computed(() => {
  if (!selectedStation.value) return stationGroups.value
  return stationGroups.value.filter(g => g.station_id === selectedStation.value)
})

// ── WebSocket connect ─────────────────────────────────────────────────────────
function connect() {
  if (_destroyed) return
  const token = localStorage.getItem(TOKEN_KEY)
  if (!token) return

  wsState.value = 'connecting'
  const url = `ws://localhost:8000/api/v1/ws/console?token=${encodeURIComponent(token)}`
  ws = new WebSocket(url)

  ws.onopen = () => {
    wsState.value = 'open'
    clearTimeout(_reconnectTimer)
  }
  ws.onmessage = (e) => {
    try { handleEvent(JSON.parse(e.data)) } catch {}
  }
  ws.onclose = (e) => {
    wsState.value = 'closed'
    if (_destroyed) return
    if (e.code === 4001 || e.code === 4003) {
      wsState.value = 'disconnected'
      toast.error('Console: ' + e.reason)
      return
    }
    _reconnectTimer = setTimeout(connect, 3000)
  }
  ws.onerror = () => ws?.close()
}

function reconnect() {
  ws?.close()
  clearTimeout(_reconnectTimer)
  connect()
}

// ── Event handler ─────────────────────────────────────────────────────────────
function _cameraName(camera_id) {
  return camerasDB.value.find(c => c.id === camera_id)?.name || null
}

function handleEvent(data) {
  const ev = data.event

  // Initial snapshot
  if (ev === 'init') {
    for (const c of (data.cameras || [])) {
      cameras[c.camera_id] = _makeCamera(c)
    }
    return
  }

  if (ev === 'camera_connected') {
    cameras[data.camera_id] = _makeCamera({
      camera_id:   data.camera_id,
      station_id:  data.station_id,
      camera_type: data.camera_type,
      status:      'active',
      fps: 0, frame_count: 0,
    })
  }

  if (ev === 'camera_disconnected' || ev === 'camera_offline') {
    delete cameras[data.camera_id]
  }

  if (ev === 'camera_paused' && cameras[data.camera_id]) {
    cameras[data.camera_id].status = 'paused'
  }
  if (ev === 'camera_resumed' && cameras[data.camera_id]) {
    cameras[data.camera_id].status = 'active'
    cameras[data.camera_id]._alert = false
  }

  // Attendance: update last-person on tile
  if (ev === 'attendance_logged' && cameras[data.camera_id]) {
    todayStats.value.total++
    todayStats.value.present = Math.max(todayStats.value.present,
      new Set([...Object.values(cameras).map(c => c._lastPerson?.employee_id).filter(Boolean), data.employee_id]).size
    )
    cameras[data.camera_id]._lastPerson = {
      full_name:   data.full_name || data.employee_id,
      employee_id: data.employee_id,
      confidence:  data.confidence,
      time: new Date().toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
    }
    cameras[data.camera_id]._alert = false
  }

  // Unknown face: alert
  if (ev === 'unknown_face' && cameras[data.camera_id]) {
    cameras[data.camera_id]._alert = true
    unknownAlertCount.value++
  }

  // Push to event feed
  const entry = {
    ...data,
    _key:  ++_evKey,
    _time: new Date().toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
  }
  events.value.unshift(entry)
  if (events.value.length > MAX_EVENTS) events.value.length = MAX_EVENTS

  nextTick(() => { if (feedEl.value) feedEl.value.scrollTop = 0 })
}

function _makeCamera(c) {
  return reactive({
    camera_id:   c.camera_id,
    station_id:  c.station_id,
    camera_type: c.camera_type || 'WEBCAM',
    status:      c.status || 'active',
    fps:         c.fps || 0,
    frame_count: c.frame_count || 0,
    camera_name: _cameraName(c.camera_id),
    _lastPerson: null,
    _alert:      false,
  })
}

// ── Commands ──────────────────────────────────────────────────────────────────
function sendCmd(action, camera_id, extra = {}) {
  if (ws?.readyState !== WebSocket.OPEN) { toast.error('Console not connected'); return }
  ws.send(JSON.stringify({ action, camera_id, ...extra }))
}

async function confirmDisconnect(cam) {
  const name = cam.camera_name || cam.camera_id
  const ok = await confirm(
    `Disconnect "${name}"?\nThe camera agent will stop streaming.`,
    { title: 'Disconnect Camera', confirmLabel: 'Disconnect', confirmClass: 'btn-error' }
  )
  if (ok) sendCmd('disconnect_camera', cam.camera_id)
}

function clearAlerts() {
  unknownAlertCount.value = 0
  for (const cam of Object.values(cameras)) cam._alert = false
}

function scrollToUnknown() {
  const el = document.querySelector('[data-alert]')
  el?.scrollIntoView({ behavior: 'smooth' })
}

// ── Style helpers ─────────────────────────────────────────────────────────────
function statusDot(status) {
  if (status === 'active')  return 'bg-success animate-pulse'
  if (status === 'paused')  return 'bg-warning'
  return 'bg-base-300'
}
function tileBorder(status) {
  if (status === 'active')  return 'border-success/30 bg-base-100'
  if (status === 'paused')  return 'border-warning/30 bg-base-100'
  return 'border-base-300 bg-base-100'
}
function typeBadge(type) {
  if (type === 'WEBCAM')    return 'badge-info badge-outline'
  if (type === 'IP_CAMERA') return 'badge-primary badge-outline'
  if (type === 'CCTV')      return 'badge-secondary badge-outline'
  return 'badge-accent badge-outline'
}
function eventLabel(ev) {
  const m = { attendance_logged: '✅ Present', attendance_cooldown: '⏱ Cooldown',
               unknown_face: '⚠ Unknown', camera_connected: '📷 Connected',
               camera_disconnected: '🔴 Offline', camera_paused: '⏸ Paused',
               camera_resumed: '▶ Resumed', camera_offline: '🔴 Offline' }
  return m[ev.event] || ev.event
}
function eventStyle(ev) {
  const e = ev.event
  if (e === 'attendance_logged')   return 'bg-success/8 border-success/20'
  if (e === 'attendance_cooldown') return 'bg-base-200 border-base-300 opacity-60'
  if (e === 'unknown_face')        return 'bg-error/10 border-error/30 font-medium'
  if (e === 'camera_connected')    return 'bg-info/8 border-info/20'
  return 'bg-base-200 border-base-300 opacity-50'
}

// ── Load DB data ──────────────────────────────────────────────────────────────
async function loadDB() {
  try {
    const [camRes, stationRes, summaryRes] = await Promise.all([
      api.get('/api/v1/cameras'),
      api.get('/api/v1/stations'),
      api.get('/api/v1/attendance/summary'),
    ])
    camerasDB.value   = camRes.data
    stationsDB.value  = stationRes.data
    todayStats.value  = {
      total:   summaryRes.data.total_records,
      present: summaryRes.data.unique_employees,
    }
    // Backfill camera_name on existing runtime cameras
    for (const cam of Object.values(cameras)) {
      if (!cam.camera_name) cam.camera_name = _cameraName(cam.camera_id)
    }
  } catch {
    // DB load failure is non-fatal — console still works
  }
}

// ── Lifecycle ─────────────────────────────────────────────────────────────────
onMounted(() => {
  loadDB()
  connect()
})
onUnmounted(() => {
  _destroyed = true
  clearTimeout(_reconnectTimer)
  ws?.close()
})
</script>

<style scoped>
.feed-slide-enter-active { transition: all 0.2s ease; }
.feed-slide-enter-from   { opacity: 0; transform: translateY(-6px); }
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
