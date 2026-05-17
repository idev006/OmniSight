<template>
  <dialog ref="dlg" class="modal modal-bottom sm:modal-middle" @cancel.prevent>
    <div class="modal-box max-w-sm">
      <!-- Icon + Title -->
      <div class="flex items-center gap-3 mb-3">
        <div class="w-10 h-10 rounded-full bg-error/10 flex items-center justify-center shrink-0">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-error" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
          </svg>
        </div>
        <h3 class="font-bold text-base">{{ title }}</h3>
      </div>

      <!-- Message -->
      <p class="text-sm text-base-content/60 leading-relaxed pl-13">{{ message }}</p>

      <!-- Actions -->
      <div class="modal-action mt-5">
        <button class="btn btn-ghost btn-sm" @click="answer(false)">Cancel</button>
        <button class="btn btn-sm" :class="confirmClass" @click="answer(true)">
          {{ confirmLabel }}
        </button>
      </div>
    </div>
    <!-- clicking backdrop = cancel -->
    <form method="dialog" class="modal-backdrop"><button @click.prevent="answer(false)">close</button></form>
  </dialog>
</template>

<script setup>
import { watch, ref } from 'vue'
import { useConfirm } from '@/composables/useConfirm'

const { isOpen, title, message, confirmLabel, confirmClass, _answer } = useConfirm()
const dlg = ref(null)

watch(isOpen, (val) => {
  if (!dlg.value) return
  if (val) dlg.value.showModal()
  else     dlg.value.close()
})

function answer(val) {
  _answer(val)
}
</script>
