# Chapter 10: Anti-Spoofing & Security

## ภัยคุกคามที่ต้องรับมือ

| ภัยคุกคาม | คำอธิบาย | ความเสี่ยง |
|----------|---------|-----------|
| Photo Attack | นำรูปถ่ายพนักงานมาจ่อกล้อง | สูง |
| Video Replay | เปิดวิดีโอพนักงานจากมือถือ | สูง |
| 3D Mask | ใช้หน้ากากซิลิโคน | ต่ำ (ราคาแพง) |
| Deepfake | วิดีโอ AI สร้างใบหน้า | ต่ำ (ยังไม่แพร่หลาย) |
| Data Breach | ขโมยข้อมูล Embedding | ปานกลาง |

---

## Anti-Spoofing Strategy (CPU-Only)

เราไม่มี GPU แต่ยังมีวิธีป้องกันที่ได้ผลดีบน Ryzen CPU

---

### Level 1: Texture Analysis (Passive Liveness)

ตรวจสอบ "ความลึก" ของผิวหนังโดยไม่ต้องให้พนักงานขยับ

**วิธี: MiniFASNet (ONNX)**
- Model ขนาดเล็ก (~1.2 MB) รันบน CPU ได้เร็วมาก
- ตรวจสอบ Texture Pattern ที่ต่างกันระหว่าง "หน้าจริง" กับ "หน้าในรูป/จอ"
- เวลาประมวลผล: ~20-30ms บน Ryzen

```
รูปถ่ายบนกระดาษ/จอ → Texture แบน → Score ต่ำ → Reject
ใบหน้าจริง → Texture มี depth → Score สูง → Pass
```

**Threshold แนะนำ:** > 0.8 = Liveness Pass

---

### Level 2: Motion Challenge (Active Liveness)

สำหรับจุดสแกนที่ความปลอดภัยสูง เช่น ห้องข้อมูลลับ

พนักงานต้องทำ Micro-movement ตามที่ระบบสั่ง:

| Challenge | วิธีตรวจ | เวลา |
|----------|---------|-----|
| กระพริบตา | ตรวจ Eye Aspect Ratio (EAR) เปลี่ยน | < 3 วินาที |
| พยักหน้า | ตรวจ Head Pose ขึ้น-ลง | < 3 วินาที |
| หันซ้าย-ขวา | ตรวจ Yaw angle เปลี่ยน | < 3 วินาที |

ระบบสุ่มเลือก 1 Challenge ต่อการสแกน 1 ครั้ง

> ใช้เฉพาะ Station ที่ Admin กำหนดว่าต้องการ Active Liveness เท่านั้น

---

### Anti-Spoofing Pipeline

```
รับภาพใบหน้า
    ↓
[Level 1] MiniFASNet Texture Check
    ├── Score > 0.8 → Pass → ไปต่อ Recognition
    └── Score < 0.8 → Fail → แสดง "กรุณาแสดงใบหน้าจริง"
    ↓
[Level 2 - ถ้า Station ต้องการ]
Random Challenge → ตรวจ Motion
    ├── Pass → ไปต่อ Recognition
    └── Fail → บันทึก Suspicious Log + Alert
    ↓
Face Recognition (Qdrant Search)
```

---

## Data Security

### 1. ไม่เก็บรูปภาพใบหน้าใน Database

```
✅ เก็บ: Embedding Vector (ตัวเลข 512 มิติ)
✅ เก็บ: รูปต้นฉบับบน Disk (/storage/faces/)
❌ ไม่เก็บ: รูปภาพใน PostgreSQL หรือ Qdrant
```

Embedding ไม่สามารถย้อนกลับมาเป็นรูปหน้าคนได้ → ปลอดภัยตาม PDPA

### 2. Encryption

| ข้อมูล | วิธีป้องกัน |
|-------|-----------|
| รูปภาพบน Disk | Encrypt filesystem หรือ File-level encryption |
| JWT Token | HS256 + Expiry 8 ชั่วโมง |
| Database Connection | SSL/TLS |
| WebSocket | WSS (TLS) สำหรับ Production |

### 3. Role-Based Access Control

| Role | สิทธิ์ |
|------|-------|
| Employee | ดูประวัติตัวเองเท่านั้น |
| HR | จัดการพนักงาน, ดู Report, Enrollment |
| Admin | + จัดการ Station, Department, Shift |
| Super Admin | ทุกอย่าง + System Config |

### 4. PDPA Compliance

| มาตรการ | รายละเอียด |
|---------|-----------|
| ลบข้อมูลเมื่อลาออก | ลบ face_templates + Qdrant points + /storage/faces/{id}/ |
| Audit Log | บันทึกทุกการเข้าถึงข้อมูลพนักงาน |
| Data Retention | กำหนดระยะเวลาเก็บ AttendanceLog (เช่น 2 ปี) |
| Consent | พนักงานต้องเซ็นยินยอมก่อน Enrollment |

---

## Suspicious Activity Logging

เมื่อพบเหตุการณ์ผิดปกติ ระบบบันทึก Log พิเศษ:

```
unknown_logs
├── id          BIGINT
├── station_id  UUID
├── timestamp   TIMESTAMPTZ
├── reason      VARCHAR  "LIVENESS_FAIL / SPOOF_DETECTED / UNKNOWN_FACE"
└── snapshot_path VARCHAR  (บันทึกภาพไว้สำหรับตรวจสอบ)
```

### Alert Threshold

ถ้า Station เดียวมี Liveness Fail > 3 ครั้งใน 5 นาที → แจ้งเตือน Admin

---

## Security Checklist (ก่อน Production)

- [ ] เปิด HTTPS/WSS ทุก endpoint
- [ ] ตั้ง JWT Expiry ที่เหมาะสม
- [ ] Encrypt /storage/faces/
- [ ] จำกัด Rate ของ WebSocket connection ต่อ Station
- [ ] ตั้ง Qdrant ให้ไม่ expose port ออก Internet
- [ ] PostgreSQL: ปิด public access, ใช้เฉพาะ internal network
- [ ] บันทึก Audit Log ทุก Admin action
- [ ] กำหนดนโยบาย Data Retention
