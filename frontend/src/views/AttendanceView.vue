<template>
  <div class="flex flex-col gap-5">

    <div class="flex items-start justify-between gap-3">
      <div>
        <h1 class="text-xl font-bold tracking-wide">Attendance Logs</h1>
        <p class="text-sm text-base-content/40 mt-0.5">Face recognition attendance records</p>
      </div>
      <!-- CSV export placeholder -->
      <button class="btn btn-ghost btn-sm gap-2" @click="exportCSV">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        Export CSV
      </button>
    </div>

    <DataTable
      :columns="columns"
      :rows="pageRows"
      :total="logs.length"
      :loading="loading"
      v-model:page="page"
      v-model:page-size="pageSize"
      v-model:search="search"
      :actions="[]"
      search-placeholder="Search name or code…"
      empty-text="No attendance records found"
    >
      <!-- Extra toolbar: date + department filters -->
      <template #toolbar>
        <input
          v-model="filterDate"
          type="date"
          class="input input-bordered input-sm"
          @change="fetchLogs"
        />
        <select v-model="filterDept" class="select select-bordered select-sm" @change="fetchLogs">
          <option value="">All Departments</option>
          <option v-for="d in departments" :key="d.id" :value="d.id">{{ d.name }}</option>
        </select>
        <button class="btn btn-primary btn-sm" @click="fetchLogs">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2a1 1 0 01-.293.707L13 13.414V19a1 1 0 01-.553.894l-4 2A1 1 0 017 21v-7.586L3.293 6.707A1 1 0 013 6V4z" />
          </svg>
          Filter
        </button>
      </template>

      <!-- Custom cells -->
      <template #cell-timestamp="{ value }">
        <div class="flex flex-col">
          <span class="text-sm font-medium">{{ formatDate(value) }}</span>
          <span class="text-xs text-base-content/40">{{ formatTime(value) }}</span>
        </div>
      </template>

      <template #cell-full_name="{ row }">
        <div class="flex items-center gap-2">
          <div class="avatar placeholder">
            <div class="bg-neutral text-neutral-content rounded-full w-6 text-xs">
              <span>{{ (row.full_name || '?')[0] }}</span>
            </div>
          </div>
          <span class="font-medium text-sm">{{ row.full_name || '—' }}</span>
        </div>
      </template>

      <template #cell-confidence_score="{ value }">
        <span
          class="badge badge-sm font-mono"
          :class="value >= 0.85 ? 'badge-success' : value >= 0.72 ? 'badge-warning' : 'badge-error'"
        >
          {{ (value * 100).toFixed(1) }}%
        </span>
      </template>

      <template #cell-station_name="{ value }">
        <span class="badge badge-ghost badge-sm">{{ value || '—' }}</span>
      </template>
    </DataTable>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api/client'
import { useToast } from '@/composables/useToast'
import DataTable from '@/components/DataTable.vue'

const toast = useToast()

const logs        = ref([])
const departments = ref([])
const loading     = ref(false)

const page       = ref(1)
const pageSize   = ref(25)
const search     = ref('')
const filterDate = ref(new Date().toISOString().slice(0, 10))
const filterDept = ref('')

const columns = [
  { key: 'timestamp',        label: 'Time' },
  { key: 'full_name',        label: 'Employee' },
  { key: 'emp_code',         label: 'Code',       class: 'font-mono text-sm', hideMobile: true },
  { key: 'station_name',     label: 'Station',    hideMobile: true },
  { key: 'confidence_score', label: 'Confidence' },
]

// Client-side search filter (date/dept filters hit the API)
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
    if (filterDate.value) params.date     = filterDate.value
    if (filterDept.value) params.dept_id  = filterDept.value
    const { data } = await api.get('/api/v1/attendance', { params })
    logs.value = data
  } catch (e) {
    toast.error('Failed to load attendance logs')
  } finally {
    loading.value = false
  }
}

function exportCSV() {
  if (!filteredLogs.value.length) {
    toast.warning('No records to export')
    return
  }
  const header = ['Timestamp', 'Employee', 'Code', 'Station', 'Confidence']
  const rows = filteredLogs.value.map(l => [
    new Date(l.timestamp).toLocaleString(),
    l.full_name || '',
    l.emp_code  || '',
    l.station_name || '',
    (l.confidence_score * 100).toFixed(1) + '%',
  ])
  const csv = [header, ...rows].map(r => r.map(v => `"${v}"`).join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href     = url
  a.download = `attendance_${filterDate.value || 'all'}.csv`
  a.click()
  URL.revokeObjectURL(url)
  toast.success('CSV exported')
}

onMounted(async () => {
  const { data } = await api.get('/api/v1/departments')
  departments.value = data
  await fetchLogs()
})
</script>
