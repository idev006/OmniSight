<template>
  <div class="flex flex-col gap-4">
    <h1 class="text-2xl font-bold">Attendance Logs</h1>

    <div class="flex gap-2 flex-wrap">
      <input v-model="filters.date" type="date" class="input input-bordered input-sm" />
      <select v-model="filters.dept_id" class="select select-bordered select-sm">
        <option value="">All Departments</option>
        <option v-for="d in departments" :key="d.id" :value="d.id">{{ d.name }}</option>
      </select>
      <button class="btn btn-primary btn-sm" @click="load">Search</button>
    </div>

    <div class="overflow-x-auto">
      <table class="table table-sm">
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Employee</th>
            <th>Code</th>
            <th>Station</th>
            <th>Confidence</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in logs" :key="log.id">
            <td class="text-sm">{{ formatDT(log.timestamp) }}</td>
            <td>{{ log.full_name || '—' }}</td>
            <td class="font-mono text-sm">{{ log.emp_code || '—' }}</td>
            <td>{{ log.station_name || '—' }}</td>
            <td>
              <span class="badge badge-sm" :class="log.confidence_score >= 0.85 ? 'badge-success' : 'badge-warning'">
                {{ (log.confidence_score * 100).toFixed(1) }}%
              </span>
            </td>
          </tr>
          <tr v-if="!logs.length">
            <td colspan="5" class="text-center text-base-content/40 py-8">No records found</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api/client'

const logs = ref([])
const departments = ref([])
const filters = ref({ date: new Date().toISOString().slice(0, 10), dept_id: '' })

function formatDT(dt) {
  return new Date(dt).toLocaleString()
}

async function load() {
  const params = {}
  if (filters.value.date) params.date = filters.value.date
  if (filters.value.dept_id) params.dept_id = filters.value.dept_id
  const { data } = await api.get('/api/v1/attendance', { params })
  logs.value = data
}

onMounted(async () => {
  const { data } = await api.get('/api/v1/departments')
  departments.value = data
  await load()
})
</script>
