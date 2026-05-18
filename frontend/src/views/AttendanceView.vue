<template>
  <div class="flex flex-col gap-5">

    <!-- Header -->
    <div class="flex items-start justify-between gap-3">
      <div>
        <h1 class="text-xl font-bold tracking-wide">Attendance</h1>
        <p class="text-sm text-base-content/40 mt-0.5">Face recognition attendance records &amp; reports</p>
      </div>
      <button v-if="activeTab === 'logs'" class="btn btn-ghost btn-sm gap-2" @click="exportCSV">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        Export CSV
      </button>
      <button v-else-if="activeTab === 'summary'" class="btn btn-ghost btn-sm gap-2" @click="exportSummaryCSV">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        Export Report CSV
      </button>
      <button v-else class="btn btn-ghost btn-sm gap-2" @click="exportDailyCSV">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        Export Daily CSV
      </button>
    </div>

    <!-- Tabs -->
    <div role="tablist" class="tabs tabs-bordered">
      <button role="tab" class="tab" :class="{ 'tab-active': activeTab === 'logs' }" @click="activeTab = 'logs'">
        Logs
      </button>
      <button role="tab" class="tab" :class="{ 'tab-active': activeTab === 'summary' }" @click="activateReport">
        Monthly Report
      </button>
      <button role="tab" class="tab" :class="{ 'tab-active': activeTab === 'daily' }" @click="activateDaily">
        Daily Status
      </button>
    </div>

    <!-- ───── TAB: LOGS ────────────────────────────────────────────────────── -->
    <template v-if="activeTab === 'logs'">
      <DataTable
        :columns="columns"
        :rows="pageRows"
        :total="filteredLogs.length"
        :loading="loading"
        v-model:page="page"
        v-model:page-size="pageSize"
        v-model:search="search"
        :actions="[]"
        search-placeholder="Search name or code…"
        empty-text="No attendance records found"
      >
        <template #toolbar>
          <input v-model="filterDate" type="date" class="input input-bordered input-sm" @change="fetchLogs" />
          <select v-model="filterDept" class="select select-bordered select-sm" @change="fetchLogs">
            <option value="">All Departments</option>
            <option v-for="d in departments" :key="d.id" :value="d.id">{{ d.name }}</option>
          </select>
          <button class="btn btn-primary btn-sm" @click="fetchLogs">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2a1 1 0 01-.293.707L13 13.414V19a1 1 0 01-.553.894l-4 2A1 1 0 017 21v-7.586L3.293 6.707A1 1 0 013 6V4z"/>
            </svg>
            Filter
          </button>
        </template>

        <template #cell-timestamp="{ value }">
          <div class="flex flex-col">
            <span class="text-sm font-medium">{{ formatDate(value) }}</span>
            <span class="text-xs text-base-content/40">{{ formatTime(value) }}</span>
          </div>
        </template>
        <template #cell-full_name="{ row }">
          <div class="flex items-center gap-2">
            <!-- Face snapshot thumbnail — click to enlarge -->
            <div
              class="avatar shrink-0 cursor-pointer"
              :class="row.snapshot_url ? '' : 'placeholder'"
              @click="row.snapshot_url && openSnapshot(row)"
              :title="row.snapshot_url ? 'คลิกดูใบหน้าหลักฐาน' : 'ไม่มีภาพหลักฐาน'"
            >
              <div v-if="row.snapshot_url"
                class="w-8 h-8 rounded-full ring-1 ring-success/40 overflow-hidden bg-base-300">
                <SnapshotImg :url="row.snapshot_url" />
              </div>
              <div v-else class="bg-neutral text-neutral-content rounded-full w-8 h-8 flex items-center justify-center text-xs">
                <span>{{ (row.full_name || '?')[0] }}</span>
              </div>
            </div>
            <span class="font-medium text-sm">{{ row.full_name || '—' }}</span>
          </div>
        </template>
        <template #cell-confidence_score="{ value }">
          <span class="badge badge-sm font-mono"
            :class="value >= 0.85 ? 'badge-success' : value >= 0.72 ? 'badge-warning' : 'badge-error'">
            {{ (value * 100).toFixed(1) }}%
          </span>
        </template>
        <template #cell-station_name="{ value }">
          <span class="badge badge-ghost badge-sm">{{ value || '—' }}</span>
        </template>
      </DataTable>
    </template>

    <!-- ───── TAB: DAILY STATUS ──────────────────────────────────────────── -->
    <template v-else-if="activeTab === 'daily'">

      <!-- Filters -->
      <div class="flex gap-2 flex-wrap items-end">
        <div class="form-control">
          <label class="label py-1"><span class="label-text text-xs">Date</span></label>
          <input v-model="dailyDate" type="date" class="input input-bordered input-sm" />
        </div>
        <div class="form-control">
          <label class="label py-1"><span class="label-text text-xs">Department</span></label>
          <select v-model="dailyDept" class="select select-bordered select-sm">
            <option value="">All Departments</option>
            <option v-for="d in departments" :key="d.id" :value="d.id">{{ d.name }}</option>
          </select>
        </div>
        <button class="btn btn-primary btn-sm self-end" @click="fetchDaily" :class="{ loading: dailyLoading }">
          Apply
        </button>
      </div>

      <!-- KPI cards -->
      <div v-if="dailyReport" class="stats bg-base-100 border border-base-300 shadow-sm w-full">
        <div class="stat py-3">
          <div class="stat-title text-xs">Total Employees</div>
          <div class="stat-value text-2xl">{{ dailyReport.summary.total }}</div>
          <div class="stat-desc">with shift assigned</div>
        </div>
        <div class="stat py-3">
          <div class="stat-title text-xs">Present</div>
          <div class="stat-value text-2xl text-success">{{ dailyReport.summary.present }}</div>
          <div class="stat-desc">on time</div>
        </div>
        <div class="stat py-3">
          <div class="stat-title text-xs">Late</div>
          <div class="stat-value text-2xl text-warning">{{ dailyReport.summary.late }}</div>
          <div class="stat-desc">&gt; {{ dailyReport.late_threshold_minutes }} min after shift</div>
        </div>
        <div class="stat py-3">
          <div class="stat-title text-xs">Absent</div>
          <div class="stat-value text-2xl text-error">{{ dailyReport.summary.absent }}</div>
          <div class="stat-desc">no check-in</div>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="dailyLoading" class="flex justify-center py-12">
        <span class="loading loading-spinner loading-lg text-primary"></span>
      </div>

      <!-- Table -->
      <div v-else-if="dailyReport" class="overflow-x-auto bg-base-100 rounded-xl border border-base-300">
        <table class="table table-sm">
          <thead>
            <tr class="text-xs text-base-content/50">
              <th>Status</th>
              <th>Employee</th>
              <th>Code</th>
              <th>Department</th>
              <th>Shift</th>
              <th>Check-in</th>
              <th>Late (min)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in dailyReport.records" :key="r.employee_id"
              class="hover:bg-base-200/50 transition-colors">
              <td>
                <span class="badge badge-sm font-semibold"
                  :class="{
                    'badge-success':  r.status === 'PRESENT',
                    'badge-warning':  r.status === 'LATE',
                    'badge-error':    r.status === 'ABSENT',
                  }">
                  {{ r.status }}
                </span>
              </td>
              <td class="font-medium text-sm">{{ r.full_name }}</td>
              <td class="font-mono text-xs text-base-content/60">{{ r.emp_code }}</td>
              <td class="text-sm text-base-content/70">{{ r.dept_name || '—' }}</td>
              <td>
                <div class="flex flex-col text-xs">
                  <span class="font-medium">{{ r.shift_name }}</span>
                  <span class="text-base-content/40">{{ r.shift_start }} – {{ r.shift_end }}</span>
                </div>
              </td>
              <td class="font-mono text-xs">
                {{ r.check_in_time ? formatTime(r.check_in_time) : '—' }}
              </td>
              <td class="text-center">
                <span v-if="r.status === 'LATE'" class="font-mono text-warning font-semibold text-sm">
                  +{{ r.minutes_late }}
                </span>
                <span v-else-if="r.status === 'ABSENT'" class="text-base-content/30 text-sm">—</span>
                <span v-else class="text-success text-sm">—</span>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="dailyReport.records.length === 0"
          class="py-12 text-center text-sm text-base-content/30">
          No employees with shift assigned found
        </div>
      </div>

      <div v-else-if="!dailyLoading" class="py-8 text-center text-sm text-base-content/30">
        Select a date and click Apply to load the daily status report
      </div>
    </template>

    <!-- ───── TAB: SUMMARY ────────────────────────────────────────────────── -->
    <template v-else-if="activeTab === 'summary'">

      <!-- Filters row -->
      <div class="flex gap-2 flex-wrap items-end">
        <div class="form-control">
          <label class="label py-1"><span class="label-text text-xs">Month</span></label>
          <input v-model="summaryMonth" type="month" class="input input-bordered input-sm"
            @change="fetchSummary" />
        </div>
        <div class="form-control">
          <label class="label py-1"><span class="label-text text-xs">Department</span></label>
          <select v-model="summaryDept" class="select select-bordered select-sm" @change="fetchSummary">
            <option value="">All Departments</option>
            <option v-for="d in departments" :key="d.id" :value="d.id">{{ d.name }}</option>
          </select>
        </div>
        <button class="btn btn-primary btn-sm self-end" @click="fetchSummary"
          :class="{ loading: summaryLoading }">
          Apply
        </button>
      </div>

      <!-- Summary KPI cards -->
      <div v-if="summary" class="stats bg-base-100 border border-base-300 shadow-sm w-full">
        <div class="stat py-3">
          <div class="stat-title text-xs">Total Scans</div>
          <div class="stat-value text-2xl">{{ summary.total_records }}</div>
          <div class="stat-desc">for {{ summary.month }}</div>
        </div>
        <div class="stat py-3">
          <div class="stat-title text-xs">Unique Employees</div>
          <div class="stat-value text-2xl text-primary">{{ summary.unique_employees }}</div>
          <div class="stat-desc">different people</div>
        </div>
        <div class="stat py-3">
          <div class="stat-title text-xs">Active Days</div>
          <div class="stat-value text-2xl text-success">{{ activeDays }}</div>
          <div class="stat-desc">days with attendance</div>
        </div>
        <div class="stat py-3">
          <div class="stat-title text-xs">Avg / Day</div>
          <div class="stat-value text-2xl">{{ avgPerDay }}</div>
          <div class="stat-desc">scans per active day</div>
        </div>
      </div>

      <!-- Loading spinner -->
      <div v-if="summaryLoading" class="flex justify-center py-12">
        <span class="loading loading-spinner loading-lg text-primary"></span>
      </div>

      <div v-else-if="summary" class="grid grid-cols-1 xl:grid-cols-3 gap-5">

        <!-- Daily bar chart (2/3 width) -->
        <div class="xl:col-span-2 bg-base-100 rounded-xl border border-base-300 p-5">
          <div class="text-sm font-semibold mb-4 text-base-content/70">Daily Attendance — {{ summary.month }}</div>
          <div class="flex items-end gap-0.5 h-36" v-if="dayMax > 0">
            <div
              v-for="day in summary.by_day" :key="day.date"
              class="flex-1 flex flex-col items-center gap-0.5 group relative"
            >
              <!-- Bar -->
              <div
                class="w-full rounded-sm transition-all duration-200"
                :class="day.count > 0 ? 'bg-primary/70 hover:bg-primary' : 'bg-base-300/30'"
                :style="{ height: day.count > 0 ? Math.max(4, (day.count / dayMax) * 128) + 'px' : '2px' }"
              ></div>
              <!-- Day number every 5th -->
              <div v-if="Number(day.date.slice(8)) % 5 === 0 || Number(day.date.slice(8)) === 1"
                class="text-[9px] text-base-content/30 leading-none">
                {{ Number(day.date.slice(8)) }}
              </div>
              <div v-else class="text-[9px] leading-none invisible">·</div>
              <!-- Tooltip -->
              <div class="absolute bottom-full mb-1 left-1/2 -translate-x-1/2
                          hidden group-hover:flex flex-col items-center
                          bg-base-content text-base-100 text-[10px] rounded px-1.5 py-1 whitespace-nowrap z-10 shadow">
                {{ day.date.slice(8) }} {{ monthName }} — {{ day.count }} scans / {{ day.unique_employees }} ppl
                <div class="absolute top-full border-4 border-transparent border-t-base-content"></div>
              </div>
            </div>
          </div>
          <div v-else class="flex items-center justify-center h-36 text-base-content/25 text-sm">
            No attendance data for this month
          </div>
        </div>

        <!-- Dept breakdown (1/3 width) -->
        <div class="bg-base-100 rounded-xl border border-base-300 p-5">
          <div class="text-sm font-semibold mb-4 text-base-content/70">By Department</div>
          <div v-if="summary.by_department.length === 0"
            class="flex items-center justify-center h-24 text-base-content/25 text-xs">
            No data
          </div>
          <div v-else class="flex flex-col gap-2.5">
            <div v-for="dept in summary.by_department" :key="dept.dept_id" class="flex flex-col gap-1">
              <div class="flex justify-between items-center text-xs">
                <span class="font-medium truncate">{{ dept.dept_name }}</span>
                <span class="text-base-content/40 font-mono shrink-0 ml-2">{{ dept.count }}</span>
              </div>
              <div class="w-full h-1.5 bg-base-300 rounded-full overflow-hidden">
                <div class="h-full bg-primary/60 rounded-full"
                  :style="{ width: Math.max(4, (dept.count / summary.total_records) * 100).toFixed(1) + '%' }">
                </div>
              </div>
              <div class="text-[10px] text-base-content/30">{{ dept.unique_employees }} unique employees</div>
            </div>
          </div>
        </div>

      </div>
    </template>

  </div>

  <!-- ── Face Snapshot Modal ──────────────────────────────────────────────── -->
  <dialog ref="snapshotModal" class="modal modal-bottom sm:modal-middle">
    <div class="modal-box max-w-sm p-5" v-if="snapshotRow">
      <div class="flex items-center justify-between mb-3">
        <div>
          <div class="font-bold">{{ snapshotRow.full_name }}</div>
          <div class="text-xs text-base-content/40 mt-0.5">
            {{ formatDate(snapshotRow.timestamp) }} {{ formatTime(snapshotRow.timestamp) }}
            · {{ snapshotRow.station_name }}
          </div>
        </div>
        <button class="btn btn-ghost btn-sm btn-circle" @click="snapshotModal.close()">✕</button>
      </div>

      <!-- Snapshot image -->
      <div class="rounded-xl overflow-hidden bg-base-300 aspect-square flex items-center justify-center">
        <img v-if="snapshotBlobUrl" :src="snapshotBlobUrl"
          class="w-full h-full object-contain" alt="Face evidence" />
        <span v-else class="loading loading-spinner loading-lg text-base-content/30"></span>
      </div>

      <!-- Metadata -->
      <div class="flex items-center justify-between mt-3 text-xs text-base-content/50">
        <span class="font-mono">{{ snapshotRow.emp_code }}</span>
        <span class="badge badge-sm font-mono"
          :class="snapshotRow.confidence_score >= 0.85 ? 'badge-success'
                : snapshotRow.confidence_score >= 0.72 ? 'badge-warning' : 'badge-error'">
          {{ (snapshotRow.confidence_score * 100).toFixed(1) }}% confidence
        </span>
      </div>
    </div>
    <form method="dialog" class="modal-backdrop"><button>close</button></form>
  </dialog>
</template>

<script setup>
import { ref, computed, onMounted, defineComponent, h } from 'vue'
import api from '@/api/client'
import { useToast } from '@/composables/useToast'
import DataTable from '@/components/DataTable.vue'

const toast = useToast()

// ── SnapshotImg — lazy-load face thumbnail with auth header ───────────────────
// <img src="..."> ไม่ส่ง Authorization header ดังนั้น fetch เองแล้วสร้าง blob URL
const SnapshotImg = defineComponent({
  props: { url: String },
  setup(props) {
    const blobUrl = ref(null)
    api.get(props.url, { responseType: 'blob' })
      .then(res => { blobUrl.value = URL.createObjectURL(res.data) })
      .catch(() => {})
    return () => blobUrl.value
      ? h('img', { src: blobUrl.value, class: 'w-full h-full object-cover' })
      : h('div', { class: 'w-full h-full bg-base-300' })
  },
})

// ── Shared ────────────────────────────────────────────────────────────────────
const departments = ref([])
const activeTab   = ref('logs')

// ── Logs tab ──────────────────────────────────────────────────────────────────
const logs      = ref([])
const loading   = ref(false)
const page      = ref(1)
const pageSize  = ref(25)
const search    = ref('')
const filterDate = ref(new Date().toISOString().slice(0, 10))
const filterDept = ref('')

const columns = [
  { key: 'timestamp',        label: 'Time' },
  { key: 'full_name',        label: 'Employee' },
  { key: 'emp_code',         label: 'Code',       class: 'font-mono text-sm', hideMobile: true },
  { key: 'station_name',     label: 'Station',    hideMobile: true },
  { key: 'confidence_score', label: 'Confidence' },
]

// ── Snapshot modal ─────────────────────────────────────────────────────────────
const snapshotModal  = ref(null)
const snapshotRow    = ref(null)
const snapshotBlobUrl = ref(null)

async function openSnapshot(row) {
  snapshotRow.value    = row
  snapshotBlobUrl.value = null
  snapshotModal.value.showModal()
  try {
    const res = await api.get(row.snapshot_url, { responseType: 'blob' })
    snapshotBlobUrl.value = URL.createObjectURL(res.data)
  } catch {
    toast.error('ไม่สามารถโหลดภาพหลักฐานได้')
  }
}

const filteredLogs = computed(() => {
  const q = search.value.toLowerCase().trim()
  if (!q) return logs.value
  return logs.value.filter(l =>
    (l.full_name || '').toLowerCase().includes(q) ||
    (l.emp_code  || '').toLowerCase().includes(q)
  )
})

const pageRows = computed(() => {
  const from = (page.value - 1) * pageSize.value
  return filteredLogs.value.slice(from, from + pageSize.value)
})

function formatDate(dt) {
  return new Date(dt).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}
function formatTime(dt) {
  return new Date(dt).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

async function fetchLogs() {
  loading.value = true
  page.value = 1
  try {
    const params = {}
    if (filterDate.value) params.date    = filterDate.value
    if (filterDept.value) params.dept_id = filterDept.value
    const { data } = await api.get('/api/v1/attendance', { params })
    logs.value = data
  } catch {
    toast.error('Failed to load attendance logs')
  } finally {
    loading.value = false
  }
}

function exportCSV() {
  if (!filteredLogs.value.length) { toast.warning('No records to export'); return }
  const header = ['Timestamp', 'Employee', 'Code', 'Department', 'Station', 'Confidence']
  const rows = filteredLogs.value.map(l => [
    new Date(l.timestamp).toLocaleString(),
    l.full_name    || '',
    l.emp_code     || '',
    l.dept_name    || '',
    l.station_name || '',
    (l.confidence_score * 100).toFixed(1) + '%',
  ])
  downloadCSV([header, ...rows], `attendance_${filterDate.value || 'all'}.csv`)
  toast.success('CSV exported')
}

// ── Summary tab ───────────────────────────────────────────────────────────────
const summary        = ref(null)
const summaryLoading = ref(false)
const summaryMonth   = ref(new Date().toISOString().slice(0, 7))
const summaryDept    = ref('')

const activeDays = computed(() =>
  summary.value ? summary.value.by_day.filter(d => d.count > 0).length : 0
)
const avgPerDay = computed(() => {
  if (!summary.value || activeDays.value === 0) return 0
  return (summary.value.total_records / activeDays.value).toFixed(1)
})
const dayMax = computed(() =>
  summary.value ? Math.max(...summary.value.by_day.map(d => d.count), 1) : 1
)
const monthName = computed(() => {
  if (!summaryMonth.value) return ''
  const [y, m] = summaryMonth.value.split('-')
  return new Date(y, m - 1, 1).toLocaleString(undefined, { month: 'short', year: 'numeric' })
})

function activateReport() {
  activeTab.value = 'summary'
  if (!summary.value) fetchSummary()
}

async function fetchSummary() {
  summaryLoading.value = true
  try {
    const params = { month: summaryMonth.value }
    if (summaryDept.value) params.dept_id = summaryDept.value
    const { data } = await api.get('/api/v1/attendance/summary', { params })
    summary.value = data
  } catch {
    toast.error('Failed to load attendance summary')
  } finally {
    summaryLoading.value = false
  }
}

function exportSummaryCSV() {
  if (!summary.value) { toast.warning('Load summary first'); return }
  const header = ['Date', 'Total Scans', 'Unique Employees']
  const rows = summary.value.by_day.map(d => [d.date, d.count, d.unique_employees])
  downloadCSV([header, ...rows], `attendance_summary_${summary.value.month}.csv`)
  toast.success('Summary CSV exported')
}

// ── Daily Status tab ─────────────────────────────────────────────────────────
const dailyReport  = ref(null)
const dailyLoading = ref(false)
const dailyDate    = ref(new Date().toISOString().slice(0, 10))
const dailyDept    = ref('')

function activateDaily() {
  activeTab.value = 'daily'
}

async function fetchDaily() {
  dailyLoading.value = true
  try {
    const params = { date: dailyDate.value }
    if (dailyDept.value) params.dept_id = dailyDept.value
    const { data } = await api.get('/api/v1/attendance/daily-report', { params })
    dailyReport.value = data
  } catch {
    toast.error('Failed to load daily status report')
  } finally {
    dailyLoading.value = false
  }
}

function exportDailyCSV() {
  if (!dailyReport.value?.records?.length) { toast.warning('No records to export'); return }
  const header = ['Status', 'Employee', 'Code', 'Department', 'Shift', 'Shift Start', 'Check-in', 'Minutes Late']
  const rows = dailyReport.value.records.map(r => [
    r.status,
    r.full_name,
    r.emp_code,
    r.dept_name || '',
    r.shift_name,
    r.shift_start,
    r.check_in_time ? formatTime(r.check_in_time) : '',
    r.minutes_late ?? '',
  ])
  downloadCSV([header, ...rows], `daily_status_${dailyDate.value}.csv`)
  toast.success('Daily CSV exported')
}

// ── Shared helpers ────────────────────────────────────────────────────────────
function downloadCSV(rows, filename) {
  const csv  = rows.map(r => r.map(v => `"${v}"`).join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

onMounted(async () => {
  const { data } = await api.get('/api/v1/departments')
  departments.value = data
  await fetchLogs()
})
</script>
