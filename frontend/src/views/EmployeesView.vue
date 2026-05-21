<template>
  <div class="flex flex-col gap-5">

    <div class="flex items-start justify-between gap-3">
      <div>
        <h1 class="text-xl font-bold tracking-wide">Employees</h1>
        <p class="text-sm text-base-content/40 mt-0.5">Manage employees and face enrollment</p>
      </div>
      <button class="btn btn-primary btn-sm gap-2" @click="openCreate">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        Add Employee
      </button>
    </div>

    <DataTable
      :columns="columns"
      :rows="employees"
      :total="total"
      :loading="loading"
      v-model:page="page"
      v-model:page-size="pageSize"
      v-model:search="search"
      :actions="actions"
      search-placeholder="Search name or code…"
      empty-text="No employees match your search"
    >
      <!-- Extra toolbar: department filter -->
      <template #toolbar>
        <select v-model="filterDept" class="select select-bordered select-sm">
          <option value="">All Departments</option>
          <option v-for="d in departments" :key="d.id" :value="d.id">{{ d.name }}</option>
        </select>
      </template>

      <!-- Custom cells -->
      <template #cell-full_name="{ row }">
        <div class="flex items-center gap-2">
          <div class="avatar placeholder">
            <div class="bg-neutral text-neutral-content rounded-full w-7 text-xs">
              <span>{{ row.full_name[0] }}</span>
            </div>
          </div>
          <span class="font-medium">{{ row.full_name }}</span>
        </div>
      </template>

      <template #cell-dept_id="{ row }">
        <span class="badge badge-ghost badge-sm">{{ deptName(row.dept_id) }}</span>
      </template>

      <template #cell-enrollment_count="{ row }">
        <div class="flex items-center gap-1.5">
          <div class="flex gap-0.5">
            <div
              v-for="i in 6" :key="i"
              class="w-2.5 h-2.5 rounded-sm"
              :class="i <= row.enrollment_count ? 'bg-success' : 'bg-base-300'"
            />
          </div>
          <span class="text-xs text-base-content/40">{{ row.enrollment_count }}/6</span>
        </div>
      </template>

      <template #cell-is_active="{ row }">
        <div class="flex items-center gap-1.5">
          <div class="w-1.5 h-1.5 rounded-full" :class="row.is_active ? 'bg-success' : 'bg-base-300'"></div>
          <span class="text-xs" :class="row.is_active ? 'text-success' : 'text-base-content/30'">
            {{ row.is_active ? 'Active' : 'Inactive' }}
          </span>
        </div>
      </template>
    </DataTable>

    <!-- Create modal -->
    <dialog ref="modal" class="modal modal-bottom sm:modal-middle">
      <div class="modal-box max-w-md">
        <div class="flex items-center justify-between mb-5">
          <h3 class="font-bold text-lg">Add Employee</h3>
          <button class="btn btn-ghost btn-sm btn-circle" @click="modal.close()">✕</button>
        </div>
        <form @submit.prevent="createEmployee" class="flex flex-col gap-3">
          <label class="form-control">
            <div class="label py-1"><span class="label-text text-xs font-medium uppercase tracking-wider opacity-60">Employee Code *</span></div>
            <input v-model="form.emp_code" class="input input-bordered" required placeholder="e.g. EMP001" />
          </label>
          <label class="form-control">
            <div class="label py-1"><span class="label-text text-xs font-medium uppercase tracking-wider opacity-60">Full Name *</span></div>
            <input v-model="form.full_name" class="input input-bordered" required placeholder="First Last" />
          </label>
          <label class="form-control">
            <div class="label py-1"><span class="label-text text-xs font-medium uppercase tracking-wider opacity-60">Department *</span></div>
            <select v-model="form.dept_id" class="select select-bordered" required>
              <option value="" disabled>Select department…</option>
              <option v-for="d in departments" :key="d.id" :value="d.id">{{ d.name }}</option>
            </select>
          </label>
          <div class="modal-action mt-2">
            <button type="button" class="btn btn-ghost" @click="modal.close()">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              <span v-if="saving" class="loading loading-spinner loading-sm"></span>
              Create
            </button>
          </div>
        </form>
      </div>
      <form method="dialog" class="modal-backdrop"><button>close</button></form>
    </dialog>

  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'
import { useToast } from '@/composables/useToast'
import DataTable from '@/components/DataTable.vue'

const router = useRouter()
const toast  = useToast()

const employees   = ref([])
const departments = ref([])
const total       = ref(0)
const loading     = ref(false)
const saving      = ref(false)
const modal       = ref(null)
const form        = ref({ emp_code: '', full_name: '', dept_id: '' })

// Table state
const page       = ref(1)
const pageSize   = ref(25)
const search     = ref('')
const filterDept = ref('')

const columns = [
  { key: 'emp_code',         label: 'Code',       class: 'font-mono text-sm', hideMobile: false },
  { key: 'full_name',        label: 'Name' },
  { key: 'dept_id',          label: 'Department',  hideMobile: true },
  { key: 'enrollment_count', label: 'Enrollment' },
  { key: 'is_active',        label: 'Status',      hideMobile: true },
]

const actions = [
  {
    label: 'Enroll Face',
    handler: (row) => router.push(`/employees/${row.id}/enroll`),
  },
]

function deptName(id) {
  return departments.value.find(d => d.id === id)?.name || '—'
}

function openCreate() {
  form.value = { emp_code: '', full_name: '', dept_id: departments.value[0]?.id || '' }
  modal.value.showModal()
}

async function createEmployee() {
  saving.value = true
  try {
    await api.post('/api/v1/employees', form.value)
    modal.value.close()
    toast.success(`Employee "${form.value.full_name}" added`)
    page.value = 1
    await loadEmployees()
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Failed to create employee')
  } finally {
    saving.value = false
  }
}

async function load() {
  await Promise.all([
    loadEmployees(),
    loadDepartments(),
  ])
}

async function loadEmployees() {
  loading.value = true
  try {
    const params = {
      page: page.value,
      page_size: pageSize.value,
    }
    const q = search.value.trim()
    if (q) params.search = q
    if (filterDept.value) params.dept_id = filterDept.value

    const { data } = await api.get('/api/v1/employees/page', { params })
    employees.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function loadDepartments() {
  const { data } = await api.get('/api/v1/departments')
  departments.value = data
}

watch([page, pageSize, search], loadEmployees)

watch(filterDept, () => {
  page.value = 1
  loadEmployees()
})

onMounted(load)
</script>
