# Chapter 15: Non-Functional Requirements & Constraints

> NFR คือสิ่งที่ระบบ "ต้องเป็น" ไม่ใช่แค่ "ต้องทำ"  
> ถ้าไม่กำหนด NFR → ระบบทำงานได้แต่ไม่เหมาะสม production

---

## 1. Performance (ประสิทธิภาพ)

### Latency SLA

| Operation | Target (P95) | Target (P99) | Current Measured |
|-----------|-------------|-------------|-----------------|
| Face detection + embedding (1 face, CPU) | < 300ms | < 500ms | ~250ms ✅ |
| Qdrant filtered search (1 face) | < 15ms | < 30ms | ~8ms ✅ |
| Redis filter lookup | < 2ms | < 5ms | < 1ms ✅ |
| Enrollment API (per slot) | < 2s | < 5s | ~500ms ✅ |
| REST API (CRUD operations) | < 100ms | < 200ms | — (not measured) |
| WebSocket round-trip (end-to-end) | < 350ms | < 600ms | ~300ms ✅ |

### Throughput SLA

| Scenario | Target | Note |
|----------|--------|------|
| Concurrent WebSocket connections | ≥ 10 stations | แต่ละสถานีมี 1 connection |
| Simultaneous faces per frame | ≥ 10 faces | Batch inference |
| Enrollment requests per minute | ≥ 60 | 1 slot/sec per operator |
| Attendance logs per hour | ≥ 10,000 | Peak morning shift |

### Throughput Calculation (Peak Load)

```
สมมุติ: 10,000 พนักงาน, เข้างาน 08:00-09:00 (1 ชั่วโมง)
→ 10,000 / 3,600 seconds = ~2.8 สแกนต่อวินาที
→ กระจายใน 10 กล้อง = 0.28 สแกน/วินาที/กล้อง
→ ระบบ handle ได้ง่าย (มี 5-second window ต่อ frame)

กรณีแย่ที่สุด: ทุกคนเดินผ่านพร้อมกัน 10 คน/กล้อง/frame
→ Batch inference 100 faces × 10 stations
→ ต้องการ GPU หรือ scale-out inference layer
```

---

## 2. Reliability & Availability (ความเสถียร)

### Availability Target

| Environment | SLA | Planned Downtime |
|-------------|-----|-----------------|
| Development | 90% | ได้ |
| Production (pilot) | 99% | < 7.3 ชั่วโมง/เดือน |
| Production (full) | 99.9% | < 44 นาที/เดือน |

### Single Point of Failure (SPOF) Analysis

| Component | SPOF? | Mitigation |
|-----------|-------|-----------|
| FastAPI server | ✅ YES | Docker restart policy, process supervisor |
| PostgreSQL | ✅ YES | Daily backup, Docker volume, replication (future) |
| Qdrant | ✅ YES | Docker volume persistence, backup script |
| Redis | ⚠️ Partial | Data reconstructable from PG on restart |
| File Storage (disk) | ✅ YES | Backup, RAID (production) |
| FaceEngine model | ⚠️ Partial | Cache model locally, re-download on startup |

### Graceful Degradation

| Failure | ระบบทำอะไร | Impact |
|---------|-----------|--------|
| Redis DOWN | fallback: query PG สำหรับ station filter | Latency +5ms, ยังสแกนได้ |
| Qdrant DOWN | ส่ง status="service_unavailable" ผ่าน WS | ไม่สแกนได้ แต่กล้อง feed ยังเห็น |
| PostgreSQL DOWN | 503 ทุก REST endpoint | Admin functions หยุด, WS อาจยังทำงานได้ |
| FaceEngine load fail | raise RuntimeError ตอน startup | Server ไม่ start |
| Camera disconnect | Browser ตรวจจาก getUserMedia error | แจ้ง UI, ไม่ส่ง WS |

---

## 3. Scalability (ความสามารถในการขยาย)

### Vertical Scaling (Scale Up)

| Resource | Development | Production (1k emp) | Production (10k emp) |
|---------|------------|--------------------|--------------------|
| RAM | 8 GB | 16 GB | 32 GB |
| CPU | 4 cores | 8 cores | 16 cores |
| GPU | — | Optional (RTX 3060) | Required (RTX 3080+) |
| Storage | 50 GB | 200 GB | 500 GB + |
| Network | 100 Mbps | 1 Gbps | 1 Gbps |

### Horizontal Scaling Path (Future)

```
Phase 1 (Now):
  [All-in-One Single Machine]
  FastAPI + PG + Qdrant + Redis + Storage

Phase 2 (50k employees):
  [Separate Inference]
  FastAPI ─► Inference Worker (GPU) via queue
  FastAPI ─► PostgreSQL
  FastAPI ─► Qdrant
  FastAPI ─► Redis

Phase 3 (100k+ employees):
  [Full Microservices]
  API Gateway ─► Auth Service
              ─► Enrollment Service ─► Inference Cluster
              ─► Scan Service       ─► Qdrant Cluster
              ─► Report Service     ─► PostgreSQL Primary/Replica
```

### Qdrant Scaling

```
10,000 employees × 6 templates = 60,000 vectors
Vector size: 512d × int8 (SQ8) = 512 bytes
Total: 60,000 × 512 bytes = 30.7 MB ← เล็กมาก

100,000 employees × 6 = 600,000 vectors
Total: 600,000 × 512 bytes = 307 MB ← ยังเล็ก

1,000,000 employees × 6 = 6,000,000 vectors
Total: 6,000,000 × 512 bytes = 3 GB ← ต้องการ Qdrant cluster
```

---

## 4. Security (ความปลอดภัย)

### Authentication & Authorization

| Concern | Current State | Production Requirement |
|---------|--------------|----------------------|
| Login | Hardcoded admin/admin | DB-backed, bcrypt hashed |
| JWT Secret | `change-this-...` | 256-bit random secret, rotated |
| JWT Expiry | 8 hours | 1 hour + refresh token |
| Role-based access | ❌ None | Admin, HR, Guard roles |
| API Rate limiting | ❌ None | 100 req/min per IP |
| HTTPS/WSS | ❌ HTTP (dev) | Required in production |

### Data Security

| Data | Classification | Protection |
|------|---------------|-----------|
| Face images (/storage/) | 🔴 Highly Sensitive | Disk encryption, access control |
| Face embeddings (Qdrant) | 🔴 Highly Sensitive | Qdrant auth, network isolation |
| Employee PII (PG) | 🔴 Sensitive | PG auth, encrypted connection |
| Attendance logs | 🟡 Sensitive | Retention policy, audit log |
| JWT tokens | 🟡 Sensitive | Short expiry, HTTPS only |

### PDPA Compliance (พ.ร.บ. คุ้มครองข้อมูลส่วนบุคคล)

| ข้อกำหนด | สถานะ | Action |
|---------|-------|--------|
| Consent ก่อนเก็บ biometric | ❌ ไม่มี UI | เพิ่ม consent flow ใน enrollment |
| Data deletion on request | ⚠️ Partial | DELETE /employees/{id} ลบ cascade แต่ไม่มี audit |
| Data retention limit | ❌ ไม่มี | เพิ่ม auto-purge attendance > 2 ปี |
| Access log / audit trail | ❌ ไม่มี | เพิ่ม audit_logs table |
| Data breach notification | ❌ ไม่มี | Monitoring + alert policy |

---

## 5. Maintainability (ความง่ายในการดูแล)

### Code Quality Standards

| มาตรฐาน | สถานะ |
|---------|-------|
| Type hints (Python) | ✅ ใช้ทั่วทั้ง codebase |
| Pydantic validation | ✅ Input/Output schemas |
| Separation of Concerns | ✅ api/core/db/models แยกชัด |
| Environment config | ✅ .env + pydantic-settings |
| Database migrations | ✅ Alembic |
| Error handling | ⚠️ Partial — บาง endpoint ไม่มี try/except |
| Logging | ❌ ไม่มี structured logging |
| Unit tests | ❌ ไม่มี |
| Integration tests | ❌ ไม่มี |
| API documentation | ✅ FastAPI auto Swagger /docs |

### Technical Debt Register

| ID | Debt | Risk | Priority |
|----|------|------|----------|
| TD-001 | Hardcoded admin/admin | 🔴 High | Phase 3 |
| TD-002 | No attendance auto-logging | 🔴 High | Phase 2 |
| TD-003 | No cooldown for attendance dup | 🔴 High | Phase 2 |
| TD-004 | Qdrant + PG not in same transaction | 🟡 Med | Phase 2 |
| TD-005 | File I/O synchronous (blocking) | 🟡 Med | Phase 3 |
| TD-006 | No structured logging | 🟡 Med | Phase 3 |
| TD-007 | No unit/integration tests | 🟡 Med | Phase 3 |
| TD-008 | JWT no refresh token | 🟡 Med | Phase 2 |
| TD-009 | No rate limiting | 🟡 Med | Phase 4 |
| TD-010 | FaceEngine not thread-safe (GIL) | 🟢 Low | Phase 4 |

---

## 6. Usability (ความง่ายในการใช้)

### UI Response Time (Perceived Performance)

| Action | Acceptable | Good |
|--------|-----------|------|
| Login | < 1s | < 500ms |
| Page navigation | < 300ms | < 100ms |
| Table load (50 rows) | < 1s | < 500ms |
| Scan overlay update | < 500ms | < 300ms |
| Enrollment capture → feedback | < 2s | < 1s |

### Error Messages (User-Facing)

| Error Code | ข้อความที่ user เห็น |
|-----------|-------------------|
| NO_FACE | "ไม่พบใบหน้าในภาพ กรุณาถ่ายใหม่" |
| QUALITY_FAILED | "ภาพไม่ชัดเพียงพอ กรุณาปรับแสงหรือระยะ" |
| MULTIPLE_FACES | "พบหลายใบหน้า กรุณาให้มีใบหน้าเดียวในภาพ" |
| 401 | "Session หมดอายุ กรุณา Login ใหม่" |
| 500 | "เกิดข้อผิดพลาด กรุณาแจ้งผู้ดูแลระบบ" |
| WS Disconnect | "การเชื่อมต่อขาดหาย กำลังเชื่อมต่อใหม่..." |

---

## 7. Constraints (ข้อจำกัด)

### Technical Constraints

| ข้อจำกัด | เหตุผล | ผลกระทบ |
|---------|--------|--------|
| Python 3.12 เท่านั้น | buffalo_l ONNX compatibility | ไม่ upgrade Python กลาง project |
| numpy < 3.0 | insightface Cython extension | pin ใน requirements.txt |
| C: drive ไม่ใช้ | พื้นที่จำกัด | MSVC + venv ต้องอยู่ F: |
| ไม่มี NVIDIA GPU | Hardware | ใช้ CPU mode (DirectML future) |
| InsightFace buffalo_l model | ~500MB download | ต้องการ internet ครั้งแรก |

### Business Constraints

| ข้อจำกัด | รายละเอียด |
|---------|-----------|
| ต้อง On-Premise | ข้อมูลใบหน้าห้ามออกนอกองค์กร |
| รองรับ 10,000+ พนักงาน | Scale requirement จาก Day 1 |
| พนักงาน 1 คน อยู่ 1 แผนก | Business rule — ห้ามข้ามแผนก |
| กล้อง 1 ตัว N แผนก | Flexible station scope |
| ลงเวลาซ้ำ cooldown 5 นาที | ป้องกัน double-logging |
