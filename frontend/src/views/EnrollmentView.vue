<template>
  <div class="flex flex-col gap-5 max-w-3xl">

    <!-- Header -->
    <div class="flex items-center gap-3">
      <RouterLink to="/employees" class="btn btn-ghost btn-sm">← Back</RouterLink>
      <div>
        <h1 class="text-xl font-bold">Face Enrollment</h1>
        <p v-if="employee" class="text-sm text-base-content/50 mt-0.5">
          {{ employee.full_name }} · {{ employee.emp_code }}
        </p>
      </div>
    </div>

    <div class="grid md:grid-cols-2 gap-5 items-start">

      <!-- ── Left: Camera ─────────────────────────────────────────────────── -->
      <div class="flex flex-col gap-3">

        <!-- Live preview -->
        <div class="relative bg-black rounded-xl overflow-hidden" style="aspect-ratio:4/3">
          <video ref="videoEl" class="w-full h-full object-cover" autoplay playsinline muted />

          <!-- Angle instruction overlay -->
          <Transition name="fade">
            <div v-if="cameraReady && activeSlot >= 0"
              class="absolute bottom-0 left-0 right-0 px-4 py-3"
              style="background: linear-gradient(transparent, rgba(0,0,0,0.75))">
              <div class="flex items-center gap-3">
                <div class="text-3xl leading-none">{{ ANGLES[activeSlot].emoji }}</div>
                <div>
                  <div class="text-white font-bold text-sm leading-tight">
                    Shot {{ activeSlot + 1 }}: {{ ANGLES[activeSlot].label }}
                  </div>
                  <div class="text-white/70 text-xs mt-0.5">{{ ANGLES[activeSlot].hint }}</div>
                </div>
              </div>
            </div>
          </Transition>

          <!-- Waiting state -->
          <div v-if="!cameraReady"
            class="absolute inset-0 flex flex-col items-center justify-center gap-2 text-white/40">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span class="text-sm">กด Capture เพื่อเปิดกล้อง</span>
          </div>

          <!-- Flash effect on capture -->
          <Transition name="flash">
            <div v-if="flashing" class="absolute inset-0 bg-white pointer-events-none" />
          </Transition>
        </div>

        <!-- Progress bar -->
        <div>
          <div class="flex justify-between text-xs text-base-content/50 mb-1">
            <span>Progress</span>
            <span>{{ enrolledCount }}/6 shots</span>
          </div>
          <progress class="progress progress-success w-full h-2" :value="enrolledCount" max="6" />
        </div>

        <!-- Capture button -->
        <button
          class="btn btn-primary btn-lg w-full gap-2"
          :class="{ 'btn-success': allDone }"
          :disabled="activeSlot < 0 || capturing"
          @click="capture"
        >
          <span v-if="capturing" class="loading loading-spinner loading-sm"></span>
          <template v-else-if="allDone">
            ✅ ครบทุกมุมแล้ว — กด Submit
          </template>
          <template v-else-if="activeSlot >= 0">
            📸 Capture — {{ ANGLES[activeSlot].label }}
          </template>
        </button>

        <!-- Submit -->
        <button
          class="btn btn-success w-full gap-2"
          :disabled="enrolledCount < 6 || submitting"
          @click="submitEnrollment"
        >
          <span v-if="submitting" class="loading loading-spinner loading-sm"></span>
          {{ submitting ? 'Saving…' : `Submit Enrollment (${enrolledCount}/6)` }}
        </button>

        <!-- Message -->
        <div v-if="message" class="alert text-sm"
          :class="messageType === 'success' ? 'alert-success' : 'alert-error'">
          {{ message }}
        </div>
      </div>

      <!-- ── Right: 6 Angle Slots ──────────────────────────────────────────── -->
      <div class="grid grid-cols-3 gap-2">
        <div
          v-for="(angle, i) in ANGLES" :key="i"
          class="relative rounded-xl border-2 overflow-hidden cursor-pointer transition-all duration-150"
          :class="slotClass(i)"
          @click="setActive(i)"
          :title="angle.label + ' — ' + angle.hint"
        >
          <!-- Captured photo -->
          <img v-if="slots[i]" :src="slots[i].preview"
            class="w-full aspect-square object-cover" />

          <!-- Empty state -->
          <div v-else class="w-full aspect-square flex flex-col items-center justify-center gap-1.5 p-2">
            <AngleFace :direction="angle.direction" :size="36" />
            <div class="text-[11px] font-semibold text-center leading-tight px-1">
              {{ angle.label }}
            </div>
            <div class="text-[9px] text-base-content/40 text-center leading-tight px-1">
              {{ angle.hintShort }}
            </div>
          </div>

          <!-- Active pulse border -->
          <div v-if="i === activeSlot && !slots[i]"
            class="absolute inset-0 rounded-xl ring-2 ring-primary ring-offset-0 animate-pulse pointer-events-none" />

          <!-- Done badge -->
          <div v-if="slots[i]"
            class="absolute top-1 right-1 w-5 h-5 bg-success rounded-full flex items-center justify-center shadow">
            <span class="text-success-content text-[10px] font-bold">✓</span>
          </div>

          <!-- Slot number -->
          <div class="absolute top-1 left-1 w-4 h-4 bg-black/40 rounded-full flex items-center justify-center">
            <span class="text-white text-[9px] font-bold">{{ i + 1 }}</span>
          </div>

          <!-- Delete -->
          <button v-if="slots[i]"
            class="absolute bottom-1 right-1 btn btn-circle btn-xs btn-error opacity-80 hover:opacity-100"
            @click.stop="deleteSlot(i)">
            ✕
          </button>
        </div>
      </div>
    </div>

    <!-- Hidden capture canvas -->
    <canvas ref="captureCanvas" class="hidden" width="640" height="480" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, defineComponent, h } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api/client'

// ── Angle guide definitions ───────────────────────────────────────────────────
// 6 poses that maximise recognition coverage across angles and lighting
const ANGLES = [
  {
    label:     'หน้าตรง',
    hint:      'มองตรงเข้ากล้อง ตาตรง ไม่เอียง',
    hintShort: 'มองตรงเข้ากล้อง',
    emoji:     '😐',
    direction: 'front',
  },
  {
    label:     'หันซ้าย',
    hint:      'หันหน้าไปทางซ้ายประมาณ 30°',
    hintShort: 'หันซ้าย ~30°',
    emoji:     '↰',
    direction: 'left',
  },
  {
    label:     'หันขวา',
    hint:      'หันหน้าไปทางขวาประมาณ 30°',
    hintShort: 'หันขวา ~30°',
    emoji:     '↱',
    direction: 'right',
  },
  {
    label:     'เงยหน้า',
    hint:      'เงยคางขึ้น มองกล้องจากด้านล่าง',
    hintShort: 'เงยคางขึ้น',
    emoji:     '⬆️',
    direction: 'up',
  },
  {
    label:     'ก้มหน้า',
    hint:      'ก้มศีรษะลงเล็กน้อย มองกล้องจากด้านบน',
    hintShort: 'ก้มศีรษะลง',
    emoji:     '⬇️',
    direction: 'down',
  },
  {
    label:     'เอียงซ้าย',
    hint:      'เอียงศีรษะไปทางซ้าย (หูซ้ายลง)',
    hintShort: 'เอียงหัวซ้าย',
    emoji:     '↙️',
    direction: 'tilt',
  },
]

// ── AngleFace SVG component ───────────────────────────────────────────────────
// Draws a simple face circle + directional arrow to indicate the required pose
const AngleFace = defineComponent({
  props: { direction: String, size: { type: Number, default: 36 } },
  setup(props) {
    return () => {
      const s   = props.size
      const cx  = s / 2
      const cy  = s / 2
      const r   = s * 0.32        // face circle radius
      const ar  = s * 0.14        // arrow arm length

      // Arrow tip based on direction
      const arrows = {
        front: null,
        left:  { x1: cx, y1: cy, x2: cx - ar * 1.4, y2: cy },
        right: { x1: cx, y1: cy, x2: cx + ar * 1.4, y2: cy },
        up:    { x1: cx, y1: cy, x2: cx, y2: cy - ar * 1.4 },
        down:  { x1: cx, y1: cy, x2: cx, y2: cy + ar * 1.4 },
        tilt:  { x1: cx, y1: cy, x2: cx - ar, y2: cy + ar },
      }
      const arr = arrows[props.direction]

      // Eyes
      const eyeY  = cy - r * 0.22
      const eyeOff = r * 0.35
      const eyeR   = r * 0.12

      // Mouth arc
      const mY  = cy + r * 0.28
      const mW  = r * 0.45
      const mH  = r * 0.18

      return h('svg', {
        width: s, height: s,
        viewBox: `0 0 ${s} ${s}`,
        style: 'display:block',
      }, [
        // Face circle
        h('circle', {
          cx, cy: cy, r,
          fill: 'none',
          stroke: 'currentColor',
          'stroke-width': s * 0.05,
          opacity: 0.6,
        }),
        // Left eye
        h('circle', { cx: cx - eyeOff, cy: eyeY, r: eyeR, fill: 'currentColor', opacity: 0.6 }),
        // Right eye
        h('circle', { cx: cx + eyeOff, cy: eyeY, r: eyeR, fill: 'currentColor', opacity: 0.6 }),
        // Mouth
        h('path', {
          d: `M ${cx - mW} ${mY} Q ${cx} ${mY + mH} ${cx + mW} ${mY}`,
          fill: 'none',
          stroke: 'currentColor',
          'stroke-width': s * 0.04,
          'stroke-linecap': 'round',
          opacity: 0.6,
        }),
        // Direction arrow
        arr ? h('line', {
          x1: arr.x1, y1: arr.y1, x2: arr.x2, y2: arr.y2,
          stroke: 'oklch(var(--p))',
          'stroke-width': s * 0.07,
          'stroke-linecap': 'round',
          'marker-end': `url(#arr-${props.direction})`,
        }) : null,
        // Arrowhead marker
        arr ? h('defs', {}, [
          h('marker', {
            id: `arr-${props.direction}`,
            markerWidth: 4, markerHeight: 4,
            refX: 2, refY: 2,
            orient: 'auto',
          }, [
            h('polygon', {
              points: '0,0 4,2 0,4',
              fill: 'oklch(var(--p))',
            }),
          ]),
        ]) : null,
      ])
    }
  },
})

// ── State ─────────────────────────────────────────────────────────────────────
const route        = useRoute()
const employee     = ref(null)
const slots        = ref(Array(6).fill(null))
const videoEl      = ref(null)
const captureCanvas = ref(null)
const cameraReady  = ref(false)
const capturing    = ref(false)
const flashing     = ref(false)
const submitting   = ref(false)
const message      = ref('')
const messageType  = ref('success')

// Active slot = next empty slot
const activeSlot = computed(() => {
  const idx = slots.value.findIndex(s => !s)
  return idx  // -1 when all done
})

const enrolledCount = computed(() => slots.value.filter(Boolean).length)
const allDone       = computed(() => enrolledCount.value === 6)

let stream = null

// ── Camera ────────────────────────────────────────────────────────────────────
async function _openCamera() {
  if (stream) return
  stream = await navigator.mediaDevices.getUserMedia({
    video: { width: { ideal: 640 }, height: { ideal: 480 } },
    audio: false,
  })
  videoEl.value.srcObject = stream
  await new Promise(r => { videoEl.value.onloadedmetadata = r })
  cameraReady.value = true
}

// ── Capture ───────────────────────────────────────────────────────────────────
async function capture() {
  if (activeSlot.value < 0) return
  capturing.value = true
  try {
    await _openCamera()

    const canvas = captureCanvas.value
    canvas.getContext('2d').drawImage(videoEl.value, 0, 0, 640, 480)

    await new Promise((resolve, reject) => {
      canvas.toBlob((blob) => {
        if (!blob) { reject(new Error('Blob failed')); return }
        const preview = URL.createObjectURL(blob)
        slots.value[activeSlot.value] = { blob, preview }
        resolve()
      }, 'image/jpeg', 0.9)
    })

    // Flash effect
    flashing.value = true
    setTimeout(() => { flashing.value = false }, 150)

  } catch (e) {
    message.value = 'Camera error: ' + (e.message || e)
    messageType.value = 'error'
  } finally {
    capturing.value = false
  }
}

// ── Slot management ───────────────────────────────────────────────────────────
function setActive(i) {
  // Click on a filled slot → delete it (re-shoot)
  // Click on an empty slot → handled by activeSlot computed (auto-advance)
  // We allow clicking any empty slot to jump to it — but activeSlot is auto
  // For simplicity: clicking a filled slot prompts re-capture via deleteSlot
  if (slots.value[i]) deleteSlot(i)
}

function deleteSlot(i) {
  if (slots.value[i]?.preview) URL.revokeObjectURL(slots.value[i].preview)
  slots.value[i] = null
}

// ── Slot card styling ─────────────────────────────────────────────────────────
function slotClass(i) {
  if (slots.value[i])          return 'border-success bg-success/5'
  if (i === activeSlot.value)  return 'border-primary bg-primary/5'
  return 'border-base-300 border-dashed hover:border-base-content/30'
}

// ── Submit ────────────────────────────────────────────────────────────────────
async function submitEnrollment() {
  submitting.value = true
  message.value = ''
  try {
    for (let i = 0; i < 6; i++) {
      if (!slots.value[i]) continue
      const fd = new FormData()
      fd.append('sample_index', i)
      fd.append('file', slots.value[i].blob, `sample_${i}.jpg`)
      await api.post(`/api/v1/employees/${route.params.id}/enroll`, fd)
    }
    messageType.value = 'success'
    message.value = '✅ Enrollment complete! Employee is now active.'
  } catch (e) {
    messageType.value = 'error'
    message.value = e.response?.data?.detail || 'Upload failed'
  } finally {
    submitting.value = false
  }
}

// ── Lifecycle ─────────────────────────────────────────────────────────────────
onMounted(async () => {
  const { data } = await api.get(`/api/v1/employees/${route.params.id}`)
  employee.value = data
})

onUnmounted(() => {
  if (stream) stream.getTracks().forEach(t => t.stop())
  slots.value.forEach(s => { if (s?.preview) URL.revokeObjectURL(s.preview) })
})
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.25s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.flash-enter-active { transition: opacity 0.05s; }
.flash-leave-active { transition: opacity 0.15s; }
.flash-enter-from, .flash-leave-to { opacity: 0; }
.flash-enter-to { opacity: 0.7; }
</style>
