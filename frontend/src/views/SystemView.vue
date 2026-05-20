<template>
  <div class="flex flex-col gap-5">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-bold tracking-wide">System Info</h1>
        <p class="text-sm text-base-content/40 mt-0.5">Live status of all services</p>
      </div>
      <button class="btn btn-sm btn-ghost gap-2" :class="loading && 'loading'" @click="load">
        <svg v-if="!loading" xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
        </svg>
        Refresh
      </button>
    </div>

    <div v-if="error" class="alert alert-error">{{ error }}</div>

    <div v-if="info" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">

      <!-- App -->
      <div class="card bg-base-100 shadow-sm border border-base-300">
        <div class="card-body p-4 gap-3">
          <div class="flex items-center gap-2">
            <span class="text-lg">🖥️</span>
            <h2 class="font-bold">Application</h2>
            <div class="badge badge-success badge-sm ml-auto">running</div>
          </div>
          <div class="flex flex-col gap-1.5 text-sm">
            <Row label="Version"         :value="info.app.version" />
            <Row label="Uptime"          :value="formatUptime(info.app.uptime_seconds)" />
            <Row label="ONNX Provider"   :value="info.app.onnx_provider" :highlight="onnxColor(info.app.onnx_provider)" />
            <Row label="Detect Size"     :value="`${info.app.face_detect_size}×${info.app.face_detect_size} px`" />
            <Row label="Infer Workers"   :value="String(info.app.inference_workers)" />
          </div>
        </div>
      </div>

      <!-- Face Engine -->
      <div class="card bg-base-100 shadow-sm border border-base-300">
        <div class="card-body p-4 gap-3">
          <div class="flex items-center gap-2">
            <span class="text-lg">🧠</span>
            <h2 class="font-bold">Face Engine</h2>
            <StatusBadge :ok="info.face_engine.loaded" />
          </div>
          <div class="flex flex-col gap-1.5 text-sm">
            <Row label="Model"     :value="info.face_engine.model" />
            <Row label="Det Size"  :value="`${info.face_engine.det_size}×${info.face_engine.det_size} px`" />
            <Row label="Status"    :value="info.face_engine.status" />
          </div>
        </div>
      </div>

      <!-- Anti-Spoof -->
      <div class="card bg-base-100 shadow-sm border border-base-300">
        <div class="card-body p-4 gap-3">
          <div class="flex items-center gap-2">
            <span class="text-lg">🛡️</span>
            <h2 class="font-bold">Anti-Spoof</h2>
            <StatusBadge :ok="info.anti_spoof.available" ok-label="available" fail-label="unavailable" />
          </div>
          <div class="flex flex-col gap-1.5 text-sm">
            <Row label="Model"     :value="info.anti_spoof.model" />
            <Row label="Available" :value="info.anti_spoof.available ? 'Yes' : 'No'" />
          </div>
          <div class="text-xs text-warning/70 bg-warning/5 rounded-lg px-2.5 py-1.5 leading-snug">
            ⚠️ {{ info.anti_spoof.note }}
          </div>
        </div>
      </div>

      <!-- PostgreSQL -->
      <div class="card bg-base-100 shadow-sm border border-base-300">
        <div class="card-body p-4 gap-3">
          <div class="flex items-center gap-2">
            <span class="text-lg">🐘</span>
            <h2 class="font-bold">PostgreSQL</h2>
            <StatusBadge :ok="info.postgres.status === 'ok'" />
          </div>
          <template v-if="info.postgres.status === 'ok'">
            <div class="flex flex-col gap-1.5 text-sm">
              <Row label="Version"   :value="info.postgres.version" />
              <Row label="DB Size"   :value="`${info.postgres.size_mb} MB`" />
              <Row label="Host"      :value="info.postgres.url" mono />
            </div>
            <div class="divider my-0 text-xs opacity-30">Row Counts</div>
            <div class="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
              <Stat label="Employees"    :value="info.postgres.rows.employees" />
              <Stat label="Active"       :value="info.postgres.rows.employees_active" />
              <Stat label="Enrolled"     :value="info.postgres.rows.employees_enrolled" />
              <Stat label="Templates"    :value="info.postgres.rows.face_templates" />
              <Stat label="Attendance"   :value="info.postgres.rows.attendance_logs" />
              <Stat label="Departments"  :value="info.postgres.rows.departments" />
              <Stat label="Stations"     :value="info.postgres.rows.stations" />
              <Stat label="Users"        :value="info.postgres.rows.users" />
            </div>
          </template>
          <div v-else class="text-error text-xs">{{ info.postgres.error }}</div>
        </div>
      </div>

      <!-- Qdrant -->
      <div class="card bg-base-100 shadow-sm border border-base-300">
        <div class="card-body p-4 gap-3">
          <div class="flex items-center gap-2">
            <span class="text-lg">🔍</span>
            <h2 class="font-bold">Qdrant</h2>
            <StatusBadge :ok="info.qdrant.status === 'ok'" />
          </div>
          <template v-if="info.qdrant.status === 'ok'">
            <div class="flex flex-col gap-1.5 text-sm">
              <Row label="Host"         :value="info.qdrant.host" mono />
              <Row label="Collection"   :value="info.qdrant.collection" />
              <Row label="Vectors"      :value="info.qdrant.vectors_count.toLocaleString()" />
              <Row label="Points"       :value="info.qdrant.points_count.toLocaleString()" />
              <Row label="Vector Size"  :value="`${info.qdrant.vector_size}D`" />
              <Row label="Distance"     :value="info.qdrant.distance" />
              <Row label="Quantization" :value="info.qdrant.quantization" />
            </div>
          </template>
          <div v-else class="text-error text-xs">{{ info.qdrant.error }}</div>
        </div>
      </div>

      <!-- Redis -->
      <div class="card bg-base-100 shadow-sm border border-base-300">
        <div class="card-body p-4 gap-3">
          <div class="flex items-center gap-2">
            <span class="text-lg">⚡</span>
            <h2 class="font-bold">Redis</h2>
            <StatusBadge :ok="info.redis.status === 'ok'" />
          </div>
          <template v-if="info.redis.status === 'ok'">
            <div class="flex flex-col gap-1.5 text-sm">
              <Row label="URL"             :value="info.redis.url" mono />
              <Row label="Version"         :value="info.redis.version" />
              <Row label="Memory Used"     :value="`${info.redis.used_memory_mb} MB`" />
              <Row label="Memory Peak"     :value="`${info.redis.peak_memory_mb} MB`" />
              <Row label="Clients"         :value="String(info.redis.connected_clients)" />
              <Row label="Uptime"          :value="formatUptime(info.redis.uptime_seconds)" />
              <Row v-if="info.redis.keyspace" label="Keys" :value="String(info.redis.keyspace?.keys ?? '—')" />
            </div>
          </template>
          <div v-else class="text-error text-xs">{{ info.redis.error }}</div>
        </div>
      </div>

      <!-- Storage -->
      <div class="card bg-base-100 shadow-sm border border-base-300 md:col-span-2 xl:col-span-3">
        <div class="card-body p-4 gap-3">
          <div class="flex items-center gap-2">
            <span class="text-lg">💾</span>
            <h2 class="font-bold">Storage</h2>
            <StatusBadge :ok="info.storage.status === 'ok'" />
          </div>
          <template v-if="info.storage.status === 'ok'">
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <div class="text-base-content/40 text-xs mb-0.5">Path</div>
                <div class="font-mono text-xs break-all">{{ info.storage.path }}</div>
              </div>
              <div>
                <div class="text-base-content/40 text-xs mb-0.5">Snapshots</div>
                <div class="font-bold text-lg">{{ info.storage.snapshots_count.toLocaleString() }}</div>
                <div class="text-xs text-base-content/40">{{ info.storage.snapshots_mb }} MB</div>
              </div>
              <div>
                <div class="text-base-content/40 text-xs mb-0.5">Disk Free</div>
                <div class="font-bold text-lg">{{ info.storage.disk_free_gb }} GB</div>
              </div>
              <div>
                <div class="text-base-content/40 text-xs mb-0.5">Disk Total</div>
                <div class="font-bold text-lg">{{ info.storage.disk_total_gb }} GB</div>
              </div>
            </div>
          </template>
          <div v-else class="text-error text-xs">{{ info.storage.error }}</div>
        </div>
      </div>

    </div>

    <!-- Loading skeleton -->
    <div v-else-if="loading" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      <div v-for="i in 6" :key="i" class="card bg-base-100 shadow-sm border border-base-300">
        <div class="card-body p-4 gap-3">
          <div class="skeleton h-5 w-32 rounded"></div>
          <div class="skeleton h-3 w-full rounded"></div>
          <div class="skeleton h-3 w-4/5 rounded"></div>
          <div class="skeleton h-3 w-3/5 rounded"></div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api/client'

const info    = ref(null)
const loading = ref(false)
const error   = ref('')

async function load() {
  loading.value = true
  error.value   = ''
  try {
    const { data } = await api.get('/api/v1/system/info')
    info.value = data
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || 'Failed to load system info'
  } finally {
    loading.value = false
  }
}

onMounted(load)

function formatUptime(seconds) {
  if (!seconds) return '—'
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  if (d > 0) return `${d}d ${h}h ${m}m`
  if (h > 0) return `${h}h ${m}m ${s}s`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

function onnxColor(provider) {
  if (provider?.includes('CUDA'))      return 'text-success font-semibold'
  if (provider?.includes('DirectML'))  return 'text-info font-semibold'
  if (provider?.includes('ROCm'))      return 'text-info font-semibold'
  return 'text-base-content/60'
}
</script>

<!-- ── Sub-components (inline) ─────────────────────────────────────────────── -->
<script>
// Row: label + value pair
export const Row = {
  props: ['label', 'value', 'mono', 'highlight'],
  template: `
    <div class="flex items-baseline justify-between gap-2">
      <span class="text-base-content/40 shrink-0">{{ label }}</span>
      <span class="truncate text-right" :class="[mono ? 'font-mono text-xs' : '', highlight || '']">{{ value }}</span>
    </div>
  `,
}

// Stat: compact number + label
export const Stat = {
  props: ['label', 'value'],
  template: `
    <div class="flex items-baseline justify-between">
      <span class="text-base-content/40">{{ label }}</span>
      <span class="font-mono font-semibold">{{ Number(value).toLocaleString() }}</span>
    </div>
  `,
}

// StatusBadge
export const StatusBadge = {
  props: { ok: Boolean, okLabel: { default: 'ok' }, failLabel: { default: 'error' } },
  template: `
    <div class="badge badge-sm ml-auto" :class="ok ? 'badge-success' : 'badge-error'">
      {{ ok ? okLabel : failLabel }}
    </div>
  `,
}
</script>
