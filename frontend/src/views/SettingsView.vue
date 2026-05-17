<template>
  <div class="flex flex-col gap-5">

    <!-- Header -->
    <div class="flex items-start justify-between gap-3">
      <div>
        <h1 class="text-xl font-bold tracking-wide">System Settings</h1>
        <p class="text-sm text-base-content/40 mt-0.5">Live configuration — most changes take effect instantly</p>
      </div>
      <button class="btn btn-ghost btn-sm" @click="load">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        Refresh
      </button>
    </div>

    <!-- Liveness legend -->
    <div class="flex flex-wrap gap-2">
      <div class="badge badge-success gap-1.5 py-3 px-3 rounded-xl border-0">
        <span>⚡</span> <span class="text-xs font-medium">live</span>
        <span class="text-success-content/60 text-xs font-normal">— instant</span>
      </div>
      <div class="badge badge-warning gap-1.5 py-3 px-3 rounded-xl border-0">
        <span>⚠️</span> <span class="text-xs font-medium">graceful</span>
        <span class="text-warning-content/60 text-xs font-normal">— on next reconnect</span>
      </div>
      <div class="badge badge-error gap-1.5 py-3 px-3 rounded-xl border-0">
        <span>🔄</span> <span class="text-xs font-medium">restart</span>
        <span class="text-error-content/60 text-xs font-normal">— requires restart</span>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex justify-center py-12">
      <span class="loading loading-spinner loading-lg text-primary"></span>
    </div>

    <!-- Settings grid -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-3">
      <div
        v-for="s in settings"
        :key="s.key"
        class="bg-base-100 rounded-2xl border p-4 flex flex-col gap-3 transition-colors"
        :class="isDirty(s) ? 'border-primary/30 bg-primary/2' : 'border-base-300'"
      >
        <!-- Key + badges -->
        <div class="flex items-start justify-between gap-2">
          <div class="flex flex-col gap-1 min-w-0">
            <span class="font-mono font-semibold text-sm tracking-tight">{{ s.key }}</span>
            <p class="text-xs text-base-content/40 leading-relaxed">{{ s.description }}</p>
          </div>
          <div class="flex flex-col gap-1 items-end shrink-0">
            <span class="badge badge-xs" :class="livenessBadge(s.liveness)">
              {{ livenessIcon(s.liveness) }} {{ s.liveness }}
            </span>
            <span class="badge badge-ghost badge-xs">{{ s.value_type }}</span>
          </div>
        </div>

        <!-- Input row -->
        <div class="flex items-center gap-2">
          <input
            :value="edits[s.key] ?? s.value"
            @input="edits[s.key] = $event.target.value"
            class="input input-bordered input-sm flex-1 font-mono"
            :class="isDirty(s) ? 'input-primary' : ''"
            :type="s.value_type !== 'string' ? 'number' : 'text'"
            :step="s.value_type === 'float' ? '0.01' : '1'"
          />
          <button
            class="btn btn-sm min-w-[4.5rem]"
            :class="isDirty(s) ? 'btn-primary' : 'btn-ghost'"
            :disabled="!isDirty(s) || !!saving[s.key]"
            @click="saveSetting(s)"
          >
            <span v-if="saving[s.key]" class="loading loading-spinner loading-xs"></span>
            <span v-else-if="saved[s.key]" class="text-success font-bold">✓ Saved</span>
            <span v-else>Save</span>
          </button>
        </div>

        <!-- Diff hint -->
        <div v-if="isDirty(s)" class="flex items-center gap-1.5 text-xs text-primary/70 -mt-1">
          <span class="font-mono opacity-60">{{ s.value }}</span>
          <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3" />
          </svg>
          <span class="font-mono font-semibold">{{ edits[s.key] }}</span>
        </div>
      </div>
    </div>

    <!-- Danger zone -->
    <div class="bg-base-100 rounded-2xl border border-error/20 p-4 mt-2">
      <div class="flex items-center gap-2 mb-1">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-error" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <span class="font-semibold text-error text-sm">Danger Zone</span>
      </div>
      <p class="text-xs text-base-content/40 mb-3">Reset all settings to factory defaults. This action is irreversible.</p>
      <button class="btn btn-sm btn-error btn-outline" @click="confirmReset">
        Reset all to defaults
      </button>
    </div>

  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import api from '@/api/client'
import { useToast } from '@/composables/useToast'

const toast = useToast()

const settings = ref([])
const loading  = ref(false)
const edits    = reactive({})
const saving   = reactive({})
const saved    = reactive({})

const DEFAULTS = {
  match_threshold:    '0.72',
  cooldown_seconds:   '300',
  max_fps_per_camera: '2',
  min_face_quality:   '0.6',
  unknown_face_alert: '5',
  inference_workers:  '2',
  face_detect_size:   '640',
}

function isDirty(s) {
  const e = edits[s.key]
  return e !== undefined && e !== s.value
}

function livenessBadge(l) {
  if (l === 'live')     return 'badge-success'
  if (l === 'graceful') return 'badge-warning'
  return 'badge-error'
}

function livenessIcon(l) {
  if (l === 'live')     return '⚡'
  if (l === 'graceful') return '⚠️'
  return '🔄'
}

async function saveSetting(s) {
  const val = edits[s.key]
  if (val === undefined || val === s.value) return
  saving[s.key] = true
  try {
    const res = await api.put(`/api/v1/settings/${s.key}`, { value: val })
    s.value = res.data.value
    delete edits[s.key]
    saved[s.key] = true
    toast.success(`${s.key} updated to ${res.data.value}`)
    setTimeout(() => { delete saved[s.key] }, 2500)
  } catch (e) {
    toast.error(e.response?.data?.detail || `Failed to save ${s.key}`)
  } finally {
    saving[s.key] = false
  }
}

async function confirmReset() {
  if (!confirm('Reset all settings to factory defaults?')) return
  let count = 0
  for (const s of settings.value) {
    const def = DEFAULTS[s.key]
    if (def && def !== s.value) {
      edits[s.key] = def
      await saveSetting(s)
      count++
    }
  }
  toast.info(count > 0 ? `Reset ${count} setting(s) to defaults` : 'All settings already at defaults')
}

async function load() {
  loading.value = true
  try {
    const res = await api.get('/api/v1/settings')
    settings.value = res.data
    Object.keys(edits).forEach(k => delete edits[k])
  } catch (e) {
    toast.error('Failed to load settings')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
