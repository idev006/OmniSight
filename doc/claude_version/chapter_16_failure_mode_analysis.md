# Chapter 16: Failure Mode Analysis & Resilience Design

> FMEA (Failure Mode and Effects Analysis) — วิเคราะห์ว่าระบบพังได้อย่างไร  
> และออกแบบให้พังอย่างสง่างาม (Graceful Degradation)

---

## Failure Taxonomy

```
ระบบพัง
├── Infrastructure Failures
│   ├── Database down (PG, Qdrant, Redis)
│   ├── Disk full
│   └── Network partition
├── Application Failures
│   ├── FaceEngine crash / OOM
│   ├── WebSocket disconnect
│   └── API unhandled exception
├── Data Failures
│   ├── Orphaned Qdrant vectors
│   ├── Corrupted face image
│   └── Stale Redis cache
└── Security Failures
    ├── JWT token compromise
    ├── Unauthorized access
    └── Data breach
```

---

## FMEA Matrix

| ID | Component | Failure Mode | Effect | Severity | Probability | Detection | Mitigation |
|----|-----------|-------------|--------|----------|-------------|-----------|-----------|
| F-01 | PostgreSQL | Service down | REST API 503, no logging | 🔴 High | Low | 503 response | Docker restart policy, health check |
| F-02 | Qdrant | Service down | Scan fails, 500 WS | 🔴 High | Low | WS error | Docker restart, fallback message to UI |
| F-03 | Redis | Service down | No station filter | 🟡 Med | Low | Miss exception | Fallback: query PG for dept_ids |
| F-04 | FaceEngine | OOM crash | All scans fail | 🔴 High | Med (CPU) | Process exit | Limit model memory, restart policy |
| F-05 | Disk | Storage full | Enrollment fail | 🟡 Med | Med | ENOSPC | Monitor disk usage, alert at 80% |
| F-06 | WebSocket | Client disconnect | Connection leak | 🟡 Med | High (mobile) | Disconnect event | except WebSocketDisconnect (done ✅) |
| F-07 | Qdrant+PG | Transaction split | Orphaned vector | 🟡 Med | Low | Manual audit | Saga pattern / reconciliation job |
| F-08 | Camera | Feed lost | No frames sent | 🟢 Low | Med | JS error | UI shows "กล้องขาดการเชื่อมต่อ" |
| F-09 | JWT | Token stolen | Unauthorized access | 🔴 High | Low | Anomaly detection | Short expiry, HTTPS, refresh token |
| F-10 | buffalo_l | Download fail | Engine not loaded | 🟡 Med | Low | RuntimeError | Pre-download, bundle in Docker |
| F-11 | ONNX Runtime | Inference hang | Frame processing stuck | 🔴 High | Low | Timeout | async timeout wrapper |
| F-12 | Redis | Stale cache | Wrong dept filter | 🟡 Med | Low | Logic error | TTL or invalidate on PG update (done ✅) |

---

## Resilience Patterns ที่ควรเพิ่ม

### Pattern 1: Redis Fallback (F-03)

```python
# ปัจจุบัน (fragile)
async def get_station_filter(station_id: str) -> list[int]:
    data = await redis.get(f"station:{station_id}:depts")
    return json.loads(data) if data else []

# ควรเป็น (resilient)
async def get_station_filter(station_id: str) -> list[int]:
    try:
        data = await redis.get(f"station:{station_id}:depts")
        if data:
            return json.loads(data)
    except Exception:
        logger.warning(f"Redis miss for station {station_id}, fallback to PG")
    
    # Fallback: query PostgreSQL
    async with get_db() as db:
        result = await db.execute(
            select(StationDepartment.dept_id)
            .where(StationDepartment.station_id == station_id)
        )
        return [row[0] for row in result.fetchall()]
```

### Pattern 2: ONNX Inference Timeout (F-11)

```python
# ป้องกัน inference hang
async def get_detections_safe(img: np.ndarray, timeout: float = 5.0):
    loop = asyncio.get_event_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(None, face_engine.get_detections, img),
            timeout=timeout
        )
        return result
    except asyncio.TimeoutError:
        logger.error("FaceEngine timeout — skipping frame")
        return []
```

### Pattern 3: Saga / Compensating Transaction (F-07)

```python
# ปัจจุบัน (at-risk)
await qdrant.upsert(...)    # ← ถ้า PG fail หลังนี้ → orphaned vector
await db.add(template)
await db.commit()

# ควรเป็น (safe)
qdrant_id = uuid.uuid4()
try:
    await qdrant.upsert(...)
    await db.add(template)
    await db.commit()
except Exception:
    # Compensating transaction
    await qdrant.delete(
        collection_name=settings.qdrant_collection,
        points_selector=PointIdsList(points=[str(qdrant_id)])
    )
    raise
```

### Pattern 4: Attendance Cooldown (F - Double Logging)

```python
# ป้องกัน log ซ้ำภายใน 5 นาที
async def log_attendance_safe(employee_id: str, station_id: str, ...):
    cooldown_key = f"attendance:{employee_id}:{datetime.utcnow().date()}"
    
    # Check cooldown in Redis
    if await redis.get(cooldown_key):
        return  # Skip — logged recently
    
    # Insert to PostgreSQL
    await db.add(AttendanceLog(...))
    await db.commit()
    
    # Set cooldown TTL = 5 minutes
    await redis.setex(cooldown_key, 300, "1")
```

### Pattern 5: WebSocket Reconnection (Client-side)

```javascript
// ปัจจุบัน (fragile)
const ws = new WebSocket(url)

// ควรเป็น (resilient)
function connectWithRetry(url, maxRetries = 5) {
  let retries = 0
  let ws = null
  
  function connect() {
    ws = new WebSocket(url)
    
    ws.onclose = (event) => {
      if (retries < maxRetries) {
        const delay = Math.pow(2, retries) * 1000  // exponential backoff
        retries++
        console.log(`WS reconnecting in ${delay}ms...`)
        setTimeout(connect, delay)
      } else {
        showError('การเชื่อมต่อขาดหาย กรุณา refresh หน้าเว็บ')
      }
    }
    
    ws.onopen = () => {
      retries = 0  // reset on success
    }
  }
  
  connect()
  return () => ws  // getter
}
```

---

## Disaster Recovery Plan

### Scenario: Qdrant Data Loss

```
1. ตรวจสอบว่า face_templates ใน PostgreSQL ยังครบ
2. รัน reconciliation script:
   - SELECT * FROM face_templates
   - สำหรับแต่ละ template: อ่านรูปจาก image_path
   - Re-extract embedding ด้วย FaceEngine
   - Upsert กลับเข้า Qdrant
3. เวลา: 10,000 พนักงาน × 6 templates × 500ms = ~8 ชั่วโมง (CPU)
           → GPU: ~1 ชั่วโมง
```

### Scenario: PostgreSQL Data Loss

```
1. Restore จาก backup (daily)
2. ข้อมูลที่หายหลัง backup:
   - Attendance logs (ต้องกู้จาก manual records)
   - Employees ที่เพิ่งสร้าง
3. Qdrant ยังคงมี embeddings อยู่ แต่ไม่มี employee_id mapping → ต้องลบและ re-enroll
4. Mitigation: ทำ backup ทุก 6 ชั่วโมง (ลด data loss window)
```

### Scenario: Server Crash During Peak Hours

```
1. Docker restart policy: always → service กลับมาใน < 30 วินาที
2. FaceEngine reload: buffalo_l model อยู่ใน ~/.insightface/models/ → ไม่ต้อง download ใหม่
3. Redis reconnect: aioredis auto-reconnect
4. WebSocket: Client ต้อง reconnect (ต้องมี exponential backoff บน browser)
5. Attendance cooldown: หาย (Redis cleared) → อาจ log ซ้ำ
   → Mitigation: check PG เมื่อ Redis miss
```

---

## Health Check Design

### Endpoints ที่ควรมี

```python
@app.get("/health")          # ✅ มีแล้ว — basic
@app.get("/health/live")     # ❌ ยังไม่มี — kubernetes liveness probe
@app.get("/health/ready")    # ❌ ยังไม่มี — kubernetes readiness probe
@app.get("/health/deep")     # ❌ ยังไม่มี — ตรวจทุก dependency
```

### `/health/deep` Design

```json
GET /health/deep

{
  "status": "healthy",
  "timestamp": "2026-05-17T10:00:00Z",
  "components": {
    "postgres": {
      "status": "healthy",
      "latency_ms": 3,
      "pool_size": 10,
      "pool_used": 2
    },
    "qdrant": {
      "status": "healthy",
      "latency_ms": 8,
      "collection": "face_registry",
      "vectors_count": 60000
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 1
    },
    "face_engine": {
      "status": "healthy",
      "model": "buffalo_l",
      "provider": "CPUExecutionProvider",
      "loaded": true
    },
    "disk": {
      "status": "healthy",
      "free_gb": 45.2,
      "used_percent": 23
    }
  }
}
```

---

## Monitoring & Alerting (ที่ควรมี)

| Metric | Alert Threshold | Action |
|--------|----------------|--------|
| Inference latency P95 | > 500ms | Scale-up / check CPU |
| WebSocket connection count | > 20 | Investigate leak |
| Attendance log rate | 0 during work hours | Camera/scan issue |
| Disk usage | > 80% | Cleanup / expand |
| Qdrant vector count drift | > 5% vs PG count | Run reconciliation |
| Failed enrollment rate | > 10% | Camera quality issue |
| 500 error rate | > 1% | Code/infra issue |
