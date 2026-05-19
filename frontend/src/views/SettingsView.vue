<template>
  <div class="flex flex-col gap-6">

    <!-- Header -->
    <div class="flex items-start justify-between gap-3">
      <div>
        <h1 class="text-xl font-bold tracking-wide">System Settings</h1>
        <p class="text-sm text-base-content/40 mt-0.5">Live configuration — most changes take effect instantly</p>
      </div>
      <button class="btn btn-ghost btn-sm gap-1.5" @click="load" :disabled="loading">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" :class="loading ? 'animate-spin' : ''" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        Refresh
      </button>
    </div>

    <!-- Liveness legend -->
    <div class="flex flex-wrap gap-2">
      <div class="badge gap-1.5 py-3 px-3 rounded-xl border-0 badge-success">
        <span>⚡</span><span class="text-xs font-semibold">live</span>
        <span class="opacity-60 text-xs">instant effect</span>
      </div>
      <div class="badge gap-1.5 py-3 px-3 rounded-xl border-0 badge-warning">
        <span>⚠️</span><span class="text-xs font-semibold">graceful</span>
        <span class="opacity-60 text-xs">on next reconnect / login</span>
      </div>
      <div class="badge gap-1.5 py-3 px-3 rounded-xl border-0 badge-error">
        <span>🔄</span><span class="text-xs font-semibold">restart</span>
        <span class="opacity-60 text-xs">requires backend restart</span>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex justify-center py-12">
      <span class="loading loading-spinner loading-lg text-primary"></span>
    </div>

    <template v-else>
      <!-- Setting groups -->
      <div v-for="group in groups" :key="group.id" class="flex flex-col gap-3">

        <!-- Group header -->
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-xl flex items-center justify-center text-base shrink-0" :class="group.iconBg">
            {{ group.icon }}
          </div>
          <div>
            <h2 class="font-semibold text-sm">{{ group.label }}</h2>
            <p class="text-xs text-base-content/40">{{ group.desc }}</p>
          </div>
        </div>

        <!-- Cards grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3 pl-0">
          <template v-for="key in group.keys" :key="key">
            <div
              v-if="byKey[key]"
              class="bg-base-100 rounded-2xl border p-4 flex flex-col gap-3 transition-colors"
              :class="isDirty(byKey[key]) ? 'border-primary/40 bg-primary/5' : 'border-base-300'"
            >
              <!-- Key + badges -->
              <div class="flex items-start justify-between gap-2">
                <div class="flex flex-col gap-0.5 min-w-0">
                  <span class="font-semibold text-sm">{{ META[key]?.label || key }}</span>
                  <p class="text-xs text-base-content/40 leading-relaxed">{{ byKey[key].description }}</p>
                </div>
                <div class="flex flex-col gap-1 items-end shrink-0">
                  <span class="badge badge-xs" :class="livenessBadge(byKey[key].liveness)">
                    {{ livenessIcon(byKey[key].liveness) }} {{ byKey[key].liveness }}
                  </span>
                  <span class="badge badge-ghost badge-xs font-mono">{{ byKey[key].value_type }}</span>
                </div>
              </div>

              <!-- Input + range hint -->
              <div class="flex items-center gap-2">
                <div class="flex-1 flex flex-col gap-0.5">
                  <input
                    :value="edits[key] ?? byKey[key].value"
                    @input="edits[key] = $event.target.value"
                    class="input input-bordered input-sm font-mono w-full"
                    :class="isDirty(byKey[key]) ? 'input-primary' : ''"
                    :type="byKey[key].value_type !== 'string' ? 'number' : 'text'"
                    :step="byKey[key].value_type === 'float' ? '0.01' : '1'"
                    :min="META[key]?.min"
                    :max="META[key]?.max"
                  />
                  <span v-if="META[key]?.hint" class="text-xs text-base-content/30 pl-1">{{ META[key].hint }}</span>
                </div>
                <button
                  class="btn btn-sm min-w-[4.5rem]"
                  :class="isDirty(byKey[key]) ? 'btn-primary' : 'btn-ghost'"
                  :disabled="!isDirty(byKey[key]) || !!saving[key]"
                  @click="saveSetting(byKey[key])"
                >
                  <span v-if="saving[key]" class="loading loading-spinner loading-xs"></span>
                  <span v-else-if="saved[key]" class="text-success">✓ Saved</span>
                  <span v-else>Save</span>
                </button>
              </div>

              <!-- Diff hint -->
              <div v-if="isDirty(byKey[key])" class="flex items-center gap-1.5 text-xs text-primary/70 -mt-1">
                <span class="font-mono opacity-60">{{ byKey[key].value }}</span>
                <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3" />
                </svg>
                <span class="font-mono font-semibold text-primary">{{ edits[key] }}</span>
              </div>
            </div>
          </template>
        </div>

      </div>

      <!-- Danger zone -->
      <div class="bg-base-100 rounded-2xl border border-error/20 p-5 mt-1">
        <div class="flex items-center gap-2 mb-1">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-error shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span class="font-semibold text-error text-sm">Danger Zone</span>
        </div>
        <p class="text-xs text-base-content/40 mb-3">Reset all settings to factory defaults. This action is irreversible.</p>
        <button class="btn btn-sm btn-error btn-outline" @click="confirmReset">
          Reset all to defaults
        </button>
      </div>
    </template>

  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import api from '@/api/client'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'

const toast = useToast()
const { confirm } = useConfirm()

const settings = ref([])
const loading   = ref(false)
const edits     = reactive({})
const saving    = reactive({})
const saved     = reactive({})

// ── Display metadata (labels, hints, min/max) ─────────────────────────────
const META = {
  access_token_expire_hours: { label: 'JWT Token Expiry',      hint: 'hours (1–720)', min: 1,    max: 720  },
  match_threshold:           { label: 'Match Threshold',        hint: '0.0–1.0',       min: 0.1,  max: 1.0  },
  min_face_quality:          { label: 'Min Face Quality',       hint: '0.0–1.0',       min: 0.0,  max: 1.0  },
  anti_spoof_enabled:        { label: 'Anti-Spoofing',          hint: '0=off, 1=on (requires model)', min: 0, max: 1 },
  anti_spoof_threshold:      { label: 'Anti-Spoof Threshold',   hint: '0.0–1.0 liveness score', min: 0.0, max: 1.0 },
  cooldown_seconds:          { label: 'Attendance Cooldown',    hint: 'seconds',       min: 30,   max: 86400 },
  unknown_face_alert:        { label: 'Unknown Face Alert',     hint: 'count per 5min',min: 1,    max: 100  },
  late_threshold_minutes:    { label: 'Late Threshold',         hint: 'minutes after shift start', min: 0, max: 120 },
  max_fps_per_camera:        { label: 'Max FPS per Camera',     hint: '1–30',          min: 1,    max: 30   },
  inference_workers:         { label: 'Inference Workers',      hint: 'threads',       min: 1,    max: 16   },
  face_detect_size:          { label: 'Face Detect Input Size', hint: '320 or 640',    min: 160,  max: 1280 },
  discord_webhook_url:       { label: 'Discord Webhook URL',    hint: 'https://discord.com/api/webhooks/...' },
  telegram_bot_token:        { label: 'Telegram Bot Token',     hint: 'from @BotFather' },
  telegram_chat_id:          { label: 'Telegram Chat ID',       hint: 'chat or group ID' },
  slack_webhook_url:         { label: 'Slack Webhook URL',      hint: 'https://hooks.slack.com/services/...' },
  notify_on_checkin:         { label: 'Notify on Check-in',     hint: '1=on, 0=off', min: 0, max: 1 },
  notify_on_unknown:         { label: 'Notify on Unknown Face', hint: '1=on, 0=off', min: 0, max: 1 },
  notify_on_spoof:           { label: 'Notify on Spoof',        hint: '1=on, 0=off', min: 0, max: 1 },
}

// ── Group definitions ──────────────────────────────────────────────────────
const groups = [
  {
    id: 'security',
    label: 'Security',
    desc: 'Authentication and access token settings',
    icon: '🔐',
    iconBg: 'bg-error/10 text-error',
    keys: ['access_token_expire_hours'],
  },
  {
    id: 'face',
    label: 'Face Recognition',
    desc: 'Matching accuracy and enrollment quality thresholds',
    icon: '👁️',
    iconBg: 'bg-primary/10 text-primary',
    keys: ['match_threshold', 'min_face_quality', 'anti_spoof_enabled', 'anti_spoof_threshold'],
  },
  {
    id: 'attendance',
    label: 'Attendance',
    desc: 'Cooldown period and alert triggers',
    icon: '📋',
    iconBg: 'bg-success/10 text-success',
    keys: ['cooldown_seconds', 'unknown_face_alert', 'late_threshold_minutes'],
  },
  {
    id: 'performance',
    label: 'Performance',
    desc: 'Camera throughput and inference engine settings',
    icon: '⚡',
    iconBg: 'bg-warning/10 text-warning',
    keys: ['max_fps_per_camera', 'inference_workers', 'face_detect_size'],
  },
  {
    id: 'notifications',
    label: 'Notifications',
    desc: 'Real-time alerts via Discord, Telegram, or Slack',
    icon: '🔔',
    iconBg: 'bg-info/10 text-info',
    keys: [
      'discord_webhook_url', 'telegram_bot_token', 'telegram_chat_id',
      'slack_webhook_url', 'notify_on_checkin', 'notify_on_unknown', 'notify_on_spoof',
    ],
  },
]

// ── Computed lookup ────────────────────────────────────────────────────────
const byKey = computed(() => {
  const m = {}
  for (const s of settings.value) m[s.key] = s
  return m
})

// ── Defaults for factory reset ─────────────────────────────────────────────
const DEFAULTS = {
  access_token_expire_hours: '8',
  match_threshold:    '0.72',
  min_face_quality:   '0.6',
  cooldown_seconds:   '300',
  unknown_face_alert: '5',
  max_fps_per_camera: '2',
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
    toast.success(`${META[s.key]?.label || s.key} updated to ${res.data.value}`)
    setTimeout(() => { delete saved[s.key] }, 2500)
  } catch (e) {
    toast.error(e.response?.data?.detail || `Failed to save ${s.key}`)
  } finally {
    saving[s.key] = false
  }
}

async function confirmReset() {
  if (!await confirm(
    'Reset all settings to factory defaults? This cannot be undone.',
    { title: 'Factory Reset', confirmLabel: 'Reset', confirmClass: 'btn-warning' }
  )) return

  let count = 0
  for (const s of settings.value) {
    const def = DEFAULTS[s.key]
    if (def !== undefined && def !== s.value) {
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
