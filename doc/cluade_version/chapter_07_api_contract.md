# Chapter 7: API Contract

## หลักการ: API-First Design

กำหนด Contract ระหว่าง Frontend และ Backend ให้ชัดเจนก่อนเขียนโค้ด

- Base URL: `http://localhost:8000/api/v1`
- Format: JSON (REST) + Binary WebSocket (Scan)
- Auth: Bearer Token (JWT)
- Docs: `/docs` (Swagger UI อัตโนมัติจาก FastAPI)

---

## Authentication

```
POST /auth/login
Body: { username, password }
Response: { access_token, token_type }

Header ทุก Request:
  Authorization: Bearer {access_token}
```

---

## Departments

```
GET    /departments          → รายการแผนกทั้งหมด
POST   /departments          → สร้างแผนกใหม่
PUT    /departments/{id}     → แก้ไขชื่อแผนก
DELETE /departments/{id}     → ลบแผนก
```

---

## Shifts

```
GET    /shifts               → รายการกะทั้งหมด
POST   /shifts               → สร้างกะใหม่
PUT    /shifts/{id}          → แก้ไขกะ
DELETE /shifts/{id}          → ลบกะ
```

---

## Employees

```
GET    /employees                     → รายการพนักงาน (pagination)
GET    /employees/{id}                → ข้อมูลพนักงาน + สถานะ Enrollment
POST   /employees                     → เพิ่มพนักงานใหม่
PUT    /employees/{id}                → แก้ไขข้อมูล
DELETE /employees/{id}                → ลบพนักงาน (cascade ทุกอย่าง)
PATCH  /employees/{id}/activate       → เปิด/ปิดใช้งาน
```

### GET /employees Response
```json
{
  "id": "uuid",
  "emp_code": "EMP001",
  "full_name": "สมชาย ใจดี",
  "dept_id": 1,
  "dept_name": "ฝ่ายสืบสวน",
  "shift_id": 1,
  "shift_name": "กะเช้า",
  "is_active": true,
  "enrollment_status": {
    "completed": 5,
    "total": 6,
    "is_ready": false
  }
}
```

---

## Face Enrollment

```
GET    /employees/{id}/face-templates        → รายการ 6 ช่อง + สถานะแต่ละช่อง
POST   /employees/{id}/face-templates        → เพิ่มรูปใหม่ (ส่ง multipart/form-data)
PUT    /employees/{id}/face-templates/{idx}  → แทนที่รูปช่อง idx (1-6)
DELETE /employees/{id}/face-templates/{idx}  → ลบรูปช่อง idx
```

### POST /employees/{id}/face-templates Body
```
Content-Type: multipart/form-data
Fields:
  sample_index : int (1-6)
  image        : file (JPEG/PNG)
```

### Response
```json
{
  "sample_index": 1,
  "quality_score": 0.93,
  "status": "success",
  "message": "Face template saved"
}
```

### Quality Check Error Response
```json
{
  "status": "error",
  "code": "QUALITY_FAILED",
  "reason": "BLURRY",
  "message": "ภาพไม่ชัดเพียงพอ กรุณาถ่ายใหม่"
}
```

### Quality Failure Codes
| Code | ความหมาย |
|------|---------|
| `NO_FACE` | ไม่พบใบหน้าในรูป |
| `MULTIPLE_FACES` | พบมากกว่า 1 ใบหน้า |
| `BLURRY` | ภาพเบลอ |
| `DARK` | แสงน้อยเกินไป |
| `FACE_TOO_SMALL` | ใบหน้าอยู่ห่างกล้องเกินไป |

---

## Stations

```
GET    /stations                    → รายการ Station ทั้งหมด
GET    /stations/{id}               → ข้อมูล Station + dept_ids
POST   /stations                    → สร้าง Station ใหม่
PUT    /stations/{id}               → แก้ไข Station
DELETE /stations/{id}               → ลบ Station
PATCH  /stations/{id}/activate      → เปิด/ปิด Station

PUT    /stations/{id}/departments   → กำหนดแผนกที่รับผิดชอบ (แทนที่ทั้งหมด)
```

### PUT /stations/{id}/departments Body
```json
{
  "dept_ids": [1, 2, 3]
}
```

---

## Active Filter (Admin Control)

```
GET    /stations/{id}/filter        → ดู Filter ที่ Active อยู่
PUT    /stations/{id}/filter        → ตั้ง Filter ใหม่ (ส่งไปที่ Redis)
DELETE /stations/{id}/filter        → Reset → ใช้ dept_ids ทั้งหมดของ Station
```

---

## Attendance Logs

```
GET /attendance/logs                → ดู Log (filter by: date, employee, station)
GET /attendance/logs/{employee_id}  → ประวัติของพนักงานคนหนึ่ง
GET /attendance/report              → รายงานสรุป (by dept, by date range)

POST /attendance/logs               → Manual Override (Admin only)
PUT  /attendance/logs/{id}          → แก้ไข Log (Admin only)
```

### GET /attendance/logs Query Params
```
?date_from=2024-01-01
&date_to=2024-01-31
&employee_id=uuid
&station_id=uuid
&dept_id=1
&page=1
&limit=50
```

---

## WebSocket: Real-time Face Scan

```
WS /ws/scan/{station_id}
```

### Client → Server (Binary Frame)
```
Format: Binary (JPEG bytes)
ส่ง: Full frame จากกล้อง (หรือ Cropped faces ถ้า Frontend ทำ pre-crop)
```

### Server → Client (JSON)
```json
{
  "timestamp": "2024-01-15T08:30:01Z",
  "faces": [
    {
      "tracking_id": 1,
      "status": "identified",
      "employee": {
        "id": "uuid",
        "full_name": "สมชาย ใจดี",
        "dept_name": "ฝ่ายสืบสวน",
        "emp_code": "EMP001"
      },
      "confidence": 0.94,
      "bbox": { "x": 120, "y": 80, "w": 150, "h": 180 }
    },
    {
      "tracking_id": 2,
      "status": "unknown",
      "employee": null,
      "confidence": 0.0,
      "bbox": { "x": 400, "y": 100, "w": 140, "h": 170 }
    }
  ]
}
```

### Status Values
| Status | ความหมาย | Overlay สี |
|--------|---------|-----------|
| `identified` | ระบุตัวตนได้ | เขียว |
| `processing` | กำลังประมวลผล | เหลือง |
| `unknown` | ไม่พบในระบบ | แดง |
| `low_confidence` | Match แต่ไม่แน่ใจ | ส้ม |

---

## Error Response Standard

```json
{
  "status": "error",
  "code": "EMPLOYEE_NOT_FOUND",
  "message": "ไม่พบพนักงานรหัส EMP999",
  "detail": {}
}
```

---

## HTTP Status Codes

| Code | ใช้เมื่อ |
|------|--------|
| 200 | สำเร็จ (GET, PUT, PATCH) |
| 201 | สร้างสำเร็จ (POST) |
| 400 | ข้อมูลที่ส่งมาผิด |
| 401 | ไม่ได้ Login |
| 403 | ไม่มีสิทธิ์ |
| 404 | ไม่พบข้อมูล |
| 422 | Validation Error (Pydantic) |
| 500 | Server Error |
