# Chapter 3: System Architecture

## หลักการออกแบบ (Design Principles)

1. **Separation of Concerns** — แต่ละ Layer ทำหน้าที่ตัวเองให้ดีที่สุด ไม่ก้าวก่ายกัน
2. **Decoupled Pipeline** — UI ไม่รอ AI, AI ไม่รอ UI
3. **Strict Scope** — พนักงานสแกนได้เฉพาะกล้องของแผนกตัวเองเท่านั้น
4. **Fail Gracefully** — ถ้า Inference ช้า UI ยังต้องแสดงผลได้

---

## 4-Layer Architecture

```
┌─────────────────────────────────────────────┐
│  Layer 1: Presentation                      │
│  Vite + Vue 3 + DaisyUI + Canvas API        │
│  หน้าที่: แสดงวิดีโอ, วาด Overlay, Admin UI │
└──────────────────┬──────────────────────────┘
                   │ WebSocket (Binary/JSON)
┌──────────────────▼──────────────────────────┐
│  Layer 2: Orchestration                     │
│  FastAPI (Python 3.12)                      │
│  หน้าที่: รับ Request, จัดคิว, WebSocket,   │
│           ดึง Active Filter จาก Redis       │
└──────────────────┬──────────────────────────┘
                   │ Internal Call
┌──────────────────▼──────────────────────────┐
│  Layer 3: Intelligence (Inference)          │
│  ONNX Runtime + InsightFace buffalo_l       │
│  หน้าที่: แปลงภาพเป็น Embedding (512d)     │
│           Batch processing สูงสุด 10 หน้า  │
└──────────────────┬──────────────────────────┘
                   │ gRPC / Connection Pool
┌──────────────────▼──────────────────────────┐
│  Layer 4: Persistence                       │
│  Qdrant (Vector) + PostgreSQL (Relational)  │
│  + Redis (Active Filter Cache)              │
│  หน้าที่: ค้นหาใบหน้า, เก็บ Log, Cache     │
└─────────────────────────────────────────────┘
```

---

## Multi-Camera Architecture (Station Model)

กล้องแต่ละตัวในระบบคือ **Station** ที่มี Identity ของตัวเอง

```
Station A                Station B              Station C
"ประตูหน้า อาคาร A"     "ประตูหลัง อาคาร B"   "ห้องประชุม VIP"
dept: [สืบสวน, ป้องกัน]  dept: [ธุรการ]         dept: [ผู้บริหาร]
        │                       │                      │
        └───────────────────────┴──────────────────────┘
                                │
                        FastAPI (Orchestrator)
                                │
                     Redis: Active Filter State
                                │
                    Qdrant: Filtered Vector Search
```

### กฎของ Station (Strict Mode)
- พนักงานสแกนได้เฉพาะ Station ที่แผนกตัวเองอยู่ใน scope
- Station 1 กล้อง รับผิดชอบได้ N แผนก (Admin กำหนด)
- พนักงาน 1 คน อยู่ได้ 1 แผนกเท่านั้น

---

## Data Flow: การสแกนหน้า (Scan Flow)

```
กล้อง
  │
  ├─[ทุก Frame]──→ Frontend แสดง Video Stream
  │
  └─[ทุก 500ms หรือเมื่อ Trigger]──→ WebSocket Binary
                                          │
                                    FastAPI รับ Frame
                                          │
                                    ดึง Active Filter
                                    จาก Redis
                                    (dept_ids ของ Station นี้)
                                          │
                                    ONNX Inference
                                    (Batch: สูงสุด 10 หน้า)
                                    → 10 Embeddings (512d)
                                          │
                                    Qdrant Batch Search
                                    WHERE dept_id IN [...]
                                    → Match Results
                                          │
                                    Fetch Employee Metadata
                                    จาก PostgreSQL
                                          │
                                    บันทึก AttendanceLog
                                          │
                                    WebSocket Push → Frontend
                                          │
                                    Frontend วาด Overlay
```

---

## Communication Standards

| เส้นทาง | Protocol | Format | เหตุผล |
|--------|---------|--------|--------|
| Frontend → Backend (scan frame) | WebSocket | Binary (Uint8Array) | ลด CPU overhead 15-20% เทียบ Base64 |
| Backend → Frontend (result) | WebSocket | JSON | ข้อมูลเล็ก, readable |
| Frontend → Backend (API) | HTTP REST | JSON | CRUD, Admin operations |
| Backend → Qdrant | gRPC Persistent | Protobuf | เร็ว, ลด handshake |
| Backend → PostgreSQL | TCP Pool | SQL | SQLAlchemy managed |
| Backend → Redis | TCP | Binary | Active filter state |

---

## Latency Budget (เป้าหมาย)

| ขั้นตอน | เวลาที่ยอมรับได้ |
|--------|----------------|
| Network (WebSocket) | < 10ms |
| ONNX Inference (10 faces) | < 200ms |
| Qdrant Filtered Search | < 10ms |
| PostgreSQL Metadata Fetch | < 5ms |
| Redis Filter Lookup | < 1ms |
| Frontend Overlay Render | < 16ms (60 FPS) |
| **รวม End-to-End** | **< 300ms** |

---

## Scalability Path

| ระดับ | พนักงาน | การปรับ |
|------|---------|--------|
| Current | 10,000 | รันทุกอย่างบนเครื่องเดียว |
| Phase 2 | 50,000 | แยก Inference Layer ออกเป็นอีก Process |
| Phase 3 | 100,000+ | แยก Layer 3 & 4 ไปรันบน Server อีกเครื่อง |

การออกแบบ 4-Layer ทำให้แต่ละ Layer ย้ายได้อิสระโดยไม่กระทบ Layer อื่น
