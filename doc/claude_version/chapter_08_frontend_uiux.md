# Chapter 8: Frontend UI/UX Specification

## หลักการออกแบบ

1. **DaisyUI Native** — ใช้ Component มาตรฐานของ DaisyUI โดยไม่ดัดแปลงโดยไม่จำเป็น
2. **Backend Does Everything** — Frontend รับผลลัพธ์จาก WebSocket แล้ววาด Overlay เท่านั้น
3. **Zero-Lag Illusion** — Video stream และ Overlay ต้องลื่นไหลตลอดเวลา แม้ Backend กำลังประมวลผล
4. **Minimalist** — แสดงเฉพาะข้อมูลที่จำเป็น ลด Cognitive Load

---

## หน้าจอหลัก (Pages)

| Page | URL | ผู้ใช้ |
|------|-----|-------|
| Scan View | `/scan/:stationId` | หน้าจอกล้อง (เปิดตลอด) |
| Admin Dashboard | `/admin` | HR/Admin |
| Employee List | `/admin/employees` | HR/Admin |
| Face Enrollment | `/admin/employees/:id/enroll` | HR/Admin |
| Station Manager | `/admin/stations` | Super Admin |
| Attendance Report | `/admin/reports` | HR/Admin |
| Login | `/login` | ทุกคน |

---

## Scan View (หน้าจอหลัก)

### Layout

```
┌─────────────────────────────────────────────────┐
│                                                 │
│     [Video Stream - Full Screen]                │
│                                                 │
│  ┌──────────────────────────────────────────┐   │
│  │  Canvas Layer (Bounding Boxes)           │   │
│  └──────────────────────────────────────────┘   │
│                                                 │
│  ┌────────────────────┐  ┌──────────────────┐   │
│  │ Recent Scans       │  │ System Status    │   │
│  │ 08:31 สมชาย ใจดี  │  │ CPU: 18%         │   │
│  │ 08:30 มานะ มั่งมี  │  │ Online ✅        │   │
│  └────────────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────┘
```

### Dual-Layer Rendering

**Layer 1 — Canvas (สำหรับ Bounding Box):**
- วาดด้วย `<canvas>` ที่ overlay ทับ `<video>`
- อัปเดตทุก animation frame
- ใช้ Linear Interpolation (Lerp) เพื่อให้กรอบเคลื่อนที่นุ่มนวล ไม่สั่น

**Layer 2 — Vue DOM (สำหรับ Identity Card):**
- แสดงชื่อ + แผนก + เวลา
- ใช้ Vue `Transition` สำหรับ Fade-in เมื่อระบุตัวตนได้
- Position คำนวณจาก bbox ที่ได้รับจาก WebSocket

### Overlay States

| State | สีกรอบ | แสดงข้อมูล | Animation |
|-------|--------|-----------|----------|
| `processing` | เหลือง (dashed) | "กำลังประมวลผล..." | Pulse |
| `identified` | เขียว (solid) | ชื่อ + แผนก + เวลา | Fade-in |
| `unknown` | แดง (solid) | "Unknown" | Static |
| `low_confidence` | ส้ม (dashed) | ชื่อ + ⚠️ | Fade-in |

### Identity Card Component

```
┌──────────────────────┐
│ ● สมชาย ใจดี        │  ← DaisyUI card, ขนาดเล็ก
│   ฝ่ายสืบสวน         │
│   08:31:05 ✅        │
└──────────────────────┘
```

### Collision Avoidance (10 คนพร้อมกัน)

เมื่อ Identity Cards ทับกัน:
1. Card ของคนที่อยู่ใกล้กว่า (bbox ใหญ่กว่า) มี Priority สูงกว่า
2. Card ที่ต้องถอยใช้ Adaptive Offset ขยับขึ้น/ซ้าย/ขวา
3. ถ้าขยับแล้วยังทับ → วาด Leader Line เชื่อมกลับไปที่ใบหน้า

---

## Face Enrollment Page

### Layout

```
┌─────────────────────────────────────────────────┐
│  ลงทะเบียนใบหน้า: สมชาย ใจดี (EMP001)          │
├─────────────────────────────────────────────────┤
│                                                 │
│         [Camera Preview - กึ่งหน้าจอ]          │
│         [Guide Text: "หันหน้าตรง"]             │
│                                                 │
│  ┌───┬───┬───┬───┬───┬───┐                     │
│  │ 1 │ 2 │ 3 │ 4 │ 5 │ 6 │  ← Photo Slots     │
│  │✅ │✅ │ ⬜ │ ⬜ │ ⬜ │ ⬜ │                     │
│  └───┴───┴───┴───┴───┴───┘                     │
│                                                 │
│  [ปุ่ม Auto-Capture]  [ปุ่ม Manual]            │
│                                                 │
│  Quality: ████████░░ 80%                       │
└─────────────────────────────────────────────────┘
```

### Guide ทั้ง 6 ช่อง

| ช่อง | คำแนะนำ | เงื่อนไข Auto-capture |
|-----|---------|---------------------|
| 1 | หน้าตรง มองกล้อง | Straight + quality > 0.8 |
| 2 | เอียงซ้ายเล็กน้อย (~15°) | Left yaw detected |
| 3 | เอียงขวาเล็กน้อย (~15°) | Right yaw detected |
| 4 | ก้มเล็กน้อย | Down pitch detected |
| 5 | เงยเล็กน้อย | Up pitch detected |
| 6 | หน้าตรง ยิ้ม | Different expression |

### Quality Indicator (Real-time)
- **แสง:** แถบวัด Brightness
- **ความชัด:** Blur Score
- **ระยะ:** ขนาด Face Area vs Frame

เมื่อคุณภาพผ่านทุกเงื่อนไข → Auto-capture ทันที (HR ไม่ต้องกด)

### Editing Existing Slot
- คลิกที่ช่องที่มีรูปแล้ว → เปิดกล้องถ่ายใหม่
- ระบบลบ Embedding เก่า → บันทึก Embedding ใหม่
- ไม่กระทบช่องอื่น

---

## Admin Dashboard

### Widgets (DaisyUI Stats)

```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│ พนักงานทั้งหมด│ ลงทะเบียนแล้ว│ สแกนวันนี้   │ Station Online│
│   10,000    │   9,850     │    1,234    │    8/10     │
│             │  (98.5%)    │             │             │
└─────────────┴─────────────┴─────────────┴─────────────┘
```

---

## Station Manager

### Station Card

```
┌──────────────────────────────────────┐
│ 📷 ประตูหน้า อาคาร A          [✅ ON]│
│ แผนก: ฝ่ายสืบสวน, ฝ่ายป้องกัน       │
│ สแกนวันนี้: 245 ครั้ง              │
│ [แก้ไข] [ตั้ง Scope] [ปิดกล้อง]    │
└──────────────────────────────────────┘
```

### Scope Configuration (DaisyUI Multi-select)

```
กำหนดแผนกที่สแกนได้:
☑ ฝ่ายสืบสวน (320 คน)
☑ ฝ่ายป้องกัน (280 คน)
☐ ฝ่ายธุรการ (150 คน)

Search Space ปัจจุบัน: 600 / 10,000 คน
ความเร็วโดยประมาณ: ~3ms
```

---

## State Management (Pinia)

```javascript
// stores/scan.js
const useScanStore = defineStore('scan', {
  state: () => ({
    faces: [],          // [{tracking_id, status, employee, bbox}]
    recentLogs: [],     // 5 รายการล่าสุด
    systemStatus: {}    // CPU, connection status
  }),
  actions: {
    updateFaces(data) { ... },   // เรียกเมื่อ WebSocket ส่งมา
    addToRecent(log) { ... }
  }
})
```

---

## WebSocket Client (Vue Composable)

```javascript
// composables/useScanSocket.js
export function useScanSocket(stationId) {
  const ws = ref(null)
  const { updateFaces } = useScanStore()

  function connect() {
    ws.value = new WebSocket(`ws://localhost:8000/ws/scan/${stationId}`)
    ws.value.onmessage = (event) => {
      const data = JSON.parse(event.data)
      updateFaces(data.faces)
    }
  }

  function sendFrame(imageBlob) {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(imageBlob)  // ส่งเป็น Binary
    }
  }

  return { connect, sendFrame }
}
```
