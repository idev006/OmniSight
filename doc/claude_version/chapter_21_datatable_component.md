# Chapter 21 — DataTable Component

> เขียน: 2026-05-17 | Sprint 8

---

## ทำไมต้องมี DataTable Component?

ทุก view ใน OmniSight มี pattern เหมือนกัน:
- แสดงรายการข้อมูลแบบตาราง
- ค้นหา / กรอง
- แบ่งหน้า
- มีปุ่ม action ต่อ row

ถ้าไม่ abstract ออกมา → copy-paste logic เดิมซ้ำทุก view  
→ แก้ bug ที่เดียวต้องแก้ทุก view

---

## Component API

### File
`frontend/src/components/DataTable.vue`

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `columns` | `Column[]` | required | Column definitions |
| `rows` | `any[]` | `[]` | Data for **current page** (parent handles fetching) |
| `total` | `number` | `0` | Total record count (all pages) |
| `loading` | `boolean` | `false` | Show loading spinner |
| `page` | `number` | `1` | Current page (1-based), **v-model** |
| `pageSize` | `number` | `25` | Rows per page, **v-model** |
| `search` | `string` | `''` | Search text, **v-model** |
| `pageSizes` | `number[]` | `[10,25,50,100]` | Page size options |
| `actions` | `Action[]` | `[]` | Row actions |
| `searchPlaceholder` | `string` | `'Search…'` | Input placeholder |
| `emptyText` | `string` | `'No records found'` | Empty state message |
| `rowKeyField` | `string` | `'id'` | Field used as `:key` |

### Column definition

```js
{
  key:         string,          // matches data field name
  label:       string,          // header text
  class?:      string,          // td CSS classes
  headerClass?:string,          // th CSS classes
  hideMobile?: boolean,         // hide in mobile card view (default: false)
}
```

### Action definition

```js
{
  label:     string,            // button text
  class?:    string,            // CSS classes (e.g. 'text-error')
  handler:   (row) => void,     // click callback
  disabled?: (row) => boolean,  // disable condition
  show?:     (row) => boolean,  // visibility condition (default: always shown)
}
```

### Emits

| Event | Payload | When |
|-------|---------|------|
| `update:page` | `number` | Page changed |
| `update:pageSize` | `number` | Page size changed (also resets page to 1) |
| `update:search` | `string` | Search text changed, debounced 350ms (also resets page to 1) |

### Slots

| Slot | Props | Description |
|------|-------|-------------|
| `cell-{key}` | `{ row, value }` | Custom cell rendering for column `key` |
| `toolbar` | — | Extra filter controls placed after search input |

---

## Usage Patterns

### Pattern A — Client-side (small dataset, fetch all at once)

```vue
<script setup>
const allRows  = ref([])       // fetch all from API once
const page     = ref(1)
const pageSize = ref(25)
const search   = ref('')

const filtered = computed(() => {
  const q = search.value.toLowerCase()
  return allRows.value.filter(r => r.name.toLowerCase().includes(q))
})

const pageRows = computed(() => {
  const from = (page.value - 1) * pageSize.value
  return filtered.value.slice(from, from + pageSize.value)
})
</script>

<template>
  <DataTable
    :columns="columns"
    :rows="pageRows"
    :total="filtered.length"
    :loading="loading"
    v-model:page="page"
    v-model:page-size="pageSize"
    v-model:search="search"
    :actions="actions"
  />
</template>
```

**ใช้กับ:** Users, Employees, Stations, Departments (< 10,000 rows)

---

### Pattern B — Server-side (large dataset, paginate from API)

```vue
<script setup>
const rows     = ref([])
const total    = ref(0)
const page     = ref(1)
const pageSize = ref(25)
const search   = ref('')

// Watch all params → call API
watch([page, pageSize, search], fetchData)

async function fetchData() {
  loading.value = true
  const { data } = await api.get('/api/v1/attendance', {
    params: { page: page.value, page_size: pageSize.value, q: search.value }
  })
  rows.value  = data.items
  total.value = data.total
  loading.value = false
}
</script>
```

**ใช้กับ:** Attendance logs, Face templates (> 10,000 rows expected)

---

## Responsive Behavior

| Breakpoint | Behavior |
|-----------|----------|
| `< 640px` (mobile) | Card layout — each row = a card with label:value pairs |
| `≥ 640px` (tablet+) | Standard table layout with horizontal scroll if needed |

Column visibility in mobile cards:
- `hideMobile: false` (default) → shown in card
- `hideMobile: true` → hidden in card (saves space, e.g. ID, dates)

---

## Action Column Rules

| # of actions visible for a row | UI |
|------|-----|
| 1 | Single inline button |
| 2 | Two inline buttons side by side |
| 3+ | ⋯ dropdown menu |

Action visibility is controlled per-row:
```js
{ label: 'Assign Stations', show: (row) => row.role === 'OPERATOR' }
```

---

## Pagination Algorithm

Page numbers use **smart ellipsis** — always shows:
- First page
- Last page
- Current page ± 1
- Padded near start/end (pages 2,3 when near start; last-1, last-2 when near end)

Example: total=20 pages, current=10
```
« ‹  1 … 9 10 11 … 20  › »
```

---

## Views Using DataTable

| View | Mode | Server-side fetch |
|------|------|-------------------|
| `UsersView.vue` | Client | Once on mount |
| `EmployeesView.vue` | Client | Once on mount |
| `AttendanceView.vue` | Client* | On date/dept filter change |

*Attendance: API fetches by date/dept (server filter), then client paginates within result.

---

## Design Decisions

| Decision | Reason |
|----------|--------|
| 350ms search debounce | Avoid hammering API on every keystroke |
| Reset to page 1 on search/pageSize change | Prevent "no results" on page 5 after narrowing filter |
| `show?` on actions | Avoids disabled+invisible buttons cluttering the UI |
| Dropdown for 3+ actions | Table rows stay compact; avoids horizontal overflow |
| Mobile card view | DaisyUI tables scroll horizontally on mobile — poor UX for touch |
| Client-side pagination default | Current datasets < 1000 rows; avoids API complexity |

---

*อัพเดทล่าสุด: 2026-05-17 (Sprint 8)*
