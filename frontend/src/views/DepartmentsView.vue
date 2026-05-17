<template>
  <div class="flex flex-col gap-5">

    <!-- Header -->
    <div class="flex items-start justify-between gap-3">
      <div>
        <h1 class="text-xl font-bold tracking-wide">Departments</h1>
        <p class="text-sm text-base-content/40 mt-0.5">Organisational units for employee grouping</p>
      </div>
      <button class="btn btn-primary btn-sm gap-2" @click="openCreate">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        Add Department
      </button>
    </div>

    <!-- DataTable -->
    <DataTable
      :columns="columns"
      :rows="pageRows"
      :total="filtered.length"
      :loading="loading"
      v-model:page="page"
      v-model:page-size="pageSize"
      v-model:search="search"
      :actions="actions"
      :page-sizes="[10, 25, 50]"
      search-placeholder="Search department name…"
      empty-text="No departments found"
    >
      <template #cell-name="{ value }">
        <span class="font-medium">{{ value }}</span>
      </template>

      <template #cell-id="{ value }">
        <span class="font-mono text-xs text-base-content/40">{{ value }}</span>
      </template>
    </DataTable>

    <!-- Create Modal -->
    <dialog ref="createModal" class="modal modal-bottom sm:modal-middle">
      <div class="modal-box max-w-sm">
        <div class="flex items-center justify-between mb-5">
          <h3 class="font-bold text-lg">Add Department</h3>
          <button class="btn btn-ghost btn-sm btn-circle" @click="createModal.close()">✕</button>
        </div>
        <form @submit.prevent="createDept" class="flex flex-col gap-3">
          <label class="form-control">
            <div class="label py-1">
              <span class="label-text text-xs font-medium uppercase tracking-wider opacity-60">Name *</span>
            </div>
            <input
              v-model="form.name"
              class="input input-bordered"
              required
              placeholder="e.g. Engineering"
              autofocus
            />
          </label>
          <div class="modal-action mt-2">
            <button type="button" class="btn btn-ghost" @click="createModal.close()">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              <span v-if="saving" class="loading loading-spinner loading-sm"></span>
              Create
            </button>
          </div>
        </form>
      </div>
      <form method="dialog" class="modal-backdrop"><button>close</button></form>
    </dialog>

    <!-- Rename Modal -->
    <dialog ref="renameModal" class="modal modal-bottom sm:modal-middle">
      <div class="modal-box max-w-sm">
        <div class="flex items-center justify-between mb-5">
          <h3 class="font-bold text-lg">Rename Department</h3>
          <button class="btn btn-ghost btn-sm btn-circle" @click="renameModal.close()">✕</button>
        </div>
        <form @submit.prevent="saveName" class="flex flex-col gap-3">
          <label class="form-control">
            <div class="label py-1">
              <span class="label-text text-xs font-medium uppercase tracking-wider opacity-60">New Name *</span>
            </div>
            <input
              v-model="renameForm.name"
              class="input input-bordered"
              required
              placeholder="Department name"
            />
          </label>
          <div class="modal-action mt-2">
            <button type="button" class="btn btn-ghost" @click="renameModal.close()">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              <span v-if="saving" class="loading loading-spinner loading-sm"></span>
              Save
            </button>
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
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import DataTable from '@/components/DataTable.vue'

const toast   = useToast()
const { confirm } = useConfirm()

const departments = ref([])
const loading     = ref(false)
const saving      = ref(false)

// Table state
const page     = ref(1)
const pageSize = ref(25)
const search   = ref('')

// Modals
const createModal = ref(null)
const renameModal = ref(null)
const renameTarget = ref(null)

// Forms
const form       = ref({ name: '' })
const renameForm = ref({ name: '' })

// Columns
const columns = [
  { key: 'id',   label: 'ID',   hideMobile: true },
  { key: 'name', label: 'Name' },
]

// Actions
const actions = [
  {
    label: 'Rename',
    handler: (row) => openRename(row),
  },
  {
    label: 'Delete',
    class: 'text-error',
    handler: (row) => deleteDept(row),
  },
]

// Client-side filter + pagination
const filtered = computed(() => {
  const q = search.value.toLowerCase().trim()
  if (!q) return departments.value
  return departments.value.filter(d => d.name.toLowerCase().includes(q))
})

const pageRows = computed(() => {
  const from = (page.value - 1) * pageSize.value
  return filtered.value.slice(from, from + pageSize.value)
})

// Handlers
function openCreate() {
  form.value = { name: '' }
  createModal.value.showModal()
}

async function createDept() {
  saving.value = true
  try {
    await api.post('/api/v1/departments', form.value)
    createModal.value.close()
    toast.success(`Department "${form.value.name}" created`)
    await load()
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Failed to create department')
  } finally {
    saving.value = false
  }
}

function openRename(dept) {
  renameTarget.value = dept
  renameForm.value = { name: dept.name }
  renameModal.value.showModal()
}

async function saveName() {
  saving.value = true
  try {
    await api.put(`/api/v1/departments/${renameTarget.value.id}`, renameForm.value)
    renameModal.value.close()
    toast.success('Department renamed')
    await load()
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Failed to rename department')
  } finally {
    saving.value = false
  }
}

async function deleteDept(dept) {
  if (!await confirm(`Delete department "${dept.name}"?`, { title: 'Delete Department', confirmLabel: 'Delete' })) return
  try {
    await api.delete(`/api/v1/departments/${dept.id}`)
    toast.success(`"${dept.name}" deleted`)
    await load()
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Failed to delete — department may have employees')
  }
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/api/v1/departments')
    departments.value = data
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
