# OmniSight API Reference

> Base URL: `http://localhost:8000` (dev) / `https://your-server` (prod)
> Interactive docs: `GET /docs` (Swagger UI)
> Auth: Bearer token จาก `POST /api/v1/auth/login`

---

## Authentication

### Login

```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=admin&password=admin
```

**Response:**
```json
{
  "access_token": "eyJhbG...",
  "token_type": "bearer"
}
```

**ใช้ token ใน request ถัดไป:**
```http
Authorization: Bearer eyJhbG...
```

### ดูข้อมูล user ปัจจุบัน

```http
GET /api/v1/auth/me
Authorization: Bearer <token>
```

---

## Employees

| Method | Path | Description | Role |
|--------|------|-------------|------|
| GET | `/api/v1/employees` | รายชื่อพนักงานทั้งหมด | HR+ |
| POST | `/api/v1/employees` | เพิ่มพนักงานใหม่ | HR+ |
| GET | `/api/v1/employees/{id}` | ดูข้อมูลพนักงาน 1 คน | HR+ |
| PATCH | `/api/v1/employees/{id}` | แก้ไขข้อมูลพนักงาน | HR+ |
| DELETE | `/api/v1/employees/{id}` | ลบพนักงาน | ADMIN |

### เพิ่มพนักงาน

```http
POST /api/v1/employees
Authorization: Bearer <token>
Content-Type: application/json

{
  "emp_code": "EMP001",
  "full_name": "สมชาย ใจดี",
  "department_id": "uuid-ของ-department",
  "shift_id": "uuid-ของ-shift"
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "emp_code": "EMP001",
  "full_name": "สมชาย ใจดี",
  "is_active": true,
  "enrollment_count": 0
}
```

### แก้ไขพนักงาน

```http
PATCH /api/v1/employees/{id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "full_name": "สมชาย มีสุข",
  "is_active": false
}
```

---

## Attendance

| Method | Path | Description | Role |
|--------|------|-------------|------|
| GET | `/api/v1/attendance` | Attendance log | HR+ |
| GET | `/api/v1/attendance/kpi` | KPI summary วันนี้ | ANY |
| GET | `/api/v1/attendance/daily-report` | รายงานรายวัน | HR+ |
| GET | `/api/v1/attendance/daily-report/pdf` | PDF รายวัน | HR+ |
| GET | `/api/v1/attendance/summary` | สรุปรายเดือน | HR+ |
| GET | `/api/v1/attendance/summary/pdf` | PDF รายเดือน | HR+ |

### Attendance Log

```http
GET /api/v1/attendance?limit=50&date=2026-05-21&employee_id=uuid
Authorization: Bearer <token>
```

**Query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 100 | จำนวนสูงสุด |
| `offset` | int | 0 | skip กี่ record |
| `date` | YYYY-MM-DD | วันนี้ | กรองตามวัน |
| `employee_id` | UUID | - | กรองตามพนักงาน |

### KPI Summary

```http
GET /api/v1/attendance/kpi
Authorization: Bearer <token>
```

**Response:**
```json
{
  "date": "2026-05-21",
  "today": {
    "present": 127,
    "late": 8,
    "absent": 15
  },
  "weekly": [
    {"date": "2026-05-15", "count": 120},
    {"date": "2026-05-16", "count": 118},
    ...
  ],
  "by_dept": [
    {"dept_name": "วิศวกรรม", "count": 45},
    ...
  ]
}
```

### รายงานรายวัน

```http
GET /api/v1/attendance/daily-report?date=2026-05-21&dept_id=uuid
Authorization: Bearer <token>
```

**Response:**
```json
{
  "date": "2026-05-21",
  "late_threshold_minutes": 15,
  "records": [
    {
      "employee_id": "uuid",
      "emp_code": "EMP001",
      "full_name": "สมชาย ใจดี",
      "dept_name": "วิศวกรรม",
      "first_seen": "2026-05-21T07:58:00Z",
      "status": "PRESENT"
    }
  ]
}
```

### Export PDF

```http
GET /api/v1/attendance/daily-report/pdf?date=2026-05-21
Authorization: Bearer <token>
```

**Response:** `application/pdf` binary
**Headers:** `Content-Disposition: attachment; filename="attendance_daily_2026-05-21.pdf"`

### สรุปรายเดือน

```http
GET /api/v1/attendance/summary?month=2026-05&dept_id=uuid
Authorization: Bearer <token>
```

**Query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `month` | YYYY-MM | เดือนนี้ | เดือนที่ต้องการ |
| `dept_id` | UUID | - | กรองตามแผนก |

---

## Face Enrollment

| Method | Path | Description | Role |
|--------|------|-------------|------|
| GET | `/api/v1/employees/{id}/enrollments` | ดู templates ของพนักงาน | HR+ |
| POST | `/api/v1/employees/{id}/enroll` | บันทึกใบหน้าใหม่ | HR+ |
| DELETE | `/api/v1/employees/{id}/enrollments` | ลบ templates ทั้งหมด | HR+ |

### Enroll ใบหน้า

```http
POST /api/v1/employees/{id}/enroll
Authorization: Bearer <token>
Content-Type: multipart/form-data

file=<image_file>
```

**Response 200:**
```json
{
  "message": "Enrolled successfully",
  "enrollment_count": 3,
  "max_enrollments": 6
}
```

**Response 422 (liveness failed):**
```json
{
  "detail": "Liveness check failed (score: 0.12). Use a real face, not a photo."
}
```

---

## Stations

| Method | Path | Description | Role |
|--------|------|-------------|------|
| GET | `/api/v1/stations` | รายการ station | ANY |
| POST | `/api/v1/stations` | เพิ่ม station | ADMIN |
| GET | `/api/v1/stations/{id}` | ดูรายละเอียด | ANY |
| PATCH | `/api/v1/stations/{id}` | แก้ไข | ADMIN |
| DELETE | `/api/v1/stations/{id}` | ลบ | ADMIN |

---

## Departments

| Method | Path | Description | Role |
|--------|------|-------------|------|
| GET | `/api/v1/departments` | รายการแผนก | ANY |
| POST | `/api/v1/departments` | เพิ่มแผนก | ADMIN |
| PATCH | `/api/v1/departments/{id}` | แก้ไข | ADMIN |
| DELETE | `/api/v1/departments/{id}` | ลบ | ADMIN |

---

## Settings

| Method | Path | Description | Role |
|--------|------|-------------|------|
| GET | `/api/v1/settings` | ดูค่าตั้งทั้งหมด | ADMIN |
| PATCH | `/api/v1/settings/{key}` | เปลี่ยนค่า setting | ADMIN |

### เปลี่ยนค่า Setting

```http
PATCH /api/v1/settings/match_threshold
Authorization: Bearer <token>
Content-Type: application/json

{"value": "0.75"}
```

**Setting keys สำคัญ:**

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `work_start_time` | string | `"08:00"` | เวลาเริ่มงาน (HH:MM) |
| `late_threshold_minutes` | int | `15` | นาทีที่ถือว่าสาย |
| `match_threshold` | float | `0.72` | ความเชื่อมั่นขั้นต่ำ |
| `inference_workers` | int | `4` | จำนวน AI threads |
| `max_fps_per_camera` | int | `2` | FPS ต่อกล้อง |
| `anti_spoof_enabled` | int | `0` | เปิด liveness (1=เปิด) |
| `recognition_cache_ttl` | int | `30` | Cache TTL (วินาที) |

---

## Health & Metrics

```http
GET /health
```

```json
{"status": "ok", "version": "1.0.0"}
```

```http
GET /metrics
```

Prometheus text format — ใช้สำหรับ Grafana scraping

**Metrics สำคัญ:**

| Metric | Type | Description |
|--------|------|-------------|
| `omnisight_frames_received_total` | Counter | Frames ที่รับมาทั้งหมด |
| `omnisight_frames_dropped_total` | Counter | Frames ที่ error |
| `omnisight_active_cameras` | Gauge | กล้องที่เชื่อมต่ออยู่ |
| `omnisight_inference_duration_seconds` | Histogram | เวลา inference AI |
| `omnisight_qdrant_search_duration_seconds` | Histogram | เวลา search vector |
| `omnisight_attendance_logged_total` | Counter | จำนวนที่ log attendance |
| `omnisight_cache_hits_total` | Counter | Cache hit |
| `omnisight_cache_misses_total` | Counter | Cache miss |

---

## WebSocket — Camera Stream

```
ws://localhost:8000/ws/camera?station_id={id}&camera_id={id}
```

**Protocol:**
1. Client ส่ง binary frame (JPEG bytes)
2. Server ตอบกลับ JSON text:

```json
{
  "faces": [
    {
      "tracking_id": 1,
      "bbox": [x, y, w, h],
      "status": "recognized",
      "employee_id": "uuid",
      "full_name": "สมชาย ใจดี",
      "emp_code": "EMP001",
      "confidence": 0.85,
      "attendance_logged": true
    }
  ]
}
```

**status values:**
- `recognized` — จำใบหน้าได้
- `unknown` — ไม่รู้จัก
- `spoof` — ตรวจพบการปลอมแปลง (liveness failed)
- `low_quality` — ภาพไม่ชัดพอ

---

## Error Codes

| Status | ความหมาย |
|--------|---------|
| 200 | สำเร็จ |
| 201 | สร้างข้อมูลใหม่สำเร็จ |
| 400 | ข้อมูลผิดรูปแบบ |
| 401 | ไม่ได้ login หรือ token หมดอายุ |
| 403 | ไม่มีสิทธิ์ |
| 404 | ไม่พบข้อมูล |
| 409 | ข้อมูลซ้ำ (เช่น emp_code ซ้ำ) |
| 422 | Validation error (ข้อมูลที่ส่งไม่ถูกต้อง) |
| 500 | Server error |

---

*Full interactive docs: `http://localhost:8000/docs` (Swagger UI)*
*อัปเดตล่าสุด: 2026-05-21 (Sprint 24)*
