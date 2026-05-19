<template>
  <div class="p-6 space-y-6 max-w-6xl mx-auto">

    <!-- Header -->
    <div class="flex items-center justify-between flex-wrap gap-3">
      <div>
        <h1 class="text-2xl font-bold">Dashboard</h1>
        <p class="text-sm text-base-content/40 mt-0.5">Real-time attendance overview — {{ todayLabel }}</p>
      </div>
      <button class="btn btn-primary btn-sm" @click="load" :class="{ loading: loading }">
        <svg v-if="!loading" xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        Refresh
      </button>
    </div>

    <!-- KPI cards -->
    <div v-if="kpi" class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="bg-base-100 border border-base-300 rounded-2xl p-5 flex flex-col gap-1">
        <span class="text-xs text-base-content/40 font-medium uppercase tracking-wide">Total</span>
        <span class="text-3xl font-bold">{{ kpi.today.total }}</span>
        <span class="text-xs text-base-content/40">employees with shift</span>
      </div>
      <div class="bg-success/10 border border-success/20 rounded-2xl p-5 flex flex-col gap-1">
        <span class="text-xs text-success/70 font-medium uppercase tracking-wide">Present</span>
        <span class="text-3xl font-bold text-success">{{ kpi.today.present }}</span>
        <span class="text-xs text-success/60">{{ kpi.today.present_pct }}%</span>
      </div>
      <div class="bg-warning/10 border border-warning/20 rounded-2xl p-5 flex flex-col gap-1">
        <span class="text-xs text-warning/70 font-medium uppercase tracking-wide">Late</span>
        <span class="text-3xl font-bold text-warning">{{ kpi.today.late }}</span>
        <span class="text-xs text-warning/60">{{ kpi.today.late_pct }}%</span>
      </div>
      <div class="bg-error/10 border border-error/20 rounded-2xl p-5 flex flex-col gap-1">
        <span class="text-xs text-error/70 font-medium uppercase tracking-wide">Absent</span>
        <span class="text-3xl font-bold text-error">{{ kpi.today.absent }}</span>
        <span class="text-xs text-error/60">{{ kpi.today.absent_pct }}%</span>
      </div>
    </div>

    <!-- Skeleton -->
    <div v-else-if="loading" class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div v-for="i in 4" :key="i" class="bg-base-200 rounded-2xl p-5 h-24 animate-pulse" />
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">

      <!-- Weekly trend chart -->
      <div class="bg-base-100 border border-base-300 rounded-2xl p-5 space-y-4">
        <h2 class="font-semibold text-sm">7-Day Check-in Trend</h2>
        <div v-if="kpi" class="flex items-end gap-1.5 h-32">
          <div
            v-for="day in kpi.weekly" :key="day.date"
            class="flex-1 flex flex-col items-center gap-1 h-full justify-end"
          >
            <span class="text-xs font-mono text-base-content/50">{{ day.count }}</span>
            <div
              class="w-full rounded-t-md bg-primary/70 transition-all"
              :style="{ height: barHeight(day.count) }"
              :title="`${day.date}: ${day.count}`"
            />
            <span class="text-xs text-base-content/40 rotate-0">{{ shortDate(day.date) }}</span>
          </div>
        </div>
        <div v-else-if="loading" class="h-32 bg-base-200 rounded-xl animate-pulse" />
      </div>

      <!-- By department -->
      <div class="bg-base-100 border border-base-300 rounded-2xl p-5 space-y-4">
        <h2 class="font-semibold text-sm">Today by Department</h2>
        <div v-if="kpi && kpi.by_dept.length > 0" class="space-y-2">
          <div
            v-for="d in kpi.by_dept" :key="d.dept"
            class="flex items-center gap-3"
          >
            <span class="text-sm w-32 truncate shrink-0">{{ d.dept }}</span>
            <div class="flex-1 bg-base-200 rounded-full h-2 overflow-hidden">
              <div
                class="h-2 rounded-full bg-primary transition-all"
                :style="{ width: deptBarWidth(d.count) }"
              />
            </div>
            <span class="text-sm font-mono w-6 text-right shrink-0">{{ d.count }}</span>
          </div>
        </div>
        <div v-else-if="kpi && kpi.by_dept.length === 0" class="text-sm text-base-content/40 py-4 text-center">
          No check-ins today
        </div>
        <div v-else-if="loading" class="space-y-2">
          <div v-for="i in 4" :key="i" class="h-5 bg-base-200 rounded animate-pulse" />
        </div>
      </div>

    </div>

    <!-- Error -->
    <div v-if="error" class="alert alert-error text-sm">{{ error }}</div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api/client'

const kpi     = ref(null)
const loading = ref(false)
const error   = ref('')

const todayLabel = computed(() => new Date().toLocaleDateString('th-TH', {
  weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
}))

async function load() {
  loading.value = true
  error.value   = ''
  try {
    const res = await api.get('/attendance/kpi')
    kpi.value = res.data
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Failed to load KPI data'
  } finally {
    loading.value = false
  }
}

const maxWeekly = computed(() => Math.max(1, ...((kpi.value?.weekly || []).map(d => d.count))))
const maxDept   = computed(() => Math.max(1, ...((kpi.value?.by_dept || []).map(d => d.count))))

function barHeight(count) {
  const pct = Math.max(4, Math.round((count / maxWeekly.value) * 100))
  return `${pct}%`
}

function deptBarWidth(count) {
  const pct = Math.max(2, Math.round((count / maxDept.value) * 100))
  return `${pct}%`
}

function shortDate(iso) {
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

onMounted(load)
</script>
