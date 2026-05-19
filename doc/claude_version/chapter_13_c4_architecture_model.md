# Chapter 13: C4 Architecture Model

> C4 Model คือ framework สำหรับอธิบาย Software Architecture ใน 4 ระดับ  
> Context → Container → Component → Code  
> แต่ละระดับตอบคำถามที่ต่างกัน สำหรับผู้อ่านที่ต่างกัน

---

## Level 1 — System Context Diagram

> **คำถาม:** ระบบนี้คืออะไร? ใครใช้? เชื่อมกับอะไรภายนอก?  
> **ผู้อ่าน:** ผู้บริหาร, Business Stakeholder, ทีมอื่น

```
┌─────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL ACTORS                               │
│                                                                      │
│  [ผู้ดูแลระบบ]    [HR Officer]      [หน่วยงานรักษาความปลอดภัย]     │
│   Admin            HR Staff          Security Guard                  │
│     │                │                      │                        │
└─────┼────────────────┼──────────────────────┼────────────────────────┘
      │                │                      │
      │    HTTPS/WSS   │    HTTPS             │    WebSocket (live scan)
      ▼                ▼                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│                    ░░░ OmniSight System ░░░                          │
│                                                                      │
│   Face Recognition Attendance System                                 │
│   - ระบุตัวตนจากใบหน้า                                              │
│   - บันทึกเวลาเข้า-ออกงาน                                          │
│   - จัดการพนักงาน / แผนก / กะ                                      │
│   - รายงาน HR                                                        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
      │                │                      │
      │                │                      │
      ▼                ▼                      ▼
┌──────────┐    ┌─────────────┐    ┌──────────────────┐
│  Camera  │    │  HR System  │    │  Notification    │
│  (IP/USB)│    │  (Future)   │    │  (Email/Line)    │
│          │    │  SAP/Excel  │    │  (Future)        │
└──────────┘    └─────────────┘    └──────────────────┘

EXTERNAL SYSTEMS:
  - Camera: กล้อง IP หรือ USB webcam ส่ง video stream ผ่าน browser
  - HR System: (Future) ระบบ HR ขององค์กรที่ import/export ข้อมูลพนักงาน
  - Notification: (Future) Email/Line Notify เมื่อพนักงานขาดงาน
```

### Actors และ Goals

| Actor | บทบาท | Goal หลัก |
|-------|--------|-----------|
| Admin | ดูแลระบบ | จัดการ Master Data (Employee, Dept, Station, Shift) |
| HR Staff | HR ฝ่ายบุคคล | ดู Report, Export, Manual Override |
| Security Guard | รปภ. | เปิดหน้า Scan, ไม่ต้องทำอะไร — ระบบทำงานเอง |
| Employee | พนักงาน | เดินผ่านกล้อง — ไม่ Interact กับระบบโดยตรง |

---

## Level 2 — Container Diagram

> **คำถาม:** ระบบประกอบด้วย Process/Service/App อะไรบ้าง? คุยกันอย่างไร?  
> **ผู้อ่าน:** Software Architect, Senior Developer, DevOps

```
┌─────────────────────────────────── OmniSight System ─────────────────────────────────────┐
│                                                                                            │
│   ┌──────────────────────┐         ┌──────────────────────────────────────────────────┐   │
│   │    [Browser]         │         │              [Backend Server]                    │   │
│   │                      │  REST   │                                                  │   │
│   │  Vue 3 SPA           │◄───────►│  FastAPI (Python 3.12)                          │   │
│   │  + DaisyUI           │         │  - REST API (8 routers)                        │   │
│   │  + Vite 5            │ WS/WSS  │  - WebSocket endpoint (/ws/scan/{station_id})  │   │
│   │  Port: 5173 (dev)   │◄───────►│  - Lifespan: init Qdrant collection            │   │
│   │  Port: 80 (prod)    │  Binary  │  Port: 8000                                    │   │
│   │                      │  JPEG   │                                                  │   │
│   └──────────────────────┘         └──────────────┬────────┬──────────┬─────────────┘   │
│                                                    │        │          │                  │
│                                              SQL   │  gRPC  │  TCP     │                  │
│                                                    ▼        ▼          ▼                  │
│   ┌─────────────────┐   ┌──────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│   │  [File Storage] │   │  [PostgreSQL 16]  │  │  [Qdrant]      │  │  [Redis 7]       │  │
│   │                 │   │                   │  │                │  │                  │  │
│   │  /storage/faces/│   │  - employees      │  │  - face_       │  │  - station:      │  │
│   │  {uuid}/        │   │  - departments    │  │    registry    │  │    {id}:depts    │  │
│   │  sample_1.jpg   │   │  - stations       │  │  - HNSW + SQ8  │  │  (Active Filter) │  │
│   │  ...            │   │  - face_templates │  │  - 512d cosine │  │                  │  │
│   │  (Local Disk)   │   │  - attendance_logs│  │  Port: 6333    │  │  Port: 6379      │  │
│   │                 │   │  Port: 5432       │  │                │  │                  │  │
│   └─────────────────┘   └──────────────────┘  └────────────────┘  └──────────────────┘  │
│                                                                                            │
└────────────────────────────────────────────────────────────────────────────────────────────┘

COMMUNICATION:
  Browser ↔ FastAPI  : HTTPS/REST (CRUD, Auth)
  Browser ↔ FastAPI  : WSS (WebSocket binary frame + JSON result)
  FastAPI → PostgreSQL: SQLAlchemy async + asyncpg (connection pool)
  FastAPI → Qdrant   : qdrant-client (HTTP/gRPC)
  FastAPI → Redis    : aioredis (async)
  FastAPI → Disk     : os/pathlib (synchronous — TODO: เปลี่ยนเป็น async)
```

### Technology Choices per Container

| Container | Technology | เหตุผล |
|-----------|-----------|--------|
| Frontend SPA | Vue 3 + Vite + DaisyUI | Reactive, fast build, dark theme out-of-box |
| Backend API | FastAPI + Python 3.12 | Async native, auto-docs, type-safe |
| Relational DB | PostgreSQL 16 | ACID, UUID, JSONB, TimestampTZ |
| Vector DB | Qdrant 1.x | HNSW, payload filter, Rust-speed |
| Cache | Redis 7 | Sub-ms latency, pub/sub future use |
| File Storage | Local Disk | Simple, ไม่ต้องการ object storage สำหรับ scale นี้ |

---

## Level 3 — Component Diagram

> **คำถาม:** ภายใน Backend มี Component อะไรบ้าง? มัน collaborate กันอย่างไร?  
> **ผู้อ่าน:** Developer ที่จะ maintain / extend ระบบ

```
┌────────────────────────────────── FastAPI Backend ────────────────────────────────────────┐
│                                                                                            │
│  ┌──────────── API Layer (app/api/) ─────────────────────────────────────────────────┐   │
│  │                                                                                    │   │
│  │  auth.py      departments.py   employees.py    stations.py                        │   │
│  │  ┌──────┐     ┌────────────┐   ┌───────────┐   ┌──────────┐                      │   │
│  │  │ JWT  │     │CRUD        │   │CRUD +     │   │CRUD +    │                      │   │
│  │  │login │     │dept/shift  │   │enrich()   │   │dept sync │                      │   │
│  │  └──────┘     └────────────┘   └───────────┘   └──────────┘                      │   │
│  │                                                                                    │   │
│  │  enrollment.py          attendance.py          websocket.py                       │   │
│  │  ┌─────────────────┐    ┌──────────────┐       ┌──────────────────────────────┐   │   │
│  │  │POST /{id}/enroll│    │GET /attendance│       │WS /ws/scan/{station_id}      │   │   │
│  │  │ → extract embed │    │ filter by    │       │  receive_bytes()              │   │   │
│  │  │ → quality check │    │ date/dept    │       │  → face_engine.get_detections│   │   │
│  │  │ → upsert Qdrant │    │              │       │  → Redis.get_station_filter  │   │   │
│  │  │ → save template │    └──────────────┘       │  → Qdrant.search()           │   │   │
│  │  └─────────────────┘                           │  → [TODO] save AttendanceLog │   │   │
│  │                                                │  → send_text(ScanResult)     │   │   │
│  └────────────────────────────────────────────────┴──────────────────────────────┴───┘   │
│                │                                             │                            │
│                ▼                                             ▼                            │
│  ┌──────────── Core Layer (app/core/) ──────────────────────────────────────────────┐   │
│  │                                                                                    │   │
│  │  face_engine.py                         config.py                                 │   │
│  │  ┌──────────────────────────────────┐   ┌──────────────────────────────────────┐  │   │
│  │  │  FaceEngine (Singleton)          │   │  Settings (Pydantic BaseSettings)    │  │   │
│  │  │  ├── _app: FaceAnalysis (lazy)   │   │  - DATABASE_URL                      │  │   │
│  │  │  ├── _load() → buffalo_l         │   │  - QDRANT_HOST/PORT/COLLECTION       │  │   │
│  │  │  ├── get_embeddings(img)         │   │  - REDIS_URL                         │  │   │
│  │  │  ├── get_quality_score(img)      │   │  - SECRET_KEY, ALGORITHM             │  │   │
│  │  │  └── get_detections(img)         │   │  - MATCH_THRESHOLD                   │  │   │
│  │  │                                  │   │  - MIN_TEMPLATES_TO_ACTIVATE         │  │   │
│  │  │  [TODO] liveness.py              │   └──────────────────────────────────────┘  │   │
│  │  │  MiniFASNet anti-spoofing        │                                              │   │
│  │  └──────────────────────────────────┘                                              │   │
│  │                                                                                    │   │
│  └────────────────────────────────────────────────────────────────────────────────────┘   │
│                │                                                                           │
│                ▼                                                                           │
│  ┌──────────── DB Layer (app/db/) ───────────────────────────────────────────────────┐   │
│  │                                                                                    │   │
│  │  postgres.py              qdrant.py                  redis.py                     │   │
│  │  ┌─────────────────┐     ┌──────────────────────┐   ┌────────────────────────┐   │   │
│  │  │ async_engine    │     │ AsyncQdrantClient     │   │ get_station_filter()   │   │   │
│  │  │ AsyncSession    │     │ QdrantClient (sync)   │   │ set_station_filter()   │   │   │
│  │  │ get_db() dep    │     │ init_collection()     │   │ aioredis pool          │   │   │
│  │  │ Base.metadata   │     │ get_qdrant() dep      │   └────────────────────────┘   │   │
│  │  └─────────────────┘     └──────────────────────┘                                 │   │
│  │                                                                                    │   │
│  └────────────────────────────────────────────────────────────────────────────────────┘   │
│                │                                                                           │
│                ▼                                                                           │
│  ┌──────────── Model Layer (app/models/) ────────────────────────────────────────────┐   │
│  │  orm.py (SQLAlchemy)          schemas.py (Pydantic)                               │   │
│  │  Employee, Department,        EmployeeOut, EnrollmentStatus,                      │   │
│  │  Station, FaceTemplate,       ScanResult, FaceResult, BBox                       │   │
│  │  AttendanceLog, Shift         StationCreate, DeptCreate...                        │   │
│  └────────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                            │
└────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities (Single Responsibility Check)

| Component | รับผิดชอบ | ❌ ไม่รับผิดชอบ |
|-----------|----------|--------------|
| `face_engine.py` | Inference เท่านั้น | ไม่รู้จัก DB, ไม่รู้จัก HTTP |
| `websocket.py` | Orchestrate scan flow | ไม่ทำ Inference โดยตรง |
| `enrollment.py` | Enrollment workflow | ไม่ทำ Inference โดยตรง |
| `qdrant.py` | Qdrant connection + init | ไม่มี business logic |
| `redis.py` | Station filter cache | ไม่มี business logic |
| `config.py` | Settings จาก .env | ไม่มี logic อื่น |

---

## Level 4 — Code (Key Algorithms)

> **คำถาม:** ส่วนที่ซับซ้อนที่สุดทำงานอย่างไร?

### Algorithm: Scan Pipeline (websocket.py)

```python
# Pseudocode — critical path
async def scan_ws(websocket, station_id, token):
    # 1. Auth check (O(1))
    verify_jwt(token)
    await websocket.accept()

    while True:
        # 2. Receive binary frame (network I/O)
        raw = await websocket.receive_bytes()          # async

        # 3. Decode JPEG → numpy array (CPU)
        frame = cv2.imdecode(raw, IMREAD_COLOR)        # sync ~1ms

        # 4. Face Detection + Embedding (CPU/GPU)
        detections = face_engine.get_detections(frame) # sync ~150-300ms (CPU)
        # Returns: [(tracking_id, embedding[512], bbox[4]), ...]

        if not detections:
            await websocket.send_text(empty_result)
            continue

        # 5. Get dept filter from Redis (async, <1ms)
        dept_ids = await get_station_filter(station_id)

        # 6. Vector search per face (async, ~5-10ms per face)
        for tracking_id, embedding, bbox in detections:
            results = qdrant.search(
                collection_name="face_registry",
                query_vector=embedding.tolist(),        # 512 floats
                query_filter=Filter(dept_id IN dept_ids),
                limit=1,
                score_threshold=0.72,                   # cosine similarity
            )
            # results[0].score = confidence (0.0 - 1.0)
            # results[0].payload["employee_id"] = UUID

        # 7. [TODO] Log attendance if match (async PostgreSQL)
        # 8. Send result JSON to browser
        await websocket.send_text(ScanResult(...).json())
```

### Algorithm: Qdrant Filtered Search

```
Query: embedding[512d] + filter{dept_id IN [1,2,3]}

Step 1: Pre-filter by payload (dept_id)
  → Qdrant uses payload index (inverted index on dept_id)
  → Reduces search space from 60,000 to N dept vectors

Step 2: HNSW approximate search
  → Navigate graph from entry point
  → ef_search=64 candidate evaluation
  → Return top-1 by cosine similarity

Step 3: Score threshold check
  → If score < 0.72 → discard (unknown)
  → If score >= 0.72 → match

Complexity: O(log N) for HNSW — not O(N)
```
