<!--
  DataTable.vue — Reusable server-side-ready data table
  ======================================================
  Props:
    columns    — [{ key, label, class?, headerClass?, sortable?, hideMobile? }]
    rows       — data for CURRENT page (parent handles fetching)
    total      — total record count across all pages
    loading    — boolean
    page       — current page (1-based),  v-model:page
    pageSize   — rows per page,           v-model:page-size
    search     — search string,           v-model:search
    pageSizes  — array of size options,   default [10, 25, 50, 100]
    actions    — [{ label, icon?, class?, handler(row), disabled?(row), show?(row) }]
    searchPlaceholder
    emptyText

  Slots:
    cell-{key}  — custom cell: { row, value }
    toolbar     — extra filter controls placed after search input
-->
<template>
  <div class="flex flex-col gap-3">

    <!-- ── Toolbar ──────────────────────────────────────────────── -->
    <div class="flex flex-wrap gap-2 items-center">

      <!-- Search -->
      <label class="input input-sm input-bordered flex items-center gap-2 flex-1 min-w-[180px] max-w-xs">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 opacity-50 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          type="text"
          class="grow bg-transparent outline-none text-sm"
          :placeholder="searchPlaceholder || 'Search…'"
          :value="search"
          @input="onSearchInput"
        />
        <button v-if="search" class="opacity-40 hover:opacity-80" @click="clearSearch">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </label>

      <!-- Extra toolbar slot (additional filters) -->
      <slot name="toolbar" />

      <div class="flex-1"></div>

      <!-- Page size -->
      <div class="flex items-center gap-2">
        <span class="text-xs text-base-content/40 hidden sm:inline whitespace-nowrap">Rows</span>
        <select
          :value="pageSize"
          @change="onPageSizeChange"
          class="select select-sm select-bordered w-20"
        >
          <option v-for="n in pageSizes" :key="n" :value="n">{{ n }}</option>
        </select>
      </div>
    </div>

    <!-- ── Table (sm+) ───────────────────────────────────────────── -->
    <!-- overflow-visible required — overflow-hidden clips DaisyUI dropdowns -->
    <div class="hidden sm:block bg-base-100 rounded-2xl border border-base-300">
      <div class="overflow-x-auto rounded-2xl">
        <table class="table table-sm">
          <thead class="bg-base-200/60">
            <tr>
              <th
                v-for="col in columns"
                :key="col.key"
                class="text-xs font-semibold uppercase tracking-wider opacity-60"
                :class="col.headerClass"
              >{{ col.label }}</th>
              <th v-if="actions.length" class="text-xs font-semibold uppercase tracking-wider opacity-60 text-right">Actions</th>
            </tr>
          </thead>

          <tbody>
            <!-- Loading skeleton -->
            <tr v-if="loading">
              <td :colspan="columns.length + (actions.length ? 1 : 0)" class="py-10 text-center">
                <span class="loading loading-spinner loading-sm text-primary"></span>
              </td>
            </tr>
            <!-- Empty state -->
            <tr v-else-if="rows.length === 0">
              <td :colspan="columns.length + (actions.length ? 1 : 0)" class="py-12 text-center text-sm text-base-content/30">
                <div class="flex flex-col items-center gap-2">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10 opacity-20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                  <span>{{ emptyText || 'No records found' }}</span>
                </div>
              </td>
            </tr>
            <!-- Data rows -->
            <tr v-else v-for="row in rows" :key="rowKey(row)" class="hover:bg-base-200/30 transition-colors">
              <td v-for="col in columns" :key="col.key" :class="col.class">
                <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]">
                  {{ row[col.key] ?? '—' }}
                </slot>
              </td>
              <!-- Actions cell -->
              <td v-if="actions.length" class="text-right">
                <!-- 1-3 actions: inline buttons -->
                <div v-if="visibleActions(row).length <= 3" class="flex gap-1 justify-end">
                  <button
                    v-for="act in visibleActions(row)"
                    :key="act.label"
                    class="btn btn-xs btn-ghost"
                    :class="act.class"
                    :disabled="act.disabled ? act.disabled(row) : false"
                    @click.stop="act.handler(row)"
                  >
                    <span v-if="act.icon" v-html="act.icon" class="h-3.5 w-3.5"></span>
                    {{ act.label }}
                  </button>
                </div>
                <!-- 4+ actions: click-toggled dropdown -->
                <div v-else class="relative" v-click-outside="() => openDropdown = null">
                  <button
                    class="btn btn-xs btn-ghost btn-circle"
                    @click.stop="openDropdown = openDropdown === rowKey(row) ? null : rowKey(row)"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                      <circle cx="12" cy="5" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/>
                    </svg>
                  </button>
                  <ul
                    v-if="openDropdown === rowKey(row)"
                    class="absolute right-0 z-[100] mt-1 w-40 bg-base-100 border border-base-300 rounded-xl shadow-xl p-1 flex flex-col"
                  >
                    <li v-for="act in visibleActions(row)" :key="act.label" class="list-none">
                      <button
                        class="w-full text-left text-sm px-3 py-1.5 rounded-lg hover:bg-base-200 transition-colors"
                        :class="act.class"
                        :disabled="act.disabled ? act.disabled(row) : false"
                        @click.stop="act.handler(row); openDropdown = null"
                      >{{ act.label }}</button>
                    </li>
                  </ul>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ── Mobile Cards ──────────────────────────────────────────── -->
    <div class="sm:hidden flex flex-col gap-2">
      <!-- Loading -->
      <div v-if="loading" class="flex justify-center py-10">
        <span class="loading loading-spinner loading-md text-primary"></span>
      </div>
      <!-- Empty -->
      <div v-else-if="rows.length === 0" class="text-center py-10 text-sm text-base-content/30">
        {{ emptyText || 'No records found' }}
      </div>
      <!-- Cards -->
      <div
        v-else
        v-for="row in rows"
        :key="rowKey(row)"
        class="bg-base-100 rounded-2xl border border-base-300 p-4 flex flex-col gap-2"
      >
        <!-- Rows: label + value for each visible column -->
        <div
          v-for="col in mobileColumns"
          :key="col.key"
          class="flex items-start justify-between gap-2 text-sm"
        >
          <span class="text-base-content/40 text-xs uppercase tracking-wider font-medium shrink-0 pt-0.5">{{ col.label }}</span>
          <div class="text-right">
            <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]">
              <span>{{ row[col.key] ?? '—' }}</span>
            </slot>
          </div>
        </div>
        <!-- Actions -->
        <div v-if="actions.length" class="flex flex-wrap gap-1.5 pt-2 mt-1 border-t border-base-300/50">
          <button
            v-for="act in visibleActions(row)"
            :key="act.label"
            class="btn btn-xs"
            :class="act.class || 'btn-ghost'"
            :disabled="act.disabled ? act.disabled(row) : false"
            @click.stop="act.handler(row)"
          >{{ act.label }}</button>
        </div>
      </div>
    </div>

    <!-- ── Pagination footer ─────────────────────────────────────── -->
    <div class="flex flex-wrap items-center justify-between gap-3 pt-1">

      <!-- Record info -->
      <div class="text-xs text-base-content/40">
        <template v-if="total > 0">
          Showing <span class="font-medium text-base-content/70">{{ rangeFrom }}</span>–<span class="font-medium text-base-content/70">{{ rangeTo }}</span>
          of <span class="font-medium text-base-content/70">{{ total }}</span> records
        </template>
        <template v-else>No records</template>
      </div>

      <!-- Page buttons — always visible, buttons disable when only 1 page -->
      <div class="join">
        <!-- First + Prev -->
        <button class="join-item btn btn-xs btn-ghost" :disabled="page <= 1" @click="goPage(1)" title="First">
          «
        </button>
        <button class="join-item btn btn-xs btn-ghost" :disabled="page <= 1" @click="goPage(page - 1)" title="Previous">
          ‹
        </button>

        <!-- Page numbers with ellipsis -->
        <template v-for="p in pageNumbers" :key="p">
          <span v-if="p === '…'" class="join-item btn btn-xs btn-disabled btn-ghost">…</span>
          <button
            v-else
            class="join-item btn btn-xs"
            :class="p === page ? 'btn-primary' : 'btn-ghost'"
            @click="goPage(p)"
          >{{ p }}</button>
        </template>

        <!-- Next + Last -->
        <button class="join-item btn btn-xs btn-ghost" :disabled="page >= totalPages" @click="goPage(page + 1)" title="Next">
          ›
        </button>
        <button class="join-item btn btn-xs btn-ghost" :disabled="page >= totalPages" @click="goPage(totalPages)" title="Last">
          »
        </button>
      </div>

    </div>

  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

// Click-outside directive for closing the dropdown
const vClickOutside = {
  mounted(el, binding) {
    el._clickOutside = (e) => { if (!el.contains(e.target)) binding.value(e) }
    document.addEventListener('click', el._clickOutside)
  },
  unmounted(el) {
    document.removeEventListener('click', el._clickOutside)
  },
}

const openDropdown = ref(null)

const props = defineProps({
  columns:           { type: Array,   required: true },
  rows:              { type: Array,   default: () => [] },
  total:             { type: Number,  default: 0 },
  loading:           { type: Boolean, default: false },
  page:              { type: Number,  default: 1 },
  pageSize:          { type: Number,  default: 25 },
  search:            { type: String,  default: '' },
  pageSizes:         { type: Array,   default: () => [10, 25, 50, 100] },
  actions:           { type: Array,   default: () => [] },
  searchPlaceholder: { type: String,  default: '' },
  emptyText:         { type: String,  default: '' },
  rowKeyField:       { type: String,  default: 'id' },
})

const emit = defineEmits([
  'update:page',
  'update:pageSize',
  'update:search',
])

// ── Derived ──────────────────────────────────────────────────────

const totalPages = computed(() =>
  props.pageSize > 0 ? Math.max(1, Math.ceil(props.total / props.pageSize)) : 1
)

const rangeFrom = computed(() =>
  props.total === 0 ? 0 : (props.page - 1) * props.pageSize + 1
)
const rangeTo = computed(() =>
  Math.min(props.page * props.pageSize, props.total)
)

// Mobile: exclude columns marked hideMobile: true, but always show at least 3
const mobileColumns = computed(() =>
  props.columns.filter(c => !c.hideMobile)
)

function rowKey(row) {
  return row[props.rowKeyField] ?? JSON.stringify(row)
}

function visibleActions(row) {
  return props.actions.filter(a => !a.show || a.show(row))
}

// ── Page number list with ellipsis ────────────────────────────────
// Returns e.g. [1, '…', 4, 5, 6, '…', 20]
const pageNumbers = computed(() => {
  const total = totalPages.value
  const cur   = props.page
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)

  const pages = new Set([1, total, cur])
  if (cur > 1) pages.add(cur - 1)
  if (cur < total) pages.add(cur + 1)
  // Add buffer near start/end
  if (cur <= 3) { pages.add(2); pages.add(3) }
  if (cur >= total - 2) { pages.add(total - 1); pages.add(total - 2) }

  const sorted = [...pages].sort((a, b) => a - b)
  const result = []
  let prev = 0
  for (const p of sorted) {
    if (p - prev > 1) result.push('…')
    result.push(p)
    prev = p
  }
  return result
})

// ── Search debounce ───────────────────────────────────────────────
let searchTimer = null

function onSearchInput(e) {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    emit('update:search', e.target.value)
    emit('update:page', 1)   // Reset to page 1 on new search
  }, 350)
}

function clearSearch() {
  emit('update:search', '')
  emit('update:page', 1)
}

// ── Page / pageSize ───────────────────────────────────────────────
function goPage(p) {
  const clamped = Math.max(1, Math.min(p, totalPages.value))
  if (clamped !== props.page) emit('update:page', clamped)
}

function onPageSizeChange(e) {
  emit('update:pageSize', Number(e.target.value))
  emit('update:page', 1)   // Reset to page 1 when page size changes
}
</script>
