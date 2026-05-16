# Chapter 2: Use Cases & Actors

## Actors

### Human Actors

| Actor | คำอธิบาย | สิทธิ์ |
|-------|---------|-------|
| **Employee** | พนักงานทั่วไปที่ใช้ระบบเช็คชื่อ | เช็คชื่อ, ดูประวัติตัวเอง |
| **HR / Admin** | ผู้ดูแลระบบ ลงทะเบียนพนักงาน จัดการข้อมูล | ทุกอย่างยกเว้น System Config |
| **Super Admin** | ผู้ดูแลระบบระดับสูงสุด | รวมถึงจัดการ Station, Department, User |

### System Actor

| Actor | คำอธิบาย |
|-------|---------|
| **AI Engine** | ระบบ Backend ที่ทำ Detection, Recognition, Logging อัตโนมัติ |

---

## Core Entities

| Entity | คำอธิบาย | Attributes หลัก |
|--------|---------|----------------|
| Employee | ข้อมูลพนักงาน | id, emp_code, full_name, dept_id, shift_id |
| Department | หน่วยงาน/แผนก | id, name |
| Shift | กะการทำงาน (เก็บไว้ทำ Report) | id, name, start_time, end_time |
| Station | กล้องสแกนแต่ละจุด | id, name, location, is_active |
| FaceTemplate | เวกเตอร์ใบหน้า 1 ใน 6 | id, employee_id, qdrant_id, sample_index |
| AttendanceLog | บันทึกการสแกน | id, employee_id, station_id, timestamp, confidence_score |

---

## Use Cases

---

### UC-01: Frictionless Entry (เช็คชื่อเข้า-ออกงาน)

**Actor:** Employee, AI Engine  
**Priority:** สูงสุด

**คำอธิบาย:**  
พนักงานเดินผ่านจุดสแกน ระบบตรวจจับและระบุตัวตนโดยอัตโนมัติ บันทึก Timestamp ทันที

**Flow:**
```
1. พนักงานเดินเข้าสู่ระยะกล้อง
2. AI Engine ตรวจจับใบหน้า
3. ระบบกรองค้นหาเฉพาะแผนกที่ Station นั้นรับผิดชอบ
4. Match สำเร็จ → บันทึก AttendanceLog
5. Overlay แสดงชื่อ + แผนก + เวลา (กรอบเขียว)
6. ไม่ Match → แสดง Unknown (กรอบแดง)
```

**Overlay ที่แสดง:**
- กรอบใบหน้า (สีตามสถานะ)
- ชื่อพนักงาน + แผนก
- Timestamp ที่บันทึก

---

### UC-02: Multi-Person Meeting Attendance (เช็คชื่อกลุ่ม)

**Actor:** HR/Admin, AI Engine  
**Priority:** สูง

**คำอธิบาย:**  
ส่องกล้องไปที่กลุ่มคน 1-10 คนพร้อมกัน เช็คว่าใครมาครบหรือยัง

**Flow:**
```
1. HR เปิดโหมด Meeting Scan
2. ส่องกล้องไปที่กลุ่มคน
3. ระบบ Scan ทุกใบหน้าในเฟรมพร้อมกัน (Batch)
4. แสดงชื่อลอยอยู่บนหัวแต่ละคน
5. Counter แสดง "ระบุได้ X / ทั้งหมด N"
```

**Overlay ที่แสดง:**
- Floating Label บนแต่ละใบหน้า
- Counter รวมมุมบนของเฟรม
- Collision Avoidance (ป้ายชื่อไม่ทับกัน)

---

### UC-03: Field-Work Verification (ลงเวลานอกสถานที่)

**Actor:** Employee, AI Engine  
**Priority:** ปานกลาง

**คำอธิบาย:**  
พนักงานใช้ Laptop/Tablet สแกนหน้าตัวเองที่ไซต์งาน

**Flow:**
```
1. พนักงานเปิดหน้า Self-Check ผ่าน Browser
2. ระบบสแกนหน้า
3. บันทึก Timestamp + Station ID ของอุปกรณ์นั้น
4. แสดงสถานะ Network Sync (Online/Offline Buffer)
```

---

### UC-04: Restricted Area & Unknown Alert (แจ้งเตือนบุคคลต้องสงสัย)

**Actor:** AI Engine, HR/Admin  
**Priority:** ปานกลาง

**คำอธิบาย:**  
ระบบแจ้งเตือนเมื่อพบใบหน้าที่ไม่อยู่ใน Search Scope ของ Station นั้น (Strict Mode)

**Flow:**
```
1. กล้องตรวจพบใบหน้า
2. ค้นหาใน Scope ของ Station (แผนกที่กำหนด)
3. ไม่พบ Match → ขึ้น "Unknown" กรอบสีแดง
4. บันทึก Unknown Log + Timestamp
```

**Overlay ที่แสดง:**
- กรอบสีแดง + ป้าย "Unknown"
- ไม่แสดงชื่อใด ๆ

---

### UC-05: Health & Safety Compliance (ตรวจ PPE)

**Actor:** AI Engine  
**Priority:** ต่ำ (Phase ถัดไป)

**คำอธิบาย:**  
ตรวจสอบว่าพนักงานสวมอุปกรณ์ความปลอดภัยก่อนเข้าพื้นที่

---

## Use Case ของ HR/Admin

| Use Case | คำอธิบาย |
|---------|---------|
| UC-A1: Register Employee | เพิ่มข้อมูลพนักงานใหม่ |
| UC-A2: Face Enrollment | ถ่ายรูปพนักงาน 6 ท่าและบันทึก Embedding |
| UC-A3: Edit Face Template | แก้ไขรูปบางช่องโดยไม่ต้องถ่ายใหม่ทั้งหมด |
| UC-A4: Manage Station | เพิ่ม/แก้ไข/เปิด-ปิด Station |
| UC-A5: Configure Scope | กำหนดว่า Station ดูแลแผนกไหนบ้าง |
| UC-A6: View Attendance Report | ดูรายงานการเข้างานตามช่วงเวลา |
| UC-A7: Manual Log Override | แก้ไข Log กรณีระบบมีปัญหา |

---

## Diagram (Use Case Overview)

```
┌─────────────────────────────────────────┐
│              OmniSight System           │
│                                         │
│  [UC-01] Frictionless Entry             │
│  [UC-02] Meeting Attendance             │
│  [UC-03] Field-Work Verification        │
│  [UC-04] Unknown Alert                  │
│  [UC-A1] Register Employee              │
│  [UC-A2] Face Enrollment                │
│  [UC-A3] Edit Face Template             │
│  [UC-A4] Manage Station                 │
│  [UC-A5] Configure Scope               │
│  [UC-A6] Attendance Report              │
└─────────────────────────────────────────┘
     ↑              ↑              ↑
 Employee        HR/Admin       AI Engine
```
