import { ref } from 'vue'

// Singleton state shared across all callers
const isOpen   = ref(false)
const title    = ref('')
const message  = ref('')
const confirmLabel = ref('Confirm')
const confirmClass = ref('btn-error')
let _resolve   = null

export function useConfirm() {
  /**
   * Show a confirm dialog.
   * @param {string} msg        - Body message
   * @param {object} [opts]
   * @param {string} [opts.title]         - Dialog title (default: 'Confirm')
   * @param {string} [opts.confirmLabel]  - Confirm button text (default: 'Confirm')
   * @param {string} [opts.confirmClass]  - DaisyUI btn class (default: 'btn-error')
   * @returns {Promise<boolean>}
   */
  function confirm(msg, opts = {}) {
    message.value      = msg
    title.value        = opts.title        ?? 'Confirm'
    confirmLabel.value = opts.confirmLabel ?? 'Confirm'
    confirmClass.value = opts.confirmClass ?? 'btn-error'
    isOpen.value       = true
    return new Promise(resolve => { _resolve = resolve })
  }

  function _answer(val) {
    isOpen.value = false
    _resolve?.(val)
    _resolve = null
  }

  return { confirm, isOpen, title, message, confirmLabel, confirmClass, _answer }
}
