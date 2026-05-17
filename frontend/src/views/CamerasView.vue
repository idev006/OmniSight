<template>
  <div class="flex flex-col gap-5">

    <!-- Header -->
    <div class="flex items-start justify-between gap-3">
      <div>
        <h1 class="text-xl font-bold tracking-wide">Cameras</h1>
        <p class="text-sm text-base-content/40 mt-0.5">Registered cameras and live connection status</p>
      </div>
      <div class="flex gap-2">
        <button class="btn btn-ghost btn-sm" @click="load" :class="{ loading: loading }">
          <svg v-if="!loading" xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
        <button class="btn btn-primary btn-sm gap-2" @click="openCreate">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          Add Camera
        </button>
      </div>
    </div>

    <!-- Stats -->
    <div class="stats bg-base-100 border border-base-300 shadow-sm w-full">
      <div class="stat">
        <div class="stat-title text-xs">Total</div>
        <div class="stat-value text-2xl">{{ cameras.length }}</div>
      </div>
      <div class="stat">
        <div class="stat-title text-xs">Live</div>
        <div class="stat-value text-2xl text-success">{{ liveCount }}</div>
        <div class="stat-desc text-success">streaming now</div>
      </div>
      <div class="stat">
        <div class="stat-title text-xs">Paused</div>
        <div class="stat-value text-2xl text-warning">{{ pausedCount }}</div>
      </div>
      <div class="stat">
        <div class="stat-title text-xs">Offline</div>
        <div class="stat-value text-2xl text-base-content/25">{{ offlineCount }}</div>
      </div>
    </div>

    <!-- Filters -->
    <div class="flex gap-2 flex-wrap">
      <select v-model="filterStation" class="select select-bordered select-sm">
        <option value="">All Stations</option>
        <option v-for="s in stations" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>
      <select v-model="filterType" class="select select-bordered select-sm">
        <option value="">All Types</option>
        <option value="WEBCAM">Webcam</option>
        <option value="IP_CAMERA">IP Camera</option>
        <option value="CCTV">CCTV</option>
        <option value="SMARTPHONE">Smartphone</option>
      </select>
      <select v-model="filterStatus" class="select select-bordered select-sm">
        <option value="">All Status</option>
        <option value="active">Active</option>
        <option value="paused">Paused</option>
        <option value="offline">Offline</option>
      </select>
    </div>

    <!-- Camera grid -->
    <div v-if="loading && cameras.length === 0" class="flex justify-center py-12">
      <span class="loading loading-spinner loading-lg text-primary"></span>
    </div>

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
      <div
        v-for="cam in filtered"
        :key="cam.id"
        class="card bg-base-100 border transition-all duration-200 hover:shadow-md"
        :class="cardBorder(cam.live_status)"
      >
        <div class="card-body p-4 gap-3">

          <!-- Header row -->
          <div class="flex items-start gap-2">
            <!-- Status dot -->
            <div class="mt-1.5 shrink-0">
              <div class="w-2 h-2 rounded-full" :class="statusDot(cam.live_status)"></div>
            </div>
            <div class="flex-1 min-w-0">
              <div class="font-semibold text-sm leading-tight truncate">{{ cam.name }}</div>
              <div class="text-xs text-base-content/30 font-mono mt-0.5">{{ cam.id.slice(0,8) }}…</div>
            </div>
            <span class="badge badge-xs shrink-0" :class="typeBadge(cam.camera_type)">{{ cam.camera_type }}</span>
          </div>

          <!-- Station -->
          <div class="flex items-center gap-1.5 text-xs text-base-content/40">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
            </svg>
            {{ stationName(cam.station_id) }}
          </div>

          <!-- Live FPS badge -->
          <div v-if="cam.live_status === 'active'" class="flex items-center gap-2">
            <div class="badge badge-success badge-sm gap-1">
              <div class="w-1.5 h-1.5 rounded-full bg-success-content/60 animate-pulse"></div>
              {{ (cam.live_fps || 0).toFixed(1) }} fps
            </div>
          </div>
          <div v-else-if="cam.live_status === 'paused'" class="badge badge-warning badge-sm">Paused</div>
          <div v-else class="badge badge-ghost badge-sm">Offline</div>

          <!-- RTSP -->
          <div v-if="cam.rtsp_url" class="truncate text-xs text-base-content/25 font-mono">{{ cam.rtsp_url }}</div>

          <!-- Description -->
          <div v-if="cam.description" class="text-xs text-base-content/40 line-clamp-1">{{ cam.description }}</div>

          <!-- Actions -->
          <div class="flex gap-1.5 mt-1 pt-3 border-t border-base-300/50">
            <button v-if="cam.live_status === 'active'" class="btn btn-xs btn-warning flex-1" @click="pauseCamera(cam)">Pause</button>
            <button v-else-if="cam.live_status === 'paused'" class="btn btn-xs btn-success flex-1" @click="resumeCamera(cam)">Resume</button>
            <div v-else class="flex-1"></div>
            <button class="btn btn-xs btn-ghost" @click="openEdit(cam)">Edit</button>
            <button class="btn btn-xs btn-ghost text-error hover:bg-error/10" @click="deleteCamera(cam)">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>

        </div>
      </div>

      <!-- Empty state -->
      <div v-if="!loading && filtered.length === 0" class="col-span-full">
        <div class="flex flex-col items-center justify-center py-16 text-base-content/25">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-14 w-14 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M3 7a1 1 0 011-1h3l2-2h6l2 2h3a1 1 0 011 1v11a1 1 0 01-1 1H4a1 1 0 01-1-1V7z" />
            <circle cx="12" cy="13" r="3" stroke="currentColor" stroke-width="1" fill="none" />
          </svg>
          <p class="text-sm">No cameras match your filters</p>
        </div>
      </div>
    </div>

    <!-- ── Create Modal ───────────────────────────────────────────── -->
    <dialog ref="createModal" class="modal modal-bottom sm:modal-middle">
      <div class="modal-box max-w-md">
        <div class="flex items-center justify-between mb-5">
          <h3 class="font-bold text-lg">Add Camera</h3>
          <button class="btn btn-ghost btn-sm btn-circle" @click="createModal.close()">✕</button>
        </div>
        <form @submit.prevent="createCamera" class="flex flex-col gap-3">
          <label class="form-control">
            <div class="label py-1"><span class="label-text text-xs font-medium uppercase tracking-wider opacity-60">Station *</span></div>
            <select v-model="form.station_id" class="select select-bordered" required>
              <option value="" disabled>Select a station…</option>
              <option v-for="s in stations" :key="s.id" :value="s.id">{{ s.name }}</option>
            </select>
          </label>
          <label class="form-control">
            <div class="label py-1"><span class="label-text text-xs font-medium uppercase tracking-wider opacity-60">Name *</span></div>
            <input v-model="form.name" class="input input-bordered" required placeholder="e.g. Main Entrance Cam" />
          </label>
          <label class="form-control">
            <div class="label py-1"><span class="label-text text-xs font-medium uppercase tracking-wider opacity-60">Type *</span></div>
            <select v-model="form.camera_type" class="select select-bordered" required>
              <option value="WEBCAM">Webcam (USB)</option>
              <option value="IP_CAMERA">IP Camera (RTSP)</option>
              <option value="CCTV">CCTV (NVR/DVR)</option>
              <option value="SMARTPHONE">Smartphone (Web)</option>
            </select>
          </label>
          <label class="form-control" v-if="form.camera_type === 'IP_CAMERA' || form.camera_type === 'CCTV'">
            <div class="label py-1"><span class="label-text text-xs font-medium uppercase tracking-wider opacity-60">RTSP URL</span></div>
            <input v-model="form.rtsp_url" class="input input-bordered font-mono text-sm" placeholder="rtsp://user:pass@192.168.1.x/stream" />
          </label>
          <label class="form-control">
            <div class="label py-1"><span class="label-text text-xs font-medium uppercase tracking-wider opacity-60">Description</span></div>
            <input v-model="form.description" class="input input-bordered" placeholder="Optional notes" />
          </label>
          <div class="modal-action mt-2">
            <button type="button" class="btn btn-ghost" @click="createModal.close()">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              <span v-if="saving" class="loading loading-spinner loading-sm"></span>
              Add Camera
            </button>
          </div>
        </form>
      </div>
      <form method="dialog" class="modal-backdrop"><button>close</button></form>
    </dialog>

    <!-- ── Edit Modal ─────────────────────────────────────────────── -->
    <dialog ref="editModal" class="modal modal-bottom sm:modal-middle">
      <div class="modal-box max-w-md">
        <div class="flex items-center justify-between mb-5">
          <div>
            <h3 class="font-bold text-lg">Edit Camera</h3>
            <p class="text-xs text-base-content/40 mt-0.5">{{ editTarget?.name }}</p>
          </div>
          <button class="btn btn-ghost btn-sm btn-circle" @click="editModal.close()">✕</button>
        </div>
        <form @submit.prevent="saveEdit" class="flex flex-col gap-3">
          <label class="form-control">
            <div class="label py-1"><span class="label-text text-xs font-medium uppercase tracking-wider opacity-60">Name</span></div>
            <input v-model="editForm.name" class="input input-bordered" />
          </label>
          <label class="form-control">
            <div class="label py-1"><span class="label-text text-xs font-medium uppercase tracking-wider opacity-60">Type</span></div>
            <select v-model="editForm.camera_type" class="select select-bordered">
              <option value="WEBCAM">Webcam</option>
              <option value="IP_CAMERA">IP Camera</option>
              <option value="CCTV">CCTV</option>
              <option value="SMARTPHONE">Smartphone</option>
            </select>
          </label>
          <label class="form-control">
            <div class="label py-1"><span class="label-text text-xs font-medium uppercase tracking-wider opacity-60">RTSP URL</span></div>
            <input v-model="editForm.rtsp_url" class="input input-bordered font-mono text-sm" placeholder="rtsp://…" />
          </label>
          <label class="form-control">
            <div class="label py-1"><span class="label-text text-xs font-medium uppercase tracking-wider opacity-60">Description</span></div>
            <input v-model="editForm.description" class="input input-bordered" />
          </label>
          <div class="flex items-center gap-3 px-1 py-2">
            <input type="checkbox" v-model="editForm.is_active" class="toggle toggle-success" />
            <span class="text-sm font-medium">Camera enabled</span>
          </div>
          <div class="modal-action mt-2">
            <button type="button" class="btn btn-ghost" @click="editModal.close()">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              <span v-if="saving" class="loading loading-spinner loading-sm"></span>
              Save Changes
            </button>
          </div>
        </form>
      </div>
      <form method="dialog" class="modal-backdrop"><button>close</button></form>
    </dialog>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api/client'
import { useToast } from '@/composables/useToast'

const toast = useToast()

const cameras      = ref([])
const stations     = ref([])
const loading      = ref(false)
const saving       = ref(false)
const filterStation = ref('')
const filterType    = ref('')
const filterStatus  = ref('')

const createModal = ref(null)
const editModal   = ref(null)
const editTarget  = ref(null)

const form = ref({ station_id: '', name: '', camera_type: 'WEBCAM', rtsp_url: '', description: '' })
const editForm = ref({ name: '', camera_type: '', rtsp_url: '', is_active: true, description: '' })

const filtered = computed(() => cameras.value.filter(c => {
  if (filterStation.value && c.station_id !== filterStation.value) return false
  if (filterType.value && c.camera_type !== filterType.value) return false
  if (filterStatus.value && c.live_status !== filterStatus.value) return false
  return true
}))

const liveCount    = computed(() => cameras.value.filter(c => c.live_status === 'active').length)
const pausedCount  = computed(() => cameras.value.filter(c => c.live_status === 'paused').length)
const offlineCount = computed(() => cameras.value.filter(c => c.live_status === 'offline').length)

function stationName(id) {
  return stations.value.find(s => s.id === id)?.name || '—'
}

function statusDot(status) {
  if (status === 'active')  return 'bg-success animate-pulse'
  if (status === 'paused')  return 'bg-warning'
  return 'bg-base-300'
}

function cardBorder(status) {
  if (status === 'active')  return 'border-success/25'
  if (status === 'paused')  return 'border-warning/25'
  return 'border-base-300'
}

function typeBadge(type) {
  if (type === 'WEBCAM')     return 'badge-info badge-outline'
  if (type === 'IP_CAMERA')  return 'badge-primary badge-outline'
  if (type === 'CCTV')       return 'badge-secondary badge-outline'
  return 'badge-accent badge-outline'
}

function openCreate() {
  form.value = { station_id: stations.value[0]?.id || '', name: '', camera_type: 'WEBCAM', rtsp_url: '', description: '' }
  createModal.value.showModal()
}

async function createCamera() {
  saving.value = true
  const payload = { ...form.value }
  if (!payload.rtsp_url) delete payload.rtsp_url
  if (!payload.description) delete payload.description
  try {
    await api.post('/api/v1/cameras', payload)
    createModal.value.close()
    toast.success(`Camera "${form.value.name}" added`)
    await load()
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Failed to add camera')
  } finally {
    saving.value = false
  }
}

function openEdit(cam) {
  editTarget.value = cam
  editForm.value = {
    name: cam.name,
    camera_type: cam.camera_type,
    rtsp_url: cam.rtsp_url || '',
    is_active: cam.is_active,
    description: cam.description || '',
  }
  editModal.value.showModal()
}

async function saveEdit() {
  saving.value = true
  const payload = { ...editForm.value }
  if (!payload.rtsp_url)    payload.rtsp_url = null
  if (!payload.description) payload.description = null
  try {
    await api.put(`/api/v1/cameras/${editTarget.value.id}`, payload)
    editModal.value.close()
    toast.success('Camera updated')
    await load()
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Failed to update camera')
  } finally {
    saving.value = false
  }
}

async function pauseCamera(cam) {
  try {
    await api.post(`/api/v1/cameras/${cam.id}/pause`)
    toast.warning(`${cam.name} paused`)
    await load()
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Cannot pause')
  }
}

async function resumeCamera(cam) {
  try {
    await api.post(`/api/v1/cameras/${cam.id}/resume`)
    toast.success(`${cam.name} resumed`)
    await load()
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Cannot resume')
  }
}

async function deleteCamera(cam) {
  if (!confirm(`Delete camera "${cam.name}"?`)) return
  try {
    await api.delete(`/api/v1/cameras/${cam.id}`)
    toast.success(`Camera "${cam.name}" deleted`)
    await load()
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Failed to delete')
  }
}

async function load() {
  loading.value = true
  try {
    const [cRes, sRes] = await Promise.all([
      api.get('/api/v1/cameras'),
      api.get('/api/v1/stations'),
    ])
    cameras.value  = cRes.data
    stations.value = sRes.data
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
