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
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <template v-for="key in group.keys" :key="key">
            <div
              v-if="byKey[key]"
              class="bg-base-100 rounded-2xl border transition-colors"
              :class="[
                isString(key) ? 'md:col-span-2' : '',
                isDirty(byKey[key]) ? 'border-primary/40 bg-primary/5' : 'border-base-300',
              ]"
            >

              <!-- ── TOGGLE CARD ───────────────────────────────── -->
              <div v-if="isBool(key)" class="flex items-center gap-4 p-4">
                <div class="flex-1 min-w-0">
                  <div class="font-semibold text-sm">{{ META[key]?.label || key }}</div>
                  <p class="text-xs text-base-content/40 mt-0.5 leading-relaxed">{{ byKey[key].description }}</p>
                </div>
                <div class="flex items-center gap-2 shrink-0">
                  <span class="badge badge-xs" :class="livenessBadge(byKey[key].liveness)">
                    {{ livenessIcon(byKey[key].liveness) }} {{ byKey[key].liveness }}
                  </span>
                  <span v-if="saving[key]" class="loading loading-spinner loading-xs text-primary"></span>
                  <input
                    v-else
                    type="checkbox"
                    class="toggle toggle-primary toggle-sm"
                    :checked="numVal(key) === 1"
                    @change="saveToggle(key, $event.target.checked)"
                  />
                </div>
              </div>

              <!-- ── STRING CARD ───────────────────────────────── -->
              <div v-else-if="isString(key)" class="flex flex-col gap-3 p-4">
                <div class="flex items-start justify-between gap-2">
                  <div class="flex flex-col gap-0.5 min-w-0">
                    <span class="font-semibold text-sm">{{ META[key]?.label || key }}</span>
                    <p class="text-xs text-base-content/40 leading-relaxed">{{ byKey[key].description }}</p>
                  </div>
                  <span class="badge badge-xs shrink-0" :class="livenessBadge(byKey[key].liveness)">
                    {{ livenessIcon(byKey[key].liveness) }} {{ byKey[key].liveness }}
                  </span>
                </div>
                <div class="flex items-center gap-2">
                  <div class="relative flex-1">
                    <input
                      :value="edits[key] ?? byKey[key].value"
                      @input="edits[key] = $event.target.value"
                      class="input input-bordered input-sm w-full"
                      :class="[isDirty(byKey[key]) ? 'input-primary' : '', isSecret(key) ? 'pr-9' : '']"
                      :type="isSecret(key) && !showSecret[key] ? 'password' : 'text'"
                      :placeholder="META[key]?.hint || ''"
                    />
                    <button
                      v-if="isSecret(key)"
                      type="button"
                      class="absolute right-2 top-1/2 -translate-y-1/2 text-base-content/40 hover:text-base-content transition-colors"
                      @click="showSecret[key] = !showSecret[key]"
                    >
                      <svg v-if="!showSecret[key]" xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                      <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 4.411m0 0L21 21" />
                      </svg>
                    </button>
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
                <div v-if="isDirty(byKey[key])" class="flex items-center gap-1.5 text-xs text-primary/70 -mt-1">
                  <span class="font-mono opacity-60 truncate max-w-[10rem]">{{ byKey[key].value || '(empty)' }}</span>
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3" />
                  </svg>
                  <span class="font-mono font-semibold text-primary truncate max-w-[10rem]">{{ edits[key] || '(empty)' }}</span>
                </div>
              </div>

              <!-- ── SLIDER CARD ───────────────────────────────── -->
              <div v-else class="flex flex-col gap-3 p-4">
                <!-- Title row -->
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

                <!-- Slider + value -->
                <div class="flex items-center gap-3">
                  <input
                    type="range"
                    class="range range-sm flex-1"
                    :class="rangeClass(key)"
                    :min="isStepped(key) ? 0 : (META[key]?.min ?? 0)"
                    :max="isStepped(key) ? (FACE_DETECT_STEPS.length - 1) : (META[key]?.max ?? 100)"
                    :step="byKey[key].value_type === 'float' ? 0.01 : 1"
                    :value="isStepped(key) ? sizeToIndex(numVal(key)) : numVal(key)"
                    @input="onSliderInput(key, $event.target.value)"
                  />
                  <div class="flex flex-col items-end shrink-0 min-w-[3.5rem]">
                    <span
                      class="text-sm font-bold font-mono tabular-nums leading-tight"
                      :class="FLOAT_GRADIENT_KEYS.includes(key) ? gradientTextClass(key) : 'text-primary'"
                    >
                      {{ displayVal(key) }}
                    </span>
                    <span v-if="showRaw(key)" class="text-xs text-base-content/35 font-mono leading-tight">
                      {{ rawVal(key) }}
                    </span>
                  </div>
                </div>

                <!-- Min / tick / max labels -->
                <div class="-mt-2">
                  <div v-if="isStepped(key)" class="flex justify-between text-xs text-base-content/30">
                    <span v-for="step in FACE_DETECT_STEPS" :key="step">{{ step }}</span>
                  </div>
                  <div v-else class="flex justify-between text-xs text-base-content/30">
                    <span>{{ META[key]?.min ?? 0 }}</span>
                    <span v-if="META[key]?.hint" class="opacity-70">{{ META[key].hint }}</span>
                    <span>{{ META[key]?.max ?? 100 }}</span>
                  </div>
                </div>

                <!-- Diff + Save -->
                <div class="flex items-center justify-between gap-2 pt-2 border-t border-base-200">
                  <div v-if="isDirty(byKey[key])" class="flex items-center gap-1.5 text-xs text-primary/70">
                    <span class="font-mono opacity-60">{{ byKey[key].value }}</span>
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3" />
                    </svg>
                    <span class="font-mono font-semibold text-primary">{{ edits[key] }}</span>
                  </div>
                  <span v-else class="text-xs text-base-content/25 italic">no pending changes</span>
                  <button
                    class="btn btn-xs min-w-[4.5rem]"
                    :class="isDirty(byKey[key]) ? 'btn-primary' : 'btn-ghost'"
                    :disabled="!isDirty(byKey[key]) || !!saving[key]"
                    @click="saveSetting(byKey[key])"
                  >
                    <span v-if="saving[key]" class="loading loading-spinner loading-xs"></span>
                    <span v-else-if="saved[key]" class="text-success">✓ Saved</span>
                    <span v-else>Save</span>
                  </button>
                </div>
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

const settings  = ref([])
const loading   = ref(false)
const edits     = reactive({})
const saving    = reactive({})
const saved     = reactive({})
const showSecret = reactive({})

const BOOL_KEYS           = ['anti_spoof_enabled', 'notify_on_checkin', 'notify_on_unknown', 'notify_on_spoof', 'notify_on_absent']
const STRING_KEYS         = ['discord_webhook_url', 'telegram_bot_token', 'telegram_chat_id', 'slack_webhook_url', 'line_notify_token', 'email_smtp_server', 'email_smtp_user', 'email_smtp_password', 'email_to_address']
const SECRET_KEYS         = ['telegram_bot_token', 'discord_webhook_url', 'slack_webhook_url', 'line_notify_token', 'email_smtp_password']
const FLOAT_GRADIENT_KEYS = ['match_threshold', 'min_face_quality', 'anti_spoof_threshold']
const FACE_DETECT_STEPS   = [160, 320, 640, 1280]

// ── Display metadata ───────────────────────────────────────────────────────
const META = {
  access_token_expire_hours: { label: 'JWT Token Expiry',      hint: 'hours (1–720)', min: 1,    max: 720  },
  match_threshold:           { label: 'Match Threshold',        hint: '0.1–1.0',       min: 0.1,  max: 1.0  },
  min_face_quality:          { label: 'Min Face Quality',       hint: '0.0–1.0',       min: 0.0,  max: 1.0  },
  anti_spoof_enabled:        { label: 'Anti-Spoofing',          hint: '0=off, 1=on',   min: 0,    max: 1    },
  anti_spoof_threshold:      { label: 'Anti-Spoof Threshold',   hint: '0.0–1.0',       min: 0.0,  max: 1.0  },
  cooldown_seconds:          { label: 'Attendance Cooldown',    hint: 'seconds',       min: 30,   max: 86400 },
  unknown_face_alert:        { label: 'Unknown Face Alert',     hint: 'count / 5 min', min: 1,    max: 100  },
  late_threshold_minutes:    { label: 'Late Threshold',         hint: 'min after shift start', min: 0, max: 120 },
  max_fps_per_camera:        { label: 'Max FPS per Camera',     hint: 'fps',           min: 1,    max: 30   },
  inference_workers:         { label: 'Inference Workers',      hint: 'threads',       min: 1,    max: 16   },
  recognition_cache_ttl:     { label: 'Recognition Cache TTL',  hint: 'sec — reuse result per tracked face (5–300)', min: 5, max: 300 },
  face_detect_size:          { label: 'Face Detect Input Size', hint: 'px',            min: 160,  max: 1280 },
  discord_webhook_url:       { label: 'Discord Webhook URL',    hint: 'https://discord.com/api/webhooks/...' },
  telegram_bot_token:        { label: 'Telegram Bot Token',     hint: 'from @BotFather' },
  telegram_chat_id:          { label: 'Telegram Chat ID',       hint: 'chat or group ID' },
  slack_webhook_url:         { label: 'Slack Webhook URL',      hint: 'https://hooks.slack.com/services/...' },
  notify_on_checkin:         { label: 'Notify on Check-in',     hint: '1=on, 0=off',   min: 0,    max: 1    },
  notify_on_unknown:         { label: 'Notify on Unknown Face', hint: '1=on, 0=off',   min: 0,    max: 1    },
  notify_on_spoof:           { label: 'Notify on Spoof',        hint: '1=on, 0=off',   min: 0,    max: 1    },
  notify_on_absent:          { label: 'Notify on Absent',       hint: '1=on, 0=off',   min: 0,    max: 1    },
  line_notify_token:         { label: 'Line Notify Token',      hint: 'from notify-bot.line.me/my/' },
  email_smtp_server:         { label: 'SMTP Server',            hint: 'e.g. smtp.gmail.com' },
  email_smtp_port:           { label: 'SMTP Port',              hint: '587=TLS, 465=SSL',  min: 1, max: 65535 },
  email_smtp_user:           { label: 'SMTP Username',          hint: 'sender email address' },
  email_smtp_password:       { label: 'SMTP Password',          hint: 'password or App Password' },
  email_to_address:          { label: 'Recipient Email',        hint: 'notification destination address' },
}

// ── Group definitions ──────────────────────────────────────────────────────
const groups = [
  { id: 'security',      label: 'Security',          desc: 'Authentication and access token settings',              icon: '🔐', iconBg: 'bg-error/10 text-error',   keys: ['access_token_expire_hours'] },
  { id: 'face',          label: 'Face Recognition',  desc: 'Matching accuracy and enrollment quality thresholds',   icon: '👁️', iconBg: 'bg-primary/10 text-primary', keys: ['match_threshold', 'min_face_quality', 'anti_spoof_enabled', 'anti_spoof_threshold'] },
  { id: 'attendance',    label: 'Attendance',         desc: 'Cooldown period and alert triggers',                    icon: '📋', iconBg: 'bg-success/10 text-success', keys: ['cooldown_seconds', 'unknown_face_alert', 'late_threshold_minutes'] },
  { id: 'performance',   label: 'Performance',        desc: 'Camera throughput and inference engine settings',       icon: '⚡', iconBg: 'bg-warning/10 text-warning', keys: ['max_fps_per_camera', 'inference_workers', 'recognition_cache_ttl', 'face_detect_size'] },
  { id: 'notifications', label: 'Notifications',      desc: 'Real-time alerts via Discord, Telegram, Slack, Line, or Email', icon: '🔔', iconBg: 'bg-info/10 text-info', keys: ['discord_webhook_url', 'telegram_bot_token', 'telegram_chat_id', 'slack_webhook_url', 'line_notify_token', 'email_smtp_server', 'email_smtp_port', 'email_smtp_user', 'email_smtp_password', 'email_to_address', 'notify_on_checkin', 'notify_on_unknown', 'notify_on_spoof', 'notify_on_absent'] },
]

// ── Computed lookup ────────────────────────────────────────────────────────
const byKey = computed(() => {
  const m = {}
  for (const s of settings.value) m[s.key] = s
  return m
})

const DEFAULTS = {
  access_token_expire_hours: '8',
  match_threshold:    '0.72',
  min_face_quality:   '0.6',
  cooldown_seconds:   '300',
  unknown_face_alert: '5',
  max_fps_per_camera:    '2',
  inference_workers:     '4',
  recognition_cache_ttl: '30',
  face_detect_size:      '640',
}

// ── Type helpers ───────────────────────────────────────────────────────────
function isBool(key)     { return BOOL_KEYS.includes(key) }
function isString(key)   { return STRING_KEYS.includes(key) }
function isSecret(key)   { return SECRET_KEYS.includes(key) }
function isStepped(key)  { return key === 'face_detect_size' }

// ── Value helpers ──────────────────────────────────────────────────────────
function numVal(key) {
  const s = byKey.value[key]
  if (!s) return 0
  const raw = edits[key] !== undefined ? edits[key] : s.value
  return s.value_type === 'float' ? parseFloat(raw) : parseInt(raw, 10)
}

function sizeToIndex(val) {
  const idx = FACE_DETECT_STEPS.indexOf(Number(val))
  return idx >= 0 ? idx : 2
}

function onSliderInput(key, rawVal) {
  const s = byKey.value[key]
  if (!s) return
  if (isStepped(key)) {
    edits[key] = String(FACE_DETECT_STEPS[Math.min(Math.max(parseInt(rawVal, 10), 0), FACE_DETECT_STEPS.length - 1)])
  } else if (s.value_type === 'float') {
    edits[key] = parseFloat(rawVal).toFixed(2)
  } else {
    edits[key] = String(parseInt(rawVal, 10))
  }
}

function humanCooldown(sec) {
  const s = Number(sec)
  if (s < 60)   return `${s}s`
  if (s < 3600) {
    const m = s / 60
    return `${m === Math.floor(m) ? m : m.toFixed(1)} min`
  }
  const h = s / 3600
  return `${h === Math.floor(h) ? h : h.toFixed(1)} hr`
}

function humanTokenExpiry(hrs) {
  const h = Number(hrs)
  if (h < 24)   return `${h} hr`
  if (h === 24) return '1 day'
  return `${Math.floor(h / 24)} days`
}

function displayVal(key) {
  const v = numVal(key)
  if (key === 'cooldown_seconds')          return humanCooldown(v)
  if (key === 'access_token_expire_hours') return humanTokenExpiry(v)
  if (byKey.value[key]?.value_type === 'float') return v.toFixed(2)
  return String(v)
}

function showRaw(key) {
  if (key === 'cooldown_seconds') return true
  if (key === 'access_token_expire_hours') return numVal(key) >= 24
  return false
}

function rawVal(key) {
  const v = numVal(key)
  if (key === 'cooldown_seconds')          return `${v}s`
  if (key === 'access_token_expire_hours') return `${v}h`
  return String(v)
}

function gradientTextClass(key) {
  const v = numVal(key)
  if (v >= 0.7) return 'text-success'
  if (v >= 0.5) return 'text-warning'
  return 'text-error'
}

function rangeClass(key) {
  if (!FLOAT_GRADIENT_KEYS.includes(key)) return 'range-primary'
  const v = numVal(key)
  if (v >= 0.7) return 'range-success'
  if (v >= 0.5) return 'range-warning'
  return 'range-error'
}

// ── Liveness helpers ───────────────────────────────────────────────────────
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

// ── Save ───────────────────────────────────────────────────────────────────
async function saveToggle(key, checked) {
  const s = byKey.value[key]
  if (!s) return
  saving[key] = true
  try {
    const res = await api.put(`/api/v1/settings/${key}`, { value: checked ? '1' : '0' })
    s.value = res.data.value
    delete edits[key]
    toast.success(`${META[key]?.label || key} ${checked ? 'enabled' : 'disabled'}`)
  } catch (e) {
    toast.error(e.response?.data?.detail || `Failed to save ${key}`)
  } finally {
    saving[key] = false
  }
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
