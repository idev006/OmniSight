<template>
  <div class="flex flex-col gap-5">

    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-bold tracking-wide">System Info</h1>
        <p class="text-sm text-base-content/40 mt-0.5">
          สถานะ live ของทุก service ที่ระบบต้องการ — รีเฟรชเมื่อสงสัยว่ามีปัญหา
        </p>
      </div>
      <button class="btn btn-sm btn-ghost gap-2" :class="loading && 'loading'" @click="load">
        <svg v-if="!loading" xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
        </svg>
        Refresh
      </button>
    </div>

    <!-- Quick-read legend -->
    <div class="flex gap-3 text-xs flex-wrap">
      <span class="flex items-center gap-1.5">
        <span class="badge badge-success badge-xs"></span>
        <span class="text-base-content/50">ทำงานปกติ</span>
      </span>
      <span class="flex items-center gap-1.5">
        <span class="badge badge-error badge-xs"></span>
        <span class="text-base-content/50">มีปัญหา — ดูรายละเอียดในการ์ดนั้น</span>
      </span>
    </div>

    <div v-if="error" class="alert alert-error">{{ error }}</div>

    <div v-if="info" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">

      <!-- ─── Application ──────────────────────────────────────────── -->
      <div class="card bg-base-100 shadow-sm border border-base-300">
        <div class="card-body p-4 gap-3">
          <div class="flex items-center gap-2">
            <span class="text-lg">🖥️</span>
            <div>
              <h2 class="font-bold leading-tight">Application</h2>
              <p class="text-xs text-base-content/40 leading-tight">Backend API server (FastAPI)</p>
            </div>
            <div class="badge badge-success badge-sm ml-auto">running</div>
          </div>
          <div class="flex flex-col gap-1.5 text-sm">
            <Row label="Version"         :value="info.app.version" />
            <Row label="Uptime"          :value="formatUptime(info.app.uptime_seconds)"
                 :hint="'เวลาตั้งแต่ backend เริ่มทำงานครั้งล่าสุด'" />
            <Row label="ONNX Provider"   :value="info.app.onnx_provider"
                 :highlight="onnxColor(info.app.onnx_provider)" />
          </div>
          <!-- ONNX explain -->
          <div class="text-xs rounded-lg px-2.5 py-1.5 leading-snug"
               :class="onnxBg(info.app.onnx_provider)">
            {{ onnxNote(info.app.onnx_provider) }}
          </div>
          <div class="flex flex-col gap-1.5 text-sm">
            <Row label="Detect Size"     :value="`${info.app.face_detect_size}×${info.app.face_detect_size} px`"
                 hint="ขนาด input ของโมเดลตรวจจับใบหน้า (320=เร็ว / 640=แม่น)" />
            <Row label="Infer Workers"   :value="String(info.app.inference_workers)"
                 hint="จำนวน thread ที่ประมวลผล AI พร้อมกัน" />
          </div>
        </div>
      </div>

      <!-- ─── Face Engine ──────────────────────────────────────────── -->
      <div class="card bg-base-100 shadow-sm border border-base-300">
        <div class="card-body p-4 gap-3">
          <div class="flex items-center gap-2">
            <span class="text-lg">🧠</span>
            <div>
              <h2 class="font-bold leading-tight">Face Engine</h2>
              <p class="text-xs text-base-content/40 leading-tight">โมเดล AI ตรวจจับ + จดจำใบหน้า</p>
            </div>
            <StatusBadge :ok="info.face_engine.loaded" />
          </div>
          <div class="flex flex-col gap-1.5 text-sm">
            <Row label="Model"     :value="info.face_engine.model" />
            <Row label="Det Size"  :value="`${info.face_engine.det_size}×${info.face_engine.det_size} px`" />
            <Row label="Status"    :value="info.face_engine.status" />
          </div>
          <div v-if="!info.face_engine.loaded" class="text-xs text-error bg-error/5 rounded-lg px-2.5 py-1.5 leading-snug">
            ❌ โมเดลโหลดไม่สำเร็จ — enrollment และ scan จะไม่ทำงาน<br>
            ตรวจสอบ: โฟลเดอร์ <code class="font-mono">models/</code> และ log ของ backend
          </div>
          <div v-else class="text-xs text-success/70 bg-success/5 rounded-lg px-2.5 py-1.5 leading-snug">
            ✅ buffalo_l โหลดแล้ว — ระบบพร้อม scan และ enrollment
          </div>
        </div>
      </div>

      <!-- ─── Anti-Spoof ───────────────────────────────────────────── -->
      <div class="card bg-base-100 shadow-sm border border-base-300">
        <div class="card-body p-4 gap-3">
          <div class="flex items-center gap-2">
            <span class="text-lg">🛡️</span>
            <div>
              <h2 class="font-bold leading-tight">Anti-Spoof</h2>
              <p class="text-xs text-base-content/40 leading-tight">ป้องกันการใช้รูปถ่ายหรือหน้ากากแทนใบหน้าจริง</p>
            </div>
            <StatusBadge :ok="info.anti_spoof.available" ok-label="available" fail-label="unavailable" />
          </div>
          <div class="flex flex-col gap-1.5 text-sm">
            <Row label="Model"     :value="info.anti_spoof.model" />
            <Row label="Available" :value="info.anti_spoof.available ? 'Yes' : 'No'" />
          </div>
          <div v-if="info.anti_spoof.available"
               class="text-xs text-success/70 bg-success/5 rounded-lg px-2.5 py-1.5 leading-snug">
            ✅ โมเดลพร้อมใช้งาน — เปิด/ปิดได้ที่ Settings → Anti-spoofing
          </div>
          <div v-else class="text-xs text-warning/70 bg-warning/5 rounded-lg px-2.5 py-1.5 leading-snug">
            ⚠️ ไม่พบไฟล์โมเดล — ระบบยังทำงานได้ปกติ แต่ไม่มีการตรวจสอบความเป็นมนุษย์<br>
            วิธีติดตั้ง: <code class="font-mono text-xs">python scripts/download_anti_spoof_model.py</code>
          </div>
          <div class="text-xs text-base-content/40 leading-snug">
            ℹ️ {{ info.anti_spoof.note }}
          </div>
        </div>
      </div>

      <!-- ─── PostgreSQL ───────────────────────────────────────────── -->
      <div class="card bg-base-100 shadow-sm border border-base-300">
        <div class="card-body p-4 gap-3">
          <div class="flex items-center gap-2">
            <span class="text-lg">🐘</span>
            <div>
              <h2 class="font-bold leading-tight">PostgreSQL</h2>
              <p class="text-xs text-base-content/40 leading-tight">ฐานข้อมูลหลัก — พนักงาน, การลงเวลา, ผู้ใช้</p>
            </div>
            <StatusBadge :ok="info.postgres.status === 'ok'" />
          </div>
          <template v-if="info.postgres.status === 'ok'">
            <div class="flex flex-col gap-1.5 text-sm">
              <Row label="Version"   :value="info.postgres.version" />
              <Row label="DB Size"   :value="`${info.postgres.size_mb} MB`"
                   hint="ขนาดของฐานข้อมูลทั้งหมด ถ้าใกล้เต็ม disk ให้รัน backup และล้างข้อมูลเก่า" />
              <Row label="Host"      :value="info.postgres.url" mono />
            </div>
            <div class="divider my-0 text-xs opacity-30">จำนวนแถวในแต่ละตาราง</div>
            <div class="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
              <Stat label="พนักงานทั้งหมด"    :value="info.postgres.rows.employees" />
              <Stat label="Active"             :value="info.postgres.rows.employees_active" />
              <Stat label="Enrolled (มีใบหน้า)" :value="info.postgres.rows.employees_enrolled" />
              <Stat label="Face Templates"     :value="info.postgres.rows.face_templates" />
              <Stat label="บันทึกลงเวลา"       :value="info.postgres.rows.attendance_logs" />
              <Stat label="แผนก"               :value="info.postgres.rows.departments" />
              <Stat label="สถานีสแกน"          :value="info.postgres.rows.stations" />
              <Stat label="ผู้ใช้ระบบ"         :value="info.postgres.rows.users" />
            </div>
            <div class="text-xs text-base-content/40 leading-snug mt-1">
              ℹ️ Face Templates ควรเท่ากับ Enrolled × 6 (6 มุมต่อคน)
            </div>
          </template>
          <div v-else class="text-xs text-error bg-error/5 rounded-lg p-2.5">
            ❌ เชื่อมต่อฐานข้อมูลไม่ได้ — ระบบจะหยุดทำงานทั้งหมด<br>
            <span class="font-mono">{{ info.postgres.error }}</span><br>
            ตรวจสอบ: Docker container <code class="font-mono">omnisight-postgres</code> รันอยู่หรือไม่
          </div>
        </div>
      </div>

      <!-- ─── Qdrant ───────────────────────────────────────────────── -->
      <div class="card bg-base-100 shadow-sm border border-base-300">
        <div class="card-body p-4 gap-3">
          <div class="flex items-center gap-2">
            <span class="text-lg">🔍</span>
            <div>
              <h2 class="font-bold leading-tight">Qdrant</h2>
              <p class="text-xs text-base-content/40 leading-tight">Vector DB — เก็บข้อมูลใบหน้าสำหรับค้นหาตัวตน</p>
            </div>
            <StatusBadge :ok="info.qdrant.status === 'ok'" />
          </div>
          <template v-if="info.qdrant.status === 'ok'">
            <div class="flex flex-col gap-1.5 text-sm">
              <Row label="Host"         :value="info.qdrant.host" mono />
              <Row label="Collection"   :value="info.qdrant.collection" />
              <Row label="Points (ใบหน้า)" :value="info.qdrant.points_count.toLocaleString()"
                   hint="จำนวน face template ที่ลงทะเบียนแล้ว ควรตรงกับ 'Face Templates' ใน PostgreSQL" />
              <Row label="Vector Size"  :value="`${info.qdrant.vector_size}D`"
                   hint="ขนาดของ embedding vector (512 มิติ = มาตรฐาน InsightFace)" />
              <Row label="Distance"     :value="info.qdrant.distance"
                   hint="วิธีวัดความเหมือนของใบหน้า (Cosine = มาตรฐาน)" />
              <Row label="Quantization" :value="info.qdrant.quantization"
                   hint="การบีบอัด vector เพื่อประหยัด RAM โดยไม่เสียความแม่นยำมาก" />
            </div>
            <!-- Sync check -->
            <div class="text-xs rounded-lg px-2.5 py-1.5 leading-snug"
                 :class="qdrantSyncOk ? 'text-success/70 bg-success/5' : 'text-warning/70 bg-warning/5'">
              <template v-if="qdrantSyncOk">
                ✅ Points ({{ info.qdrant.points_count }}) ตรงกับ Face Templates ใน DB ({{ info.postgres?.rows?.face_templates }})
              </template>
              <template v-else>
                ⚠️ Points ({{ info.qdrant.points_count }}) ≠ Face Templates ใน DB ({{ info.postgres?.rows?.face_templates }}) — อาจมี orphan vectors<br>
                วิธีแก้: รัน <code class="font-mono">python scripts/reconcile_qdrant.py</code>
              </template>
            </div>
          </template>
          <div v-else class="text-xs text-error bg-error/5 rounded-lg p-2.5">
            ❌ เชื่อมต่อ Qdrant ไม่ได้ — การ scan จะหา match ไม่ได้<br>
            <span class="font-mono">{{ info.qdrant.error }}</span><br>
            ตรวจสอบ: Docker container <code class="font-mono">omnisight-qdrant</code>
          </div>
        </div>
      </div>

      <!-- ─── Redis ───────────────────────────────────────────────── -->
      <div class="card bg-base-100 shadow-sm border border-base-300">
        <div class="card-body p-4 gap-3">
          <div class="flex items-center gap-2">
            <span class="text-lg">⚡</span>
            <div>
              <h2 class="font-bold leading-tight">Redis</h2>
              <p class="text-xs text-base-content/40 leading-tight">Cache — settings, cooldown, การแจ้งเตือน</p>
            </div>
            <StatusBadge :ok="info.redis.status === 'ok'" />
          </div>
          <template v-if="info.redis.status === 'ok'">
            <div class="flex flex-col gap-1.5 text-sm">
              <Row label="URL"             :value="info.redis.url" mono />
              <Row label="Version"         :value="info.redis.version" />
              <Row label="Memory Used"     :value="`${info.redis.used_memory_mb} MB`"
                   hint="RAM ที่ Redis ใช้อยู่ตอนนี้ — ปกติควรต่ำกว่า 50 MB" />
              <Row label="Memory Peak"     :value="`${info.redis.peak_memory_mb} MB`" />
              <Row label="Clients"         :value="String(info.redis.connected_clients)"
                   hint="จำนวน connection ที่เชื่อมต่ออยู่ (backend + workers)" />
              <Row label="Uptime"          :value="formatUptime(info.redis.uptime_seconds)" />
              <Row v-if="info.redis.keyspace" label="Keys" :value="String(info.redis.keyspace?.keys ?? '—')"
                   hint="จำนวน key ที่เก็บอยู่ใน Redis ตอนนี้" />
            </div>
            <div class="text-xs text-base-content/40 leading-snug">
              ℹ️ Redis ใช้เก็บ: settings live, cooldown ป้องกัน log ซ้ำ, station filter, event bus การแจ้งเตือน
            </div>
          </template>
          <div v-else class="text-xs text-error bg-error/5 rounded-lg p-2.5">
            ❌ เชื่อมต่อ Redis ไม่ได้ — settings จะไม่ live-reload, การแจ้งเตือนหยุด<br>
            <span class="font-mono">{{ info.redis.error }}</span><br>
            ตรวจสอบ: Docker container <code class="font-mono">omnisight-redis</code>
          </div>
        </div>
      </div>

      <!-- ─── Storage ─────────────────────────────────────────────── -->
      <div class="card bg-base-100 shadow-sm border border-base-300 md:col-span-2 xl:col-span-3">
        <div class="card-body p-4 gap-3">
          <div class="flex items-center gap-2">
            <span class="text-lg">💾</span>
            <div>
              <h2 class="font-bold leading-tight">Storage</h2>
              <p class="text-xs text-base-content/40 leading-tight">พื้นที่เก็บภาพใบหน้าที่ถ่ายตอน scan (snapshot)</p>
            </div>
            <StatusBadge :ok="info.storage.status === 'ok'" />
          </div>
          <template v-if="info.storage.status === 'ok'">
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <div class="text-base-content/40 text-xs mb-0.5">Path</div>
                <div class="font-mono text-xs break-all">{{ info.storage.path }}</div>
                <div class="text-xs text-base-content/40 mt-0.5">โฟลเดอร์เก็บข้อมูล</div>
              </div>
              <div>
                <div class="text-base-content/40 text-xs mb-0.5">Snapshots</div>
                <div class="font-bold text-lg">{{ info.storage.snapshots_count.toLocaleString() }}</div>
                <div class="text-xs text-base-content/40">{{ info.storage.snapshots_mb }} MB</div>
                <div class="text-xs text-base-content/40 mt-0.5">รูปภาพหลักฐานการลงเวลา</div>
              </div>
              <div>
                <div class="text-base-content/40 text-xs mb-0.5">Disk Free</div>
                <div class="font-bold text-lg" :class="diskWarnClass">{{ info.storage.disk_free_gb }} GB</div>
                <div class="text-xs text-base-content/40 mt-0.5">พื้นที่ว่างบน disk</div>
              </div>
              <div>
                <div class="text-base-content/40 text-xs mb-0.5">Disk Total</div>
                <div class="font-bold text-lg">{{ info.storage.disk_total_gb }} GB</div>
                <div class="text-xs text-base-content/40 mt-0.5">ขนาด disk ทั้งหมด</div>
              </div>
            </div>
            <!-- Disk warning -->
            <div v-if="diskWarnLevel === 'critical'"
                 class="text-xs text-error bg-error/5 rounded-lg px-2.5 py-1.5 leading-snug">
              🚨 พื้นที่ disk เหลือน้อยมาก (&lt; 5 GB) — สำรองข้อมูลและล้าง snapshot เก่าทันที<br>
              รัน: <code class="font-mono">bash scripts/backup.sh</code>
            </div>
            <div v-else-if="diskWarnLevel === 'warn'"
                 class="text-xs text-warning/70 bg-warning/5 rounded-lg px-2.5 py-1.5 leading-snug">
              ⚠️ พื้นที่ disk เหลือน้อย (&lt; 20 GB) — ควรวางแผน backup และล้างข้อมูลเก่า
            </div>
            <div v-else class="text-xs text-base-content/40 leading-snug">
              ℹ️ Snapshot คือภาพถ่ายใบหน้า ณ เวลาที่ลงเวลางาน — เก็บไว้เป็นหลักฐาน สามารถดูได้ที่หน้า Attendance Logs
            </div>
          </template>
          <div v-else class="text-xs text-error bg-error/5 rounded-lg p-2.5">
            ❌ ตรวจสอบ storage ไม่ได้: {{ info.storage.error }}
          </div>
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
import { ref, computed, onMounted } from 'vue'
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

// ── Uptime formatter ──────────────────────────────────────────────────────────
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

// ── ONNX provider helpers ─────────────────────────────────────────────────────
function onnxColor(provider) {
  if (provider?.includes('CUDA'))      return 'text-success font-semibold'
  if (provider?.includes('DirectML'))  return 'text-info font-semibold'
  if (provider?.includes('ROCm'))      return 'text-info font-semibold'
  return 'text-base-content/60'
}

function onnxBg(provider) {
  if (provider?.includes('CUDA'))     return 'text-success/70 bg-success/5'
  if (provider?.includes('DirectML')) return 'text-info/70 bg-info/5'
  if (provider?.includes('ROCm'))     return 'text-info/70 bg-info/5'
  return 'text-warning/70 bg-warning/5'
}

function onnxNote(provider) {
  if (provider?.includes('CUDA'))
    return '⚡ GPU (NVIDIA CUDA) — ประมวลผลใบหน้าเร็วมาก (~50ms/frame)'
  if (provider?.includes('DirectML'))
    return '⚡ GPU (DirectML) — ใช้ GPU ผ่าน Windows DirectX ML'
  if (provider?.includes('ROCm'))
    return '⚡ GPU (AMD ROCm) — ใช้ GPU ผ่าน ROCm'
  return '🐢 CPU Only — ระบบทำงานได้ แต่ช้ากว่า GPU (~300–500ms/frame) เหมาะสำหรับทดสอบ'
}

// ── Qdrant sync check ─────────────────────────────────────────────────────────
const qdrantSyncOk = computed(() => {
  if (!info.value) return true
  const qdrant = info.value.qdrant
  const pg     = info.value.postgres
  if (qdrant?.status !== 'ok' || pg?.status !== 'ok') return true  // can't compare
  return qdrant.points_count === pg.rows.face_templates
})

// ── Disk warning ──────────────────────────────────────────────────────────────
const diskWarnLevel = computed(() => {
  const free = info.value?.storage?.disk_free_gb
  if (free == null) return 'ok'
  if (free < 5)  return 'critical'
  if (free < 20) return 'warn'
  return 'ok'
})

const diskWarnClass = computed(() => {
  if (diskWarnLevel.value === 'critical') return 'text-error'
  if (diskWarnLevel.value === 'warn')     return 'text-warning'
  return ''
})
</script>

<!-- ── Sub-components (inline) ─────────────────────────────────────────────── -->
<script>
// Row: label + value pair (with optional tooltip hint)
export const Row = {
  props: ['label', 'value', 'mono', 'highlight', 'hint'],
  template: `
    <div class="flex items-baseline justify-between gap-2">
      <span class="text-base-content/40 shrink-0 flex items-center gap-1">
        {{ label }}
        <span v-if="hint"
              class="cursor-help text-base-content/30 hover:text-base-content/60 transition-colors"
              :title="hint">ⓘ</span>
      </span>
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
