# Chapter 14: Sequence Diagrams — Critical Flows

> Sequence Diagrams แสดง "ใครทำอะไร เมื่อไหร่ ลำดับเป็นอย่างไร"  
> สำคัญมากสำหรับการ debug, onboarding developer ใหม่, และ contract verification

---

## Flow 1: Employee Enrollment

**Actor:** Admin  
**Trigger:** Admin ต้องการลงทะเบียนใบหน้าพนักงานใหม่  
**Precondition:** พนักงานมีอยู่ในระบบแล้ว (สร้างด้วย POST /employees)

```
Admin          Browser         FastAPI         FaceEngine      PostgreSQL      Qdrant        Disk
  │               │               │                │               │             │             │
  │─ Open Enroll ─►               │                │               │             │             │
  │  page(emp_id) │               │                │               │             │             │
  │               │─GET enrollment►               │               │             │             │
  │               │    status     │                │               │             │             │
  │               │               │─ SELECT        │               │             │             │
  │               │               │  FaceTemplates ►               │             │             │
  │               │               │                │               │◄────────────┤             │
  │               │               │                │               │  6 slot rows│             │
  │               │◄── 200 slots ─┤                │               │             │             │
  │               │   [X][ ][ ]   │                │               │             │             │
  │               │   [ ][ ][ ]   │                │               │             │             │
  │               │               │                │               │             │             │
  │─ Capture photo►               │                │               │             │             │
  │  (webcam)     │               │                │               │             │             │
  │               │─POST /enroll  │                │               │             │             │
  │               │  sample_index=1               │               │             │             │
  │               │  file=<jpeg>  │                │               │             │             │
  │               │               │─ Save to disk ──────────────────────────────────────────► │
  │               │               │                │               │             │  write jpg  │
  │               │               │─ imread() ─────►               │             │             │
  │               │               │                │─ get_        │             │             │
  │               │               │                │  embeddings()│             │             │
  │               │               │                │  (ONNX inf.) │             │             │
  │               │               │                │◄─ [512d vec] ┤             │             │
  │               │               │◄─ embedding+   │               │             │             │
  │               │               │   quality_score│               │             │             │
  │               │               │                │               │             │             │
  │               │               │  quality < 0.75?               │             │             │
  │               │               │  ├─ YES → 422 "QUALITY_FAILED"─►             │             │
  │               │               │  └─ NO → continue              │             │             │
  │               │               │                │               │             │             │
  │               │               │─────────────────────────────────────────────► upsert()    │
  │               │               │                │               │             │ point_id=uuid│
  │               │               │                │               │             │ vector=[512] │
  │               │               │                │               │             │ payload={    │
  │               │               │                │               │             │  emp_id, dept}│
  │               │               │                │               │◄────────────┤             │
  │               │               │                │               │  OK         │             │
  │               │               │─ INSERT face_template          │             │             │
  │               │               │  (qdrant_id, sample_index) ───►             │             │
  │               │               │                │               │             │             │
  │               │               │  count(templates) >= 6?        │             │             │
  │               │               │  └─ YES → UPDATE employees     │             │             │
  │               │               │           SET is_active=TRUE   │             │             │
  │               │               │                │               │             │             │
  │               │               │─ COMMIT ───────────────────────►             │             │
  │               │◄── 201 {sample_index, quality_score}           │             │             │
  │               │               │                │               │             │             │
  │ (repeat for   │               │                │               │             │             │
  │  slots 2-6)   │               │                │               │             │             │
```

**ข้อสังเกตสำคัญ:**
- Qdrant upsert และ PostgreSQL INSERT ไม่ได้อยู่ใน transaction เดียวกัน → ถ้า PG fail หลัง Qdrant upsert → orphaned vector (BUG-002)
- ต้องเพิ่ม Saga pattern หรือ compensating transaction ใน production

---

## Flow 2: Real-time Face Scan & Attendance Logging

**Actor:** Security Guard (passive), Employee (เดินผ่าน)  
**Trigger:** Guard เปิดหน้า Scan → WebSocket เชื่อมต่อ  
**Rate:** ส่ง frame ทุก 200ms

```
Browser(Guard)  FastAPI(WS)   Redis      FaceEngine   Qdrant    PostgreSQL
     │               │          │             │           │           │
     │─ WS Connect ──►           │             │           │           │
     │  ?token=JWT   │           │             │           │           │
     │               │─ verify ──►             │           │           │
     │               │  JWT      │             │           │           │
     │               │           │             │           │           │
     │               │◄──────────┤             │           │           │
     │               │  OK       │             │           │           │
     │◄── WS Accept ─┤           │             │           │           │
     │               │           │             │           │           │
     │               │           │             │           │           │
     │  [every 200ms]│           │             │           │           │
     │── Binary ─────►           │             │           │           │
     │   JPEG frame  │           │             │           │           │
     │               │─ imdecode─►             │           │           │
     │               │  numpy    │             │           │           │
     │               │           │             │           │           │
     │               │─ get_depts►             │           │           │
     │               │  (station_id)           │           │           │
     │               │◄──[1,2,3]─┤             │           │           │
     │               │           │             │           │           │
     │               │─────────────────────────► get_      │           │
     │               │           │             │ detections│           │
     │               │           │             │ (ONNX)    │           │
     │               │           │             │           │           │
     │               │◄─────────────────────────[faces]    │           │
     │               │           │             │           │           │
     │               │  for each face:         │           │           │
     │               │────────────────────────────────────►search()   │
     │               │           │             │           │ cosine    │
     │               │           │             │           │ filter    │
     │               │           │             │           │ dept_ids  │
     │               │◄────────────────────────────────────[results]  │
     │               │           │             │           │           │
     │               │  if score >= 0.72:      │           │           │
     │               │────────────────────────────────────────────────►
     │               │           │             │           │  [TODO]   │
     │               │           │             │           │  INSERT   │
     │               │           │             │           │  attendance│
     │               │           │             │           │  _logs    │
     │               │           │             │           │  (cooldown│
     │               │           │             │           │   5 min)  │
     │               │◄───────────────────────────────────────────────┤
     │               │           │             │           │  OK       │
     │               │           │             │           │           │
     │◄── JSON ──────┤           │             │           │           │
     │   ScanResult  │           │             │           │           │
     │   {faces:[{   │           │             │           │           │
     │    status,    │           │             │           │           │
     │    emp_id,    │           │             │           │           │
     │    confidence,│           │             │           │           │
     │    bbox}]}    │           │             │           │           │
     │               │           │             │           │           │
     │  Draw overlay │           │             │           │           │
     │  on canvas    │           │             │           │           │
```

**Timing per frame (CPU mode):**

```
Network receive        : ~5ms
JPEG decode            : ~1ms
Face detection (ONNX)  : ~150-250ms   ← bottleneck
Redis lookup           : ~1ms
Qdrant search (1 face) : ~5-10ms
PostgreSQL INSERT      : ~5ms
JSON encode + send     : ~1ms
─────────────────────────────
Total (1 face)         : ~170-270ms  ✅ < 300ms SLA
Total (10 faces batch) : ~300-400ms  ✅ < 500ms SLA
```

---

## Flow 3: Admin Configure Station Scope

**Actor:** Admin  
**Trigger:** Admin ต้องการเปลี่ยน scope ของกล้อง (เพิ่ม/ลบแผนก)  
**Impact:** กล้องนั้นจะ scan พนักงานของแผนกใหม่ทันที

```
Admin    Browser    FastAPI    PostgreSQL    Redis
  │          │          │           │          │
  │─ Open ───►           │           │          │
  │  Station  │           │           │          │
  │  config   │           │           │          │
  │           │─GET station►          │          │
  │           │           │─SELECT ───►          │
  │           │           │  station_ │          │
  │           │           │  depts    │          │
  │           │           │◄──────────┤          │
  │           │◄── station │           │          │
  │           │   {dept_ids│           │          │
  │           │   :[1,2]}  │           │          │
  │           │           │           │          │
  │─ Check/   │           │           │          │
  │  Uncheck  │           │           │          │
  │  dept 3   │           │           │          │
  │           │─PUT /stations/{id}/depts          │
  │           │  {dept_ids:[1,2,3]}               │
  │           │           │           │          │
  │           │           │─ DELETE station_depts─►         │
  │           │           │  WHERE station_id=X  │          │
  │           │           │─ INSERT dept_ids [1,2,3]        │
  │           │           │                      │          │
  │           │           │─ COMMIT ──────────────►          │
  │           │           │                      │          │
  │           │           │─ SET station:{id}:depts=[1,2,3]─►
  │           │           │  (update Redis cache)           │
  │           │           │                                 │
  │           │◄── 200 OK ┤                                 │
  │           │           │                                 │
  │  [WS frames ต่อจากนี้ จะใช้ dept_ids=[1,2,3] ทันที]   │
```

**Critical Point:** Redis อัปเดต ATOMIC หลัง PG commit — ถ้า Redis fail → WebSocket ยังใช้ค่าเก่า  
→ Mitigation: fallback query PG ถ้า Redis miss

---

## Flow 4: Login & Token Lifecycle

**Actor:** Admin / HR Staff  
**Security Note:** Hardcoded admin/admin → ต้องเปลี่ยนใน production

```
User     Browser      FastAPI      JWT Library
  │          │             │            │
  │─ Enter ──►             │            │
  │  credentials│           │            │
  │           │─POST /auth/login         │
  │           │  {username, password}    │
  │           │             │─ verify ───►
  │           │             │  credentials│
  │           │             │  (hardcoded)│
  │           │             │◄── valid ───┤
  │           │             │            │
  │           │             │─ create ───►
  │           │             │  JWT token │
  │           │             │  {sub:admin│
  │           │             │   exp:+8h} │
  │           │             │◄── token ──┤
  │           │◄── 200 {access_token} ───┤
  │           │             │            │
  │           │─ store in   │            │
  │           │  localStorage           │
  │           │             │            │
  │  [subsequent requests]  │            │
  │           │─ GET /api/v1/...         │
  │           │  Authorization: Bearer {token}
  │           │             │─ verify ───►
  │           │             │  signature  │
  │           │             │  + expiry   │
  │           │             │◄── valid ───┤
  │           │             │            │
  │  [token expires after 8h]           │
  │           │─ GET /api/v1/...         │
  │           │             │─ verify ───►
  │           │             │◄── EXPIRED ┤
  │           │◄── 401 Unauthorized      │
  │           │─ redirect to /login      │
```

---

## Flow 5: System Startup (Lifespan)

**Trigger:** `uvicorn main:app` หรือ Docker container start

```
uvicorn    FastAPI     Qdrant      PostgreSQL    Redis
   │           │          │             │          │
   │─ startup─►           │             │          │
   │           │─ init_collection()     │          │
   │           │──────────►             │          │
   │           │  GET /collections/     │          │
   │           │  face_registry         │          │
   │           │◄─ exists? ─────────────┤          │
   │           │           │             │          │
   │           │  if NOT exists:        │          │
   │           │──────────►             │          │
   │           │  CREATE collection     │          │
   │           │  vectors={512,cosine}  │          │
   │           │  hnsw={m=16}           │          │
   │           │  quantization=SQ8      │          │
   │           │  payload_index dept_id │          │
   │           │◄─ OK ──────────────────┤          │
   │           │           │             │          │
   │           │  [FaceEngine NOT loaded yet — lazy]│
   │           │           │             │          │
   │◄── ready ─┤           │             │          │
   │  "Application startup complete"               │
   │           │           │             │          │
   │  [First enrollment/scan request]             │
   │           │─ FaceEngine._load()              │
   │           │  Download buffalo_l (~500MB)      │
   │           │  Load ONNX models                 │
   │           │  prepare(ctx_id=0, det_size=640)  │
   │           │◄─ ready ──────────────────────────┤
```
