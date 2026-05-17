# OmniSight — AI Session Handover

> อ่านไฟล์นี้ก่อนทุกครั้งที่เริ่ม session ใหม่

---

## ⚠️ Path สำคัญ — ห้ามผิด

| สิ่งของ | Path |
|---------|------|
| **เอกสารทุกฉบับ** | `F:\programming\python\OmniSight\doc\cluade_version\` |
| **PM docs** | `F:\programming\python\OmniSight\doc\project_management\` |
| **Python venv (3.12)** | `F:\programming\python\OmniSight\my_env\` ← **ที่เดียวเท่านั้น** |
| Python exe | `F:\programming\python\OmniSight\my_env\Scripts\python.exe` |
| pip | `F:\programming\python\OmniSight\my_env\Scripts\pip.exe` |
| Backend | `F:\programming\python\OmniSight\backend\` |
| Frontend | `F:\programming\python\OmniSight\frontend\` |

> **หมายเหตุ:** โฟลเดอร์เอกสารชื่อ `cluade_version` (สะกดผิดโดยตั้งใจ ห้ามแก้ชื่อ เพราะมีไฟล์อยู่แล้ว)

---

## โครงการคืออะไร

**OmniSight** — ระบบลงเวลางานด้วย Face Recognition  
เป้าหมายแรก: Enterprise HR (พนักงานบริษัท)  
เป้าหมายในอนาคต: โรงเรียน, ห้องประชุม, Multi-purpose

**Tech Stack:**
- Backend: FastAPI (Python 3.12) + SQLAlchemy async + Alembic
- AI: InsightFace buffalo_l (ONNX) — face detection + embedding
- Vector DB: Qdrant (HNSW + SQ8)
- Cache: Redis (station filter, attendance cooldown)
- SQL DB: PostgreSQL 16
- Frontend: Vue 3 + Vite + Tailwind CSS
- Services: Docker (Postgres 5432, Qdrant 6333, Redis 6379)

---

## Environment Setup

```powershell
# Start backend
cd F:\programming\python\OmniSight
.\start-backend.bat       # uvicorn at http://localhost:8000

# Start frontend
.\start-frontend.bat      # vite at http://localhost:5173

# Run migration
.\migrate.bat upgrade

# Install package
.\my_env\Scripts\pip.exe install <package>

# Run Python script
.\my_env\Scripts\python.exe backend\<script>.py

# Default login
username: admin
password: admin
```

---

## สถานะปัจจุบัน

### Phase Progress
```
Phase 1 — Foundation     ████████████████████ 100%  ✅ DONE
Phase 2 — AI Core        ████████░░░░░░░░░░░░  40%  🔄 IN PROGRESS
Phase 3 — HR Features    ░░░░░░░░░░░░░░░░░░░░   0%  ⏳ PENDING
Phase 4 — Multi-Camera   ░░░░░░░░░░░░░░░░░░░░   0%  📐 DESIGNED
Phase 5 — Production     ░░░░░░░░░░░░░░░░░░░░   0%  ⏳ PENDING
```

### Data ใน DB (ณ Sprint 7)
| รายการ | ค่า |
|--------|-----|
| Employee | emp1 (6/6 enrolled ✅), emp2 (0/6) |
| Station | sta1 (ccd829a0), sta2 (07464848) |
| Attendance logs | 2 records |
| Qdrant vectors | 7 (6 จริง + 1 orphaned, BUG-002) |

---

## งานที่ต้องทำถัดไป (Sprint 8)

### ลำดับความสำคัญ
1. 🔴 **User Management + RBAC** — users table, bcrypt, roles
2. 🔴 **WebSocket auth จริง** — ตรวจ JWT + station permission
3. 🔴 **JWT expiry fix (BUG-001)** — ACCESS_TOKEN_EXPIRE_HOURS=8
4. 🔴 **Camera model + CRUD** — cameras table, /api/v1/cameras
5. 🔴 **CameraManager + Pilot Console WS** — Redis pub/sub
6. 🟡 **BUG-002** — ลบ orphaned Qdrant vector
7. 🟡 **Attendance Report** — daily/monthly + CSV export

---

## Bug ที่ยังเปิดอยู่

| ID | ปัญหา | Severity |
|----|-------|----------|
| BUG-001 | JWT token หมดอายุเร็ว | Medium |
| BUG-002 | Orphaned Qdrant vector (7 แทน 6) | Low |

---

## เอกสารสำคัญ

| ไฟล์ | เนื้อหา |
|------|---------|
| `doc/project_management/PROJECT_STATUS.md` | Dashboard + phase tracking |
| `doc/project_management/SPRINT_LOG.md` | Sprint history + context |
| `doc/project_management/DECISIONS_LOG.md` | ADR-001 ถึง ADR-011 |
| `doc/cluade_version/chapter_17_multi_camera_pilot_console.md` | Multi-camera & Pilot Console design |

---

## GitHub

- Repository: https://github.com/idev006/OmniSight
- Branch: master
- Latest commit: `6bb79e9` — multi-camera architecture design
- .gitignore excludes: `my_env/`, `.env`, `storage/`, `frontend/node_modules/`

---

## Key Architecture Decisions (สรุป)

| ADR | การตัดสินใจ |
|-----|------------|
| ADR-001 | InsightFace buffalo_l (all-in-one pipeline) |
| ADR-002 | Qdrant HNSW + SQ8 |
| ADR-003 | Redis เก็บ station dept_filter |
| ADR-004 | 6 face templates ต่อคน |
| ADR-005 | WebSocket binary JPEG |
| ADR-008 | Match threshold 0.72 cosine |
| ADR-009 | 1 WebSocket per camera |
| ADR-010 | Redis Pub/Sub เป็น event bus |
| ADR-011 | Bidirectional WS control สำหรับ smartphone |

---

*อัพเดทล่าสุด: 2026-05-17 (Sprint 8 design)*
