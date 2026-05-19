# Chapter 12: Development Philosophy & Project Management

## ปรัชญาหลัก (Core Philosophy)

โครงการ OmniSight มีลักษณะเฉพาะ 3 อย่างที่กำหนดทิศทางของทุกการตัดสินใจ:

```
Real-time AI  +  Hardware Constraint  +  Mission-critical Attendance
```

---

## 3 หลักปรัชญา

---

### หลักที่ 1: "Complexity Belongs to Engineers, Not Users"

> ความซับซ้อนทั้งหมดต้องซ่อนอยู่ข้างหลัง
> พนักงานเดินผ่านแล้วชื่อเด้ง — นั่นคือคำนิยามของความสำเร็จ

วิศวกรแบกภาระทางเทคนิคทั้งหมด ไม่ว่าจะเป็น Batch Inference, Vector Search,
Collision Avoidance หรือ WebSocket Management ผู้ใช้งานจริงไม่ควรรู้สึกว่า
มีอะไรซับซ้อนเกิดขึ้น

**นำไปใช้อย่างไร:**
- ถ้า Feature ใดทำให้ผู้ใช้ต้องคิดมากขึ้น → ออกแบบใหม่
- Error message ต้องบอก "ทำอะไรต่อ" ไม่ใช่บอก "อะไรผิดพลาด"
- Loading state ต้องมีเสมอ ไม่มีการค้างโดยไม่มี Feedback

---

### หลักที่ 2: "Constraints Drive Creativity"

> CPU-Only ไม่ใช่ข้อจำกัด แต่คือโจทย์ที่บังคับให้ออกแบบอย่างฉลาด

ระบบที่ทำงานได้ดีบน Hardware จำกัด มักแข็งแกร่งและประหยัดกว่าระบบที่
พึ่งพา Hardware แพงเสมอ การออกแบบ Strict Filter, Batch Inference และ
Search Space Partitioning ล้วนเกิดจากข้อจำกัดด้าน Hardware

**นำไปใช้อย่างไร:**
- ก่อนเพิ่ม Hardware → หาวิธี Optimize Algorithm ก่อนเสมอ
- ทุก Feature ต้องผ่าน Performance Budget: latency รวม < 300ms
- ถ้า Feature ใดทำให้ latency เกิน → ตัดทิ้งหรือ Optimize ก่อน Merge

---

### หลักที่ 3: "Build to Validate, Not to Complete"

> สร้างให้ใช้งานได้จริงเร็วที่สุด แล้วค่อยปรับ
> อย่าสร้างให้ครบแล้วค่อยทดสอบ

ระบบ AI มี Unknown มากกว่าระบบ Business Logic ทั่วไป
ความแม่นยำของ Model, Threshold ที่เหมาะสม, การตอบสนองของ User
ล้วนต้องพิสูจน์ด้วยการทดสอบจริง ไม่ใช่การคาดเดา

**นำไปใช้อย่างไร:**
- Phase 1 ต้องใช้งานได้จริงก่อน Phase 2 เริ่ม
- Demo ด้วยของจริงเท่านั้น ไม่ใช่ Mock data
- ถ้า Phase 1 ยังไม่ผ่าน Performance Budget → ไม่ขยับไป Phase 2

---

## วิธีบริหารโครงการ

### สำหรับทีม 1-2 คน: Kanban

```
┌──────────┬────────────┬──────────┬──────────┐
│  To Do   │In Progress │  Review  │   Done   │
│          │            │          │          │
│ Task A   │ Task B     │ Task C   │ Task D   │
│ Task E   │            │          │ Task F   │
└──────────┴────────────┴──────────┴──────────┘

กฎ: In Progress มีได้สูงสุด 2 งานพร้อมกัน
    เสร็จชิ้นเดิมก่อน แล้วค่อยหยิบชิ้นใหม่
```

### สำหรับทีม 3+ คน: Lightweight Scrum

```
Sprint: 2 สัปดาห์
├── Sprint Planning (1 ชั่วโมง)  → เลือกงานที่จะทำ
├── Daily Standup (15 นาที)      → มีอะไรติดขัด?
├── Sprint Review (30 นาที)      → Demo ของจริง
└── Retrospective (20 นาที)      → ปรับกระบวนการ
```

---

## Definition of Done (DoD)

งานชิ้นหนึ่งถือว่า "เสร็จ" เมื่อผ่านทุกข้อต่อไปนี้:

| เกณฑ์ | รายละเอียด |
|-------|-----------|
| ✅ ทำงานได้ | Feature ทำงานตาม Use Case ที่กำหนด |
| ✅ Performance ผ่าน | latency อยู่ในเกณฑ์ที่กำหนดใน Ch.3 |
| ✅ Edge Case ผ่าน | ทดสอบกรณีผิดปกติแล้ว |
| ✅ API Contract ตรง | ตรงกับ Ch.7 ทุก field |
| ✅ เอกสารอัปเดต | Chapter ที่เกี่ยวข้องอัปเดตแล้ว |

---

## บทบาทของเอกสาร 12 Chapters

เอกสารชุดนี้ทำหน้าที่เป็น **เข็มทิศ (Compass)** ไม่ใช่ **สัญญา (Contract)**

```
❌ สัญญา = เปลี่ยนไม่ได้ ต้องทำตามทุกอักษร
✅ เข็มทิศ = ชี้ทิศทาง ปรับได้เมื่อ Reality เปลี่ยน
```

### กฎการใช้เอกสาร

**กฎที่ 1: API Contract (Ch.7) นำหน้าโค้ดเสมอ**
```
ตกลง API Contract → เขียน Frontend + Backend พร้อมกันได้เลย
ห้ามเขียนโค้ดก่อนที่ API Contract จะชัดเจน
```

**กฎที่ 2: Reality ไม่ตรงเอกสาร → แก้เอกสารก่อนแก้โค้ด**
```
พบว่า Schema ต้องเปลี่ยน
→ แก้ Ch.6 ก่อน
→ แล้วค่อยแก้ Migration + โค้ด
ไม่ใช่แก้โค้ดแล้วลืมอัปเดตเอกสาร
```

**กฎที่ 3: Edge Case ที่ไม่อยู่ในเอกสาร → คุย → ตัดสินใจ → บันทึก**
```
เจอ Edge Case ระหว่างพัฒนา
→ อย่าเดาเอง
→ คุยกัน → ตัดสินใจ → อัปเดต Chapter ที่เกี่ยวข้อง
```

### ตารางความรับผิดชอบของเอกสาร

| Chapter | บทบาท | อัปเดตเมื่อ |
|---------|-------|-----------|
| Ch.0 Technology Stack | Source of Truth ของ Tech | เปลี่ยน Library หลัก |
| Ch.1 Vision | ไม่ค่อยเปลี่ยน | Scope เปลี่ยนใหญ่ |
| Ch.2 Use Cases | Reference ของ Feature | เพิ่ม/ลด Use Case |
| Ch.3 Architecture | Blueprint ของระบบ | เปลี่ยน Structure |
| Ch.4 AI & Hardware | Optimization Guide | เปลี่ยน Model หรือ Provider |
| Ch.5 Vector DB | Search Strategy | เปลี่ยน Indexing/Filtering |
| Ch.6 Data Schema | **อัปเดตทุกครั้งที่ DB เปลี่ยน** | ทุก Migration |
| Ch.7 API Contract | **อัปเดตก่อนเขียนโค้ดเสมอ** | ทุก Endpoint เปลี่ยน |
| Ch.8 UI/UX | Design Reference | UX เปลี่ยน |
| Ch.9 Shift & Scope | Business Logic | Business Rule เปลี่ยน |
| Ch.10 Security | Security Checklist | ก่อน Production |
| Ch.11 Roadmap | แผนงาน | ทุก Phase เสร็จ |
| Ch.12 Philosophy | ไม่เปลี่ยน | — |

---

## Performance Budget (กฎเหล็ก)

ทุก Feature ต้องไม่ทำให้ตัวเลขเหล่านี้เกิน:

| Metric | Budget | วิธีวัด |
|--------|--------|--------|
| End-to-end latency | < 300ms | Scan จนถึง Overlay |
| Qdrant Search | < 15ms | Filtered Search |
| ONNX Inference | < 250ms | 10 faces batch |
| UI Frame Rate | > 30 FPS | Video + Overlay |
| RAM Usage | < 8 GB | ใช้งาน 24 ชั่วโมง |

ถ้า Feature ใดทำให้ Budget เกิน → **Optimize ก่อน Merge เสมอ**

---

## สรุปในหนึ่งประโยค

> ใช้เอกสาร 12 Chapters เป็นเข็มทิศ,
> ใช้ Kanban หรือ Lightweight Scrum เป็นเครื่องยนต์,
> ยึดหลัก "ใช้งานได้จริงก่อนเสมอ"
> และไม่มีอะไรเสร็จจนกว่า Performance Budget จะผ่าน
