# Chapter 9: Shift & Scope Management

## หลักการที่ตกลงกัน

> **ระบบสแกนหน้า = บันทึก Timestamp เท่านั้น**
> **Shift = ข้อมูลอ้างอิงสำหรับ HR Report เท่านั้น**
> **Scope = แผนกของ Station ที่ Admin กำหนด**

Shift ไม่มีผลต่อ Logic การสแกน ไม่ Block ไม่ Filter

---

## Shift Management

### วัตถุประสงค์

| ใช้เพื่อ | ไม่ใช้เพื่อ |
|---------|-----------|
| ดึงข้อมูลใน HR Report ("พนักงานกะเช้าสายกี่คน") | Filter การสแกน |
| แสดงในหน้า Employee Profile | Block พนักงานสแกนนอกเวลา |
| คำนวณ OT ใน Report | เปลี่ยน Search Space |

### Schema

```sql
shifts
├── id         SMALLINT
├── name       "กะเช้า"
├── start_time 08:30
└── end_time   17:30
```

### ตัวอย่าง Shift

| ชื่อ | เวลา |
|-----|------|
| กะเช้า | 08:30 - 17:30 |
| กะบ่าย | 14:00 - 23:00 |
| กะดึก | 22:00 - 07:00 |
| ยืดหยุ่น | ไม่กำหนด |

Admin สร้าง Shift ได้ N กะ ไม่จำกัด

### การใช้ใน Report

```
HR ต้องการรายงาน:
"พนักงานกะเช้า วันที่ 15 มกราคม 2567 มาสาย"

Query:
  attendance_logs.timestamp > shift.start_time  → ปกติ
  attendance_logs.timestamp < shift.start_time  → มาก่อน (Early)
  attendance_logs.timestamp > shift.start_time + 15min → สาย

หมายเหตุ: ระบบ OmniSight แค่เก็บ timestamp
          HR Report Engine ทำการตัดสินเองว่าสายหรือไม่
```

---

## Scope Management (Station Filter)

### แนวคิด: "Search Space Partitioning"

Admin กำหนดว่าแต่ละกล้องจะ "เห็น" พนักงานกลุ่มไหน

```
Station "ประตูหน้า อาคาร A"
  dept_ids: [1, 2]  ← ฝ่ายสืบสวน (300 คน) + ฝ่ายป้องกัน (280 คน)

เมื่อมีคนเดินผ่าน:
  Search Space = 580 คน × 6 vectors = 3,480 vectors
  (จากทั้งหมด 60,000 vectors)
```

### ผลลัพธ์ด้าน Performance

| Search Space | เวลา Qdrant | ความแม่นยำ |
|-------------|------------|-----------|
| 60,000 vectors (ไม่มี Filter) | ~15ms | ปกติ |
| 3,480 vectors (Filter 2 แผนก) | ~2ms | ดีขึ้น (false positive น้อยลง) |
| 600 vectors (Filter 1 แผนก) | < 1ms | ดีที่สุด |

### Active Filter Flow

```
Admin เลือก Scope ใน Dashboard
    ↓
PUT /stations/{id}/filter
Body: { "dept_ids": [1, 2] }
    ↓
FastAPI บันทึกใน Redis
Key: "station:{id}:filter"
Value: [1, 2]
    ↓
ทุก Scan Request:
  FastAPI ดึง dept_ids จาก Redis
  ส่งไปกับ Qdrant Search เป็น Filter
```

### Default Scope

ถ้า Admin ไม่ได้ตั้ง Filter → ใช้ dept_ids ทั้งหมดของ Station จาก `station_departments` โดยอัตโนมัติ

### Strict Mode (ที่ตกลงกัน)

พนักงานที่ **ไม่อยู่ใน Scope** ของ Station → ระบบมองไม่เห็น → Unknown

```
สถานการณ์:
  Station A ดูแล [แผนกสืบสวน, แผนกป้องกัน]
  พนักงานแผนก HR เดินผ่าน

ผลลัพธ์:
  Qdrant Filter: dept_id IN [1, 2]
  พนักงาน HR มี dept_id = 5
  → ไม่อยู่ใน Search Space
  → Score < threshold
  → แสดง "Unknown" (กรอบแดง)
  → บันทึก Unknown Log
```

---

## Admin UI: Scope Configuration

### Station Card + Scope Panel

```
┌──────────────────────────────────────────────────┐
│ Scope Configuration: ประตูหน้า อาคาร A           │
├──────────────────────────────────────────────────┤
│ แผนกที่สแกนได้:                                  │
│                                                  │
│  ☑ ฝ่ายสืบสวน        (300 คน, 1,800 vectors)   │
│  ☑ ฝ่ายป้องกัน       (280 คน, 1,680 vectors)   │
│  ☐ ฝ่ายธุรการ        (150 คน, 900 vectors)     │
│  ☐ ฝ่ายการเงิน       (120 คน, 720 vectors)     │
│                                                  │
│  Search Space: 580 / 10,000 คน                  │
│  ████░░░░░░░░░░░░░░░░ 5.8%                      │
│  เวลาค้นหาโดยประมาณ: ~2ms                      │
│                                                  │
│  [บันทึก Scope]  [Reset เป็นค่าเริ่มต้น]        │
└──────────────────────────────────────────────────┘
```

---

## HR Report: ตัวอย่าง Query

```sql
-- รายงานการเข้างานรายวัน พร้อมข้อมูลกะ
SELECT
    e.full_name,
    e.emp_code,
    d.name AS dept_name,
    s.name AS shift_name,
    s.start_time AS shift_start,
    al.timestamp AS scan_time,
    CASE
        WHEN al.timestamp::time <= s.start_time THEN 'ตรงเวลา'
        WHEN al.timestamp::time <= s.start_time + INTERVAL '15 min' THEN 'สายเล็กน้อย'
        ELSE 'สาย'
    END AS status
FROM attendance_logs al
JOIN employees e ON al.employee_id = e.id
JOIN departments d ON e.dept_id = d.id
LEFT JOIN shifts s ON e.shift_id = s.id
WHERE al.timestamp::date = '2024-01-15'
ORDER BY al.timestamp;
```

OmniSight เพียงแค่เก็บ `attendance_logs` ส่วน Logic ว่าสายหรือไม่ขึ้นอยู่กับ Report Layer ของ HR
