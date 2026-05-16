<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold">Employees</h1>
      <button class="btn btn-primary btn-sm" @click="openCreate">+ Add Employee</button>
    </div>

    <div class="flex gap-2">
      <input v-model="search" type="text" placeholder="Search by name or code..." class="input input-bordered input-sm flex-1 max-w-sm" />
      <select v-model="filterDept" class="select select-bordered select-sm">
        <option value="">All Departments</option>
        <option v-for="d in departments" :key="d.id" :value="d.id">{{ d.name }}</option>
      </select>
    </div>

    <div class="overflow-x-auto">
      <table class="table table-sm">
        <thead>
          <tr>
            <th>Code</th>
            <th>Name</th>
            <th>Department</th>
            <th>Enrollment</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="emp in filtered" :key="emp.id">
            <td class="font-mono text-sm">{{ emp.emp_code }}</td>
            <td>{{ emp.full_name }}</td>
            <td>{{ deptName(emp.dept_id) }}</td>
            <td>
              <div class="flex gap-0.5">
                <div
                  v-for="i in 6" :key="i"
                  class="w-3 h-3 rounded-sm"
                  :class="i <= emp.enrollment_count ? 'bg-success' : 'bg-base-300'"
                />
              </div>
            </td>
            <td>
              <span class="badge badge-sm" :class="emp.is_active ? 'badge-success' : 'badge-ghost'">
                {{ emp.is_active ? 'Active' : 'Inactive' }}
              </span>
            </td>
            <td>
              <RouterLink :to="`/employees/${emp.id}/enroll`" class="btn btn-ghost btn-xs">Enroll</RouterLink>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create modal -->
    <dialog ref="modal" class="modal">
      <div class="modal-box">
        <h3 class="font-bold text-lg mb-4">Add Employee</h3>
        <form @submit.prevent="createEmployee">
          <div class="form-control mb-3">
            <label class="label"><span class="label-text">Employee Code</span></label>
            <input v-model="form.emp_code" class="input input-bordered" required />
          </div>
          <div class="form-control mb-3">
            <label class="label"><span class="label-text">Full Name</span></label>
            <input v-model="form.full_name" class="input input-bordered" required />
          </div>
          <div class="form-control mb-6">
            <label class="label"><span class="label-text">Department</span></label>
            <select v-model="form.dept_id" class="select select-bordered" required>
              <option v-for="d in departments" :key="d.id" :value="d.id">{{ d.name }}</option>
            </select>
          </div>
          <div class="modal-action">
            <button type="button" class="btn btn-ghost" @click="modal.close()">Cancel</button>
            <button type="submit" class="btn btn-primary">Create</button>
          </div>
        </form>
      </div>
      <form method="dialog" class="modal-backdrop"><button>close</button></form>
    </dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api/client'

const employees = ref([])
const departments = ref([])
const search = ref('')
const filterDept = ref('')
const modal = ref(null)
const form = ref({ emp_code: '', full_name: '', dept_id: '' })

const filtered = computed(() =>
  employees.value.filter((e) => {
    const matchSearch = !search.value ||
      e.full_name.toLowerCase().includes(search.value.toLowerCase()) ||
      e.emp_code.toLowerCase().includes(search.value.toLowerCase())
    const matchDept = !filterDept.value || e.dept_id === filterDept.value
    return matchSearch && matchDept
  })
)

function deptName(id) {
  return departments.value.find((d) => d.id === id)?.name || '-'
}

function openCreate() {
  form.value = { emp_code: '', full_name: '', dept_id: departments.value[0]?.id || '' }
  modal.value.showModal()
}

async function createEmployee() {
  await api.post('/api/v1/employees', form.value)
  modal.value.close()
  await load()
}

async function load() {
  const [empRes, deptRes] = await Promise.all([
    api.get('/api/v1/employees'),
    api.get('/api/v1/departments'),
  ])
  employees.value = empRes.data
  departments.value = deptRes.data
}

onMounted(load)
</script>
