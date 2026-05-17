import { ref } from 'vue'

const toasts = ref([])
let _id = 0

export function useToast() {
  function add(message, type = 'info', duration = 3500) {
    const id = ++_id
    toasts.value.push({ id, message, type })
    setTimeout(() => remove(id), duration)
    return id
  }

  function remove(id) {
    const idx = toasts.value.findIndex(t => t.id === id)
    if (idx !== -1) toasts.value.splice(idx, 1)
  }

  const success = (msg, dur)  => add(msg, 'success', dur)
  const error   = (msg, dur)  => add(msg, 'error',   dur ?? 5000)
  const warning = (msg, dur)  => add(msg, 'warning', dur)
  const info    = (msg, dur)  => add(msg, 'info',    dur)

  return { toasts, add, remove, success, error, warning, info }
}
