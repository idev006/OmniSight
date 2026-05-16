# Chapter 11: Implementation Roadmap

## หลักการ: Build Fast, Validate Early

สร้างระบบที่ใช้งานได้จริงให้เร็วที่สุด แล้วค่อยเพิ่ม Feature ตามความต้องการที่พิสูจน์แล้ว

---

## โครงสร้างโปรเจกต์

```
OmniSight/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI Routers
│   │   │   ├── auth.py
│   │   │   ├── employees.py
│   │   │   ├── stations.py
│   │   │   ├── enrollment.py
│   │   │   ├── attendance.py
│   │   │   └── websocket.py
│   │   ├── core/
│   │   │   ├── face_engine.py    # InsightFace + ONNX
│   │   │   ├── liveness.py       # MiniFASNet
│   │   │   └── config.py
│   │   ├── db/
│   │   │   ├── postgres.py       # SQLAlchemy
│   │   │   ├── qdrant.py         # Qdrant client
│   │   │   └── redis.py          # Redis client
│   │   ├── models/
│   │   │   ├── schemas.py        # Pydantic models
│   │   │   └── orm.py            # SQLAlchemy models
│   │   └── services/
│   │       ├── scan_service.py   # Scan pipeline logic
│   │       └── enroll_service.py # Enrollment logic
│   ├── alembic/                  # DB Migrations
│   ├── main.py
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   │   ├── ScanView.vue
│   │   │   ├── admin/
│   │   │   │   ├── Dashboard.vue
│   │   │   │   ├── EmployeeList.vue
│   │   │   │   ├── FaceEnrollment.vue
│   │   │   │   ├── StationManager.vue
│   │   │   │   └── AttendanceReport.vue
│   │   ├── components/
│   │   │   ├── OverlayCanvas.vue
│   │   │   ├── IdentityCard.vue
│   │   │   └── PhotoSlotGrid.vue
│   │   ├── stores/
│   │   │   ├── scan.js
│   │   │   └── auth.js
│   │   └── composables/
│   │       └── useScanSocket.js
│   └── package.json
│
├── storage/
│   └── faces/                    # Original face images
│
└── docker-compose.yml
```

---

## Phase 1: Foundation (สัปดาห์ที่ 1-3)

**เป้าหมาย:** ระบบสแกนหน้าพื้นฐานทำงานได้ End-to-End

### Backend
- [ ] Setup FastAPI + PostgreSQL + Qdrant + Redis ด้วย Docker Compose
- [ ] Alembic migrations สำหรับทุก Table
- [ ] Face Engine: InsightFace buffalo_l + ONNX Runtime
- [ ] Enrollment API (6 รูป, Quality Check)
- [ ] WebSocket scan endpoint (single face)
- [ ] Qdrant: Create collection + payload index

### Frontend
- [ ] Project setup: Vite + Vue 3 + DaisyUI + Tailwind
- [ ] Login page
- [ ] Scan View: Video stream + Canvas overlay
- [ ] WebSocket connection + รับผลลัพธ์
- [ ] Identity Card component (Fade-in animation)

### Deliverable
> พนักงาน 1 คน เดินผ่านกล้อง → ชื่อเด้งขึ้นมา ✅

---

## Phase 2: Core Features (สัปดาห์ที่ 4-6)

**เป้าหมาย:** ระบบครบถ้วนสำหรับ Production

### Backend
- [ ] Batch inference (10 faces พร้อมกัน)
- [ ] Strict Filter: dept_id via Redis + Qdrant Payload Filter
- [ ] Station management API
- [ ] station_departments: N แผนกต่อกล้อง
- [ ] Attendance Log API + Manual Override
- [ ] Anti-Spoofing: MiniFASNet integration
- [ ] Authentication: JWT + Role-based

### Frontend
- [ ] Multi-face Overlay (Collision Avoidance)
- [ ] Face Enrollment UI (6 Photo Slots + Auto-capture)
- [ ] Admin Dashboard (Stats widgets)
- [ ] Station Manager + Scope Configuration
- [ ] Employee management CRUD

### Deliverable
> 10 คนพร้อมกัน, Strict Filter ทำงาน, Admin ตั้ง Scope ได้ ✅

---

## Phase 3: Reporting & Polish (สัปดาห์ที่ 7-8)

**เป้าหมาย:** ระบบพร้อมใช้งานจริงในองค์กร

### Backend
- [ ] Attendance Report API (by date, dept, employee)
- [ ] Export: CSV / Excel
- [ ] Health Check endpoints
- [ ] Unknown Alert logging
- [ ] Performance tuning: Int8 Quantization

### Frontend
- [ ] Attendance Report page (ตาราง + กราฟ)
- [ ] Export CSV/Excel
- [ ] System Health widget บน Scan View
- [ ] Recent Logs sidebar บน Scan View
- [ ] Error handling & offline detection

### Deliverable
> HR ออก Report ได้, ระบบพร้อม Deploy จริง ✅

---

## Phase 4: Hardening (สัปดาห์ที่ 9-10)

**เป้าหมาย:** ระบบปลอดภัยและเสถียร

- [ ] HTTPS/WSS
- [ ] Audit Logging
- [ ] Auto-restart ด้วย Docker health check
- [ ] Data Retention policy (ลบ Log เก่า)
- [ ] Load testing: 10 กล้อง × 10 คนพร้อมกัน
- [ ] Memory leak testing (24-hour run)
- [ ] PDPA: Data deletion workflow

---

## Docker Compose

### CPU Mode (ปัจจุบัน — Windows 11 / Linux)

```yaml
# docker-compose.yml
services:
  backend:
    build:
      context: ./backend
      args:
        ONNXRUNTIME_PROVIDER: cpu      # ← เปลี่ยนเป็น cuda หรือ dml
    environment:
      - ONNXRUNTIME_PROVIDER=cpu
    ports: ["8000:8000"]
    depends_on: [postgres, qdrant, redis]
    volumes: ["./storage:/app/storage"]

  frontend:
    build: ./frontend
    ports: ["3000:80"]

  postgres:
    image: postgres:16
    volumes: ["pgdata:/var/lib/postgresql/data"]

  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]
    volumes: ["qdrantdata:/qdrant/storage"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
```

### GPU Mode (Cloud / Local NVIDIA GPU)

```yaml
# docker-compose.gpu.yml  (override file)
services:
  backend:
    build:
      args:
        ONNXRUNTIME_PROVIDER: cuda
    environment:
      - ONNXRUNTIME_PROVIDER=cuda
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

```bash
# รันใน CPU mode
docker compose up

# รันใน GPU mode
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up
```

### Windows 11 DirectML Mode (AMD/Intel iGPU)

```yaml
# docker-compose.dml.yml  (override file)
services:
  backend:
    environment:
      - ONNXRUNTIME_PROVIDER=dml
```

```bash
docker compose -f docker-compose.yml -f docker-compose.dml.yml up
```

---

## Deployment Environments

| Environment | OS | Provider | ใช้เมื่อ |
|-------------|-----|---------|---------|
| Local Dev | Windows 11 | CPU (AVX-512) | พัฒนาและทดสอบ |
| Local Prod | Windows 11 | DirectML / CUDA | ติดตั้งจริงในองค์กร |
| On-Premise | Linux | CUDA | Server ภายในองค์กร |
| Cloud Scale | Linux | CUDA (T4/A10G) | ขยายรองรับหลายองค์กร |

---

## Performance Milestones

| Milestone | เป้าหมาย | ทดสอบด้วย |
|-----------|---------|----------|
| Single face scan | < 300ms | 1 กล้อง, 1 คน |
| 10 faces batch | < 400ms | 1 กล้อง, 10 คน |
| Multi-station | < 400ms | 5 กล้อง, แต่ละตัว 5 คน |
| Memory stability | < 4 GB RAM | ใช้งาน 24 ชั่วโมง |
| Uptime | 99.9% | 30 วัน |

---

## ลำดับความสำคัญของ Dependencies

```
Phase 1 ต้องเสร็จก่อน Phase 2
Phase 2 ต้องเสร็จก่อน Phase 3
Phase 3 และ Phase 4 สามารถทำบางส่วนพร้อมกันได้

Critical Path:
Face Engine → Qdrant → WebSocket → Overlay → Multi-face → Filter → Report
```
