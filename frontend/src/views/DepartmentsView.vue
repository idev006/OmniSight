<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold">Departments</h1>
      <button class="btn btn-primary btn-sm" @click="openCreate">+ Add Department</button>
    </div>

    <div class="overflow-x-auto">
      <table class="table table-sm">
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in departments" :key="d.id">
            <td class="text-base-content/50">{{ d.id }}</td>
            <td>{{ d.name }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <dialog ref="modal" class="modal">
      <div class="modal-box">
        <h3 class="font-bold text-lg mb-4">Add Department</h3>
        <form @submit.prevent="create">
          <div class="form-control mb-6">
            <label class="label"><span class="label-text">Name</span></label>
            <input v-model="form.name" class="input input-bordered" required />
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
import { ref, onMounted } from 'vue'
import api from '@/api/client'

const departments = ref([])
const modal = ref(null)
const form = ref({ name: '' })

function openCreate() {
  form.value = { name: '' }
  modal.value.showModal()
}

async function create() {
  await api.post('/api/v1/departments', form.value)
  modal.value.close()
  await load()
}

async function load() {
  const { data } = await api.get('/api/v1/departments')
  departments.value = data
}

onMounted(load)
</script>
