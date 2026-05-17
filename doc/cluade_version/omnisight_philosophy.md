# OmniSight — Philosophy & Engineering Principles
### "องค์ความรู้และปรัชญาของการพัฒนา"

> บันทึก ณ 2026-05-17 | สำหรับทีมพัฒนาและ AI sessions ถัดไป

---

## I. Core Philosophy — "ทำไม ก่อน ทำอะไร"

> **ระบบที่ดีไม่ใช่แค่ระบบที่ทำงานได้ — แต่คือระบบที่ล้มแล้วลุกได้เอง  
> เปลี่ยนได้โดยไม่ต้องหยุดทำงาน และ user ไม่รู้สึกว่ากำลังใช้เทคโนโลยี**

---

## II. สถาปัตยกรรม — หลักการ 5 ข้อ

**1. SSOT (Single Source of Truth)**  
PostgreSQL คือ truth เสมอ Redis คือ cache ที่ถูก derive มา ไม่ใช่ owner  
ถ้า Redis ล่ม ระบบยังทำงานได้ (ช้าลง) — ไม่ใช่หยุด  
Config ที่ปรับได้อยู่ใน `system_settings` table ไม่ใช่ `.env`

**2. Event-Driven over Polling**  
ทุก state change ส่งออกเป็น event ผ่าน Redis Pub/Sub  
Frontend ไม่เคย poll — รอรับ push เท่านั้น  
ผลลัพธ์: latency ต่ำ, server load ต่ำ, UI real-time จริง

**3. Layered Resilience (Defense in Depth)**  
Redis SETNX → PostgreSQL unique constraint → application rollback  
ไม่มีชั้นเดียวที่เป็น single point of failure  
Graceful degradation: ทุก dependency มี fallback path

**4. Separation of Concerns — ชัดเจนทุกชั้น**  
`websocket.py` = orchestration เท่านั้น ไม่มี business logic  
`attendance_service.py` = business rules + cooldown  
`redis.py` = cache ops เท่านั้น ไม่รู้จัก business  
`face_engine.py` = AI inference เท่านั้น ไม่รู้จัก DB

**5. Optimistic UI + Eventual Consistency**  
UI เปลี่ยน state ทันทีที่ user กระทำ — ไม่รอ server  
ถ้า server fail → revert พร้อม toast แจ้งเตือน  
ผลลัพธ์: UX รู้สึกเร็ว ไม่มี lag แม้ network ช้า

---

## III. แนวคิด Multi-Camera — "1 กล้อง 1 ชีวิต"

กล้องแต่ละตัวคือ independent entity — มี lifecycle ของตัวเอง  
1 WebSocket connection ต่อ 1 กล้อง → fault isolation ตามธรรมชาติ  
กล้องตัวหนึ่งล้มไม่ลาม Camera Manager เป็น single registry (Redis-backed)  
Hot plug = device event → state update → UI reflects — ไม่มีมือ user ต้องเข้าไปแตะ

---

## IV. UX Philosophy — "Zero Cognitive Load"

> **User ต้องการ outcome ไม่ใช่ process**

ออกแบบตาม Persona ไม่ใช่ Feature:
- **ADMIN** → Control Tower: เห็นทุกอย่าง ควบคุมได้ทุกอย่างจากจุดเดียว
- **OPERATOR** → Passive Display: เสียง + สี บอกทุกอย่าง ไม่ต้องคลิก
- **Teacher** → Thumb-zone, haptic, outdoor contrast — ออกแบบสำหรับสนามจริง
- **HR** → Data-first, export 1 คลิก, ไม่รอ IT

Feedback ทุก action ภายใน 100ms — ใช้ skeleton loader ถ้าต้องรอ  
Progressive Disclosure: แสดงเฉพาะสิ่งที่ต้องการ ณ ตอนนั้น  
Error Prevention ดีกว่า Error Message

---

## V. Conflict Management — "Plan for Failure"

> **ทุก conflict ที่คิดไม่ถึงตอนออกแบบ จะปรากฏตอน production**

แนวทาง: ระบุ conflict scenarios ล่วงหน้าทุกระดับ (Device/Network/Data/Logic)  
แก้ที่ต้นเหตุก่อน ไม่ใช่ปลายเหตุ  
Atomic operations (Redis SETNX) ป้องกัน race condition ระดับ data  
Exponential backoff + jitter ป้องกัน thundering herd  
Last-writer-wins สำหรับ reconnection — ไม่ปฏิเสธ camera ที่กลับมา

---

## VI. Live System — "ระบบที่หายใจได้"

Config เปลี่ยนได้ขณะระบบทำงาน — ไม่มี downtime  
Model threshold ปรับ realtime → propagate ทุก instance ทันที  
Camera pause/resume จาก Pilot Console — smartphone รับคำสั่งทันที  
Health endpoint `/health/deep` บอกสุขภาพทุก layer รวมถึง conflict indicators

---

## VII. Technology Choices — "Right Tool, Right Reason"

| เครื่องมือ | เหตุผลที่เลือก |
|-----------|--------------|
| InsightFace buffalo_l | all-in-one: detect + landmark + 512d ArcFace embedding |
| Qdrant HNSW + SQ8 | approximate search O(log N), 75% RAM saving, payload filter |
| Redis | ephemeral state + pub/sub + cooldown — ไม่ใช่ SSOT |
| FastAPI async | WebSocket + async DB + ONNX thread pool ใน event loop เดียว |
| WebSocket binary JPEG | 33% less bandwidth vs Base64, latency ต่ำกว่า |
| Pinia + 1 Console WS | single state source per session, event-routed |

---

## VIII. Engineering Values

```
Reliability   > Raw Performance      — ทำงานได้สม่ำเสมอดีกว่าเร็วบางครั้ง
Simplicity    > Cleverness           — โค้ดที่อ่านง่าย debug ง่ายกว่าเสมอ
Prevention    > Recovery             — ป้องกัน conflict ดีกว่าแก้ตอนพัง
Observability > Assumption           — log และ metric บอกความจริง ไม่ใช่สมมติฐาน
User Outcome  > Technical Elegance   — ระบบเก่งแค่ไหนไม่สำคัญถ้า user งง
```

---

*OmniSight — Face Recognition Attendance Platform*  
*Enterprise HR → School → Meeting Room — Built to scale, designed to last*
