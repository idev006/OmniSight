<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold">Stations</h1>
      <button class="btn btn-primary btn-sm" @click="openCreate">+ Add Station</button>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="s in stations" :key="s.id" class="card bg-base-200">
        <div class="card-body p-4">
          <div class="flex items-start justify-between">
            <div>
              <h3 class="font-bold">{{ s.name }}</h3>
              <p v-if="s.location" class="text-sm text-base-content/60">{{ s.location }}</p>
            </div>
            <span class="badge" :class="s.is_active ? 'badge-success' : 'badge-ghost'">
              {{ s.is_active ? 'Active' : 'Off' }}
            </span>
          </div>
          <div class="mt-2">
            <span class="text-xs text-base-content/50 uppercase">Departments</span>
            <div class="flex flex-wrap gap-1 mt-1">
              <span v-for="id in s.dept_ids" :key="id" class="badge badge-outline badge-sm">
                {{ deptName(id) }}
              </span>
              <span v-if="!s.dept_ids.length" class="text-xs text-base-content/40">None configured</span>
            </div>
          </div>
          <div class="card-actions justify-end mt-2">
            <button class="btn btn-ghost btn-xs" @click="openEdit(s)">Configure</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Create modal -->
    <dialog ref="createModal" class="modal">
      <div class="modal-box">
        <h3 class="font-bold text-lg mb-4">Add Station</h3>
        <form @submit.prevent="createStation">
          <div class="form-control mb-3">
            <label class="label"><span class="label-text">Name</span></label>
            <input v-model="createForm.name" class="input input-bordered" required />
          </div>
          <div class="form-control mb-6">
            <label class="label"><span class="label-text">Location (optional)</span></label>
            <input v-model="createForm.location" class="input input-bordered" />
          </div>
          <div class="modal-action">
            <button type="button" class="btn btn-ghost" @click="createModal.close()">Cancel</button>
            <button type="submit" class="btn btn-primary">Create</button>
          </div>
        </form>
      </div>
      <form method="dialog" class="modal-backdrop"><button>close</button></form>
    </dialog>

    <!-- Edit departments modal -->
    <dialog ref="editModal" class="modal">
      <div class="modal-box">
        <h3 class="font-bold text-lg mb-4">Configure: {{ editTarget?.name }}</h3>
        <div class="form-control mb-6">
          <label class="label"><span class="label-text">Assigned Departments</span></label>
          <div class="flex flex-col gap-2 mt-1">
            <label v-for="d in departments" :key="d.id" class="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" class="checkbox checkbox-sm" :value="d.id" v-model="editDepts" />
              <span>{{ d.name }}</span>
            </label>
          </div>
        </div>
        <div class="modal-action">
          <button type="button" class="btn btn-ghost" @click="editModal.close()">Cancel</button>
          <button class="btn btn-primary" @click="saveEdit">Save</button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop"><button>close</button></form>
    </dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api/client'

const stations = ref([])
const departments = ref([])
const createModal = ref(null)
const editModal = ref(null)
const createForm = ref({ name: '', location: '' })
const editTarget = ref(null)
const editDepts = ref([])

function deptName(id) {
  return departments.value.find((d) => d.id === id)?.name || id
}

function openCreate() {
  createForm.value = { name: '', location: '' }
  createModal.value.showModal()
}

function openEdit(station) {
  editTarget.value = station
  editDepts.value = [...station.dept_ids]
  editModal.value.showModal()
}

async function createStation() {
  await api.post('/api/v1/stations', createForm.value)
  createModal.value.close()
  await load()
}

async function saveEdit() {
  await api.put(`/api/v1/stations/${editTarget.value.id}/departments`, { dept_ids: editDepts.value })
  editModal.value.close()
  await load()
}

async function load() {
  const [sRes, dRes] = await Promise.all([
    api.get('/api/v1/stations'),
    api.get('/api/v1/departments'),
  ])
  stations.value = sRes.data
  departments.value = dRes.data
}

onMounted(load)
</script>
