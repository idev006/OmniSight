<template>
  <div class="flex flex-col gap-5">

    <!-- Page header -->
    <div class="flex items-start justify-between gap-3">
      <div>
        <h1 class="text-xl font-bold tracking-wide">User Management</h1>
        <p class="text-sm text-base-content/40 mt-0.5">System accounts and station access control</p>
      </div>
      <button class="btn btn-primary btn-sm gap-2" @click="openCreate">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        Add User
      </button>
    </div>

    <!-- Stats row -->
    <div class="stats bg-base-100 border border-base-300 shadow-sm w-full">
      <div class="stat"><div class="stat-title text-xs">Total</div><div class="stat-value text-2xl">{{ allUsers.length }}</div></div>
      <div class="stat"><div class="stat-title text-xs">Active</div><div class="stat-value text-2xl text-success">{{ allUsers.filter(u=>u.is_active).length }}</div></div>
      <div class="stat"><div class="stat-title text-xs">Admin</div><div class="stat-value text-2xl text-error">{{ allUsers.filter(u=>u.role==='ADMIN').length }}</div></div>
      <div class="stat"><div class="stat-title text-xs">HR</div><div class="stat-value text-2xl text-warning">{{ allUsers.filter(u=>u.role==='HR').length }}</div></div>
    </div>

    <!-- Role filter (extra toolbar slot) -->
    <DataTable
      :columns="columns"
      :rows="pageRows"
      :total="filtered.length"
      :loading="loading"
      v-model:page="page"
      v-model:page-size="pageSize"
      v-model:search="search"
      :actions="actions"
      search-placeholder="Search username or name…"
      empty-text="No users match your search"
    >
      <!-- Extra toolbar: role filter -->
      <template #toolbar>
        <select v-model="filterRole" class="select select-bordered select-sm">
          <option value="">All Roles</option>
          <option value="ADMIN">ADMIN</option>
          <option value="HR">HR</option>
          <option value="OPERATOR">OPERATOR</option>
        </select>
      </template>

      <!-- Custom cells -->
      <template #cell-username="{ row }">
        <div class="flex items-center gap-2">
          <div class="avatar placeholder">
            <div class="rounded-full w-6 text-xs font-bold" :class="avatarBg(row.role)">
              <span>{{ row.username[0].toUpperCase() }}</span>
            </div>
          </div>
          <span class="font-medium">{{ row.username }}</span>
        </div>
      </template>

      <template #cell-role="{ row }">
        <span class="badge badge-sm font-medium" :class="roleBadge(row.role)">{{ row.role }}</span>
      </template>

      <template #cell-station_ids="{ row }">
        <span v-if="row.role !== 'OPERATOR'" class="text-xs text-base-content/30">All</span>
        <span v-else class="text-sm font-medium">
          {{ row.station_ids.length }}
          <span class="text-base-content/40 font-normal text-xs">station{{ row.station_ids.length !== 1 ? 's' : '' }}</span>
        </span>
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

    <!-- ── Create Modal ───────────────────────────────────────────────── -->
    <dialog ref="createModal" class="modal modal-bottom sm:modal-middle">
      <div class="modal-box max-w-md">
        <div class="flex items-center justify-between mb-5">
          <h3 class="font-bold text-lg">Create User</h3>
          <button class="btn btn-ghost btn-sm btn-circle" @click="createModal.close()">✕</button>
        </div>
        <form @submit.prevent="createUser" class="flex flex-col gap-3">
          <label class="form-control">
            <div class="label py-1"><span class="label-text text-xs font-medium uppercase tracking-wider opacity-60">Username *</span></div>
            <input v-model="form.username" class="input input-bordered" required autocomplete="off" placeholder="e.g. john.doe" />
          </label>
          <label class="form-control">
            <div class="label py-1"><span class="label-text text-xs font-medium uppercase tracking-wider opacity-60">Password *</span></div>
            <input v-model="form.password" type="password" class="input input-bordered" required autocomplete="new-password" placeholder="••••••••" />
          </label>
          <label class="form-control">
            <div class="label py-1"><span class="label-text text-xs font-medium uppercase tracking-wider opacity-60">Full Name</span></div>
            <input v-model="form.full_name" class="input input-bordered" placeholder="Optional display name" />
          </label>
          <label class="form-control">
            <div class="label py-1"><span class="label-text text-xs font-medium uppercase tracking-wider opacity-60">Role *</span></div>
            <select v-model="form.role" class="select select-bordered">
              <option value="OPERATOR">OPERATOR — Station access only</option>
              <option value="HR">HR — Employee &amp; attendance management</option>
              <option value="ADMIN">ADMIN — Full system access</option>
            </select>
          </label>
          <div class="modal-action mt-2">
            <button type="button" class="btn btn-ghost" @click="createModal.close()">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              <span v-if="saving" class="loading loading-spinner loading-sm"></span>
              Create User
            </button>
          </div>
        </form>
      </div>
      <form method="dialog" class="modal-backdrop"><button>close</button></form>
    </dialog>

    <!-- ── Edit Modal ─────────────────────────────────────────────────── -->
    <dialog ref="editModal" class="modal modal-bottom sm:modal-middle">
      <div class="modal-box max-w-md">
        <div class="flex items-center justify-between mb-5">
          <div>
            <h3 class="font-bold text-lg">Edit User</h3>
            <p class="text-xs text-base-content/40 font-mono mt-0.5">{{ editTarget?.username }}</p>
          </div>
          <button class="btn btn-ghost btn-sm btn-circle" @click="editModal.close()">✕</button>
        </div>
        <form @submit.prevent="saveEdit" class="flex flex-col gap-3">
          <label class="form-control">
            <div class="label py-1"><span class="label-text text-xs font-medium uppercase tracking-wider opacity-60">Full Name</span></div>
            <input v-model="editForm.full_name" class="input input-bordered" placeholder="Display name" />
          </label>
          <label class="form-control">
            <div class="label py-1"><span class="label-text text-xs font-medium uppercase tracking-wider opacity-60">Role</span></div>
            <select v-model="editForm.role" class="select select-bordered">
              <option value="OPERATOR">OPERATOR</option>
              <option value="HR">HR</option>
              <option value="ADMIN">ADMIN</option>
            </select>
          </label>
          <label class="form-control">
            <div class="label py-1">
              <span class="label-text text-xs font-medium uppercase tracking-wider opacity-60">New Password</span>
              <span class="label-text-alt text-xs opacity-40">Leave blank to keep</span>
            </div>
            <input v-model="editForm.password" type="password" class="input input-bordered" autocomplete="new-password" placeholder="••••••••" />
          </label>
          <div class="flex items-center gap-3 px-1 py-2">
            <input type="checkbox" v-model="editForm.is_active" class="toggle toggle-success" />
            <span class="text-sm font-medium">Account active</span>
          </div>
          <div class="modal-action mt-2">
            <button type="button" class="btn btn-ghost" @click="editModal.close()">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              <span v-if="saving" class="loading loading-spinner loading-sm"></span>
              Save Changes
            </button>
          </div>
        </form>
      </div>
      <form method="dialog" class="modal-backdrop"><button>close</button></form>
    </dialog>

    <!-- ── Station Assignment Modal ───────────────────────────────────── -->
    <dialog ref="stationModal" class="modal modal-bottom sm:modal-middle">
      <div class="modal-box max-w-md">
        <div class="flex items-center justify-between mb-1">
          <h3 class="font-bold text-lg">Station Access</h3>
          <button class="btn btn-ghost btn-sm btn-circle" @click="stationModal.close()">✕</button>
        </div>
        <p class="text-sm text-base-content/40 mb-4">
          Operator <span class="font-mono text-primary font-medium">{{ stationTarget?.username }}</span> can only scan at assigned stations.
        </p>
        <div class="flex flex-col gap-1.5 max-h-64 overflow-y-auto pr-1">
          <label
            v-for="s in stations"
            :key="s.id"
            class="flex items-center gap-3 cursor-pointer px-3 py-2.5 rounded-xl hover:bg-base-200 border border-transparent hover:border-base-300 transition-colors"
            :class="{ 'bg-primary/5 border-primary/20': selectedStations.includes(s.id) }"
          >
            <input type="checkbox" :value="s.id" v-model="selectedStations" class="checkbox checkbox-primary checkbox-sm" />
            <div class="flex-1 min-w-0">
              <div class="font-medium text-sm">{{ s.name }}</div>
              <div class="text-xs text-base-content/35 truncate">{{ s.location || 'No location set' }}</div>
            </div>
          </label>
          <div v-if="stations.length === 0" class="text-center py-6 text-sm text-base-content/30">No stations configured</div>
        </div>
        <div class="modal-action mt-4">
          <button class="btn btn-ghost" @click="stationModal.close()">Cancel</button>
          <button class="btn btn-primary" @click="saveStations" :disabled="saving">
            <span v-if="saving" class="loading loading-spinner loading-sm"></span>
            Save Access
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop"><button>close</button></form>
    </dialog>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import DataTable from '@/components/DataTable.vue'

const authStore = useAuthStore()
const toast     = useToast()

// ── Data ──────────────────────────────────────────────────────────
const allUsers = ref([])
const stations = ref([])
const loading  = ref(false)
const saving   = ref(false)

// ── Table state ───────────────────────────────────────────────────
const page       = ref(1)
const pageSize   = ref(25)
const search     = ref('')
const filterRole = ref('')

// ── Columns ───────────────────────────────────────────────────────
const columns = [
  { key: 'username',    label: 'Username' },
  { key: 'full_name',   label: 'Full Name',  hideMobile: true },
  { key: 'role',        label: 'Role' },
  { key: 'station_ids', label: 'Stations',   hideMobile: true },
  { key: 'is_active',   label: 'Status' },
]

// ── Actions ───────────────────────────────────────────────────────
const actions = [
  {
    label: 'Edit',
    handler: (row) => openEdit(row),
  },
  {
    label: 'Stations',
    handler: (row) => openStations(row),
    show: (row) => row.role === 'OPERATOR',
  },
  {
    label: 'Delete',
    class: 'text-error',
    handler: (row) => deleteUser(row),
    disabled: (row) => row.username === authStore.user?.username,
  },
]

// ── Client-side filtering + pagination ────────────────────────────
const filtered = computed(() => {
  let list = allUsers.value
  const q = search.value.toLowerCase().trim()
  if (q) {
    list = list.filter(u =>
      u.username.toLowerCase().includes(q) ||
      (u.full_name || '').toLowerCase().includes(q)
    )
  }
  if (filterRole.value) {
    list = list.filter(u => u.role === filterRole.value)
  }
  return list
})

const pageRows = computed(() => {
  const from = (page.value - 1) * pageSize.value
  return filtered.value.slice(from, from + pageSize.value)
})

// ── Modals ────────────────────────────────────────────────────────
const createModal  = ref(null)
const editModal    = ref(null)
const stationModal = ref(null)

const form              = ref({ username: '', password: '', full_name: '', role: 'OPERATOR' })
const editTarget        = ref(null)
const editForm          = ref({ full_name: '', role: '', is_active: true, password: '' })
const stationTarget     = ref(null)
const selectedStations  = ref([])

// ── Helpers ───────────────────────────────────────────────────────
function roleBadge(role) {
  if (role === 'ADMIN') return 'badge-error'
  if (role === 'HR')    return 'badge-warning'
  return 'badge-info'
}
function avatarBg(role) {
  if (role === 'ADMIN') return 'bg-error text-error-content'
  if (role === 'HR')    return 'bg-warning text-warning-content'
  return 'bg-primary text-primary-content'
}

// ── CRUD ──────────────────────────────────────────────────────────
function openCreate() {
  form.value = { username: '', password: '', full_name: '', role: 'OPERATOR' }
  createModal.value.showModal()
}

async function createUser() {
  saving.value = true
  try {
    await api.post('/api/v1/users', form.value)
    createModal.value.close()
    toast.success(`User "${form.value.username}" created`)
    await load()
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Failed to create user')
  } finally {
    saving.value = false
  }
}

function openEdit(u) {
  editTarget.value = u
  editForm.value = { full_name: u.full_name || '', role: u.role, is_active: u.is_active, password: '' }
  editModal.value.showModal()
}

async function saveEdit() {
  saving.value = true
  const payload = { ...editForm.value }
  if (!payload.password) delete payload.password
  try {
    await api.put(`/api/v1/users/${editTarget.value.id}`, payload)
    editModal.value.close()
    toast.success('User updated')
    await load()
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Failed to update user')
  } finally {
    saving.value = false
  }
}

function openStations(u) {
  stationTarget.value = u
  selectedStations.value = [...u.station_ids]
  stationModal.value.showModal()
}

async function saveStations() {
  saving.value = true
  try {
    await api.put(`/api/v1/users/${stationTarget.value.id}/stations`, {
      station_ids: selectedStations.value,
    })
    stationModal.value.close()
    toast.success('Station access updated')
    await load()
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Failed to update stations')
  } finally {
    saving.value = false
  }
}

async function deleteUser(u) {
  if (!confirm(`Delete user "${u.username}"? This cannot be undone.`)) return
  try {
    await api.delete(`/api/v1/users/${u.id}`)
    toast.success(`User "${u.username}" deleted`)
    await load()
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Failed to delete user')
  }
}

async function load() {
  loading.value = true
  try {
    const [uRes, sRes] = await Promise.all([
      api.get('/api/v1/users'),
      api.get('/api/v1/stations'),
    ])
    allUsers.value = uRes.data
    stations.value = sRes.data
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
