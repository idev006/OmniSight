# OmniSight — Sprint Log

> บันทึกสิ่งที่ทำในแต่ละ session/sprint  
> ใช้เป็น changelog และ handover document สำหรับ session AI ถัดไป

---

## Sprint 1 — Project Inception
**วันที่:** 2026-05-15 (Session 1)  
**เป้าหมาย:** วางแผนโครงการ เขียนเอกสาร

### สิ่งที่ทำ
- วิเคราะห์ความต้องการ: ระบบลงเวลา 10,000+ คน ด้วย face recognition
- เลือก tech stack: FastAPI + Vue 3 + InsightFace + Qdrant + Redis + PostgreSQL
- เขียนเอกสาร 13 บท (`doc/claude_version/chapter_00` ถึง `chapter_12`)
- ออกแบบ Data Schema: 6 tables
- ออกแบบ API Contract: 30+ endpoints

### Output
- `doc/claude_version/` — 13 chapter documentation
- ยังไม่มีโค้ด

---

## Sprint 2 — Foundation Build
**วันที่:** 2026-05-16 (Session 2)  
**เป้าหมาย:** สร้าง project skeleton ครบทุกไฟล์

### สิ่งที่ทำ
- สร้าง project structure (backend/frontend/doc)
- `docker-compose.yml` — PostgreSQL 16 + Qdrant + Redis
- `docker-compose.gpu.yml` — variant สำหรับ GPU
- Backend skeleton:
  - `main.py` — FastAPI app + lifespan + CORS
  - `app/models/orm.py` — SQLAlchemy ORM (6 models)
  - `app/models/schemas.py` — Pydantic schemas
  - `app/core/config.py` — Settings จาก .env
  - `app/core/face_engine.py` — FaceEngine (lazy-load)
  - `app/db/postgres.py`, `qdrant.py`, `redis.py`
  - `app/api/` — 8 router files
  - `alembic/` — async migration setup
- Frontend (สร้างทุกไฟล์ manually เพราะ `npm create vite` fail บน existing dir):
  - `vite.config.js`, `tailwind.config.js`, `postcss.config.js`
  - `src/main.js`, `App.vue`, `style.css`
  - `src/router/index.js`, `src/stores/auth.js`, `src/api/client.js`
  - `src/layouts/AppLayout.vue`
  - `src/views/` — 7 views (Login, Scan, Employees, Enrollment, Departments, Stations, Attendance)
- Batch files: `start-dev.bat`, `start-backend.bat`, `start-frontend.bat`, `migrate.bat`

### ปัญหาที่พบและแก้ไข
| ปัญหา | การแก้ไข |
|-------|---------|
| `npm create vite .` cancel เพราะ dir มีไฟล์แล้ว | สร้างไฟล์ทุกอย่างด้วยตนเอง |
| `migrate.bat` ไม่ทำงาน — ไม่มีไฟล์ migration | รัน `autogenerate` แล้ว `upgrade` |
| 500 "relation departments does not exist" | รัน migration ก่อนเปิด frontend |

### Output
- Project scaffold ครบทุกไฟล์
- Database tables สร้างแล้ว

---

## Sprint 3 — InsightFace Installation
**วันที่:** 2026-05-16 (Session 2 ต่อ)  
**เป้าหมาย:** ติดตั้ง insightface บน Windows ที่ MSVC อยู่ใน F: drive

### ปัญหาและขั้นตอนแก้ไข
ลำดับความพยายาม 5 ครั้ง:

| # | สิ่งที่ลอง | ผล |
|---|----------|-----|
| 1 | `pip install insightface` ตรง ๆ | ❌ MSVC not found |
| 2 | เรียก vcvarsall.bat ก่อน pip | ❌ Build isolation ป้องกัน env vars |
| 3 | `--no-build-isolation` | ❌ No module Cython |
| 4 | ติดตั้ง Cython ก่อน | ❌ setuptools ค้น registry ไม่พบ |
| 5 | `DISTUTILS_USE_SDK=1 + MSSdk=1` | ✅ สำเร็จ! |

หลังติดตั้ง: numpy version mismatch (1.26.4 → 2.4.5)  
แก้: `--force-reinstall --no-cache-dir --no-deps` rebuild Cython extension

### Output
- `insightface 0.7.3` installed และ import ได้
- `doc/claude_version/other/lesson_learned_insightface_msvc_non_c_drive.md`

---

## Sprint 4 — Integration Testing
**วันที่:** 2026-05-17 (Session 3)  
**เป้าหมาย:** ทดสอบระบบ end-to-end

### สิ่งที่ทำ
- Start backend (port 8000) — uvicorn --reload
- ทดสอบ API endpoints ทั้งหมด
- ทดสอบ Enrollment pipeline:
  - ดาวน์โหลดรูป biden.jpg (2204x970)
  - Enroll 6 slots สำเร็จ, quality=0.799 ทุก slot
  - Qdrant มี 7 vectors (6 จริง + 1 orphaned)
- ทดสอบ WebSocket scan:
  - เชื่อมต่อสำเร็จ
  - ส่ง frame 2204x970 → detect ได้ 1 face
  - Match กับ employee ถูกต้อง, confidence=99.57%

### Bug ที่พบ
| Bug | สาเหตุ | การแก้ไข |
|-----|--------|---------|
| BUG-001: JWT หมดอายุระหว่างทดสอบ | Token expire สั้น + test loop ช้า | ขอ token ใหม่ทุก test |
| BUG-004: Qdrant delete 500 | ใช้ `list` แทน `PointIdsList` | แก้ `enrollment.py` แล้ว |

### Output
- ยืนยัน face recognition pipeline ทำงานได้จริง
- `pip freeze > requirements.txt` — 95 packages locked

---

## Sprint 5 — GitHub Push
**วันที่:** 2026-05-17 (Session 3 ต่อ)  
**เป้าหมาย:** Push โค้ดขึ้น GitHub

### สิ่งที่ทำ
- สร้าง `.gitignore` (exclude: my_env, .env, storage, node_modules, .claude)
- `git init` + `git remote add origin`
- ตรวจสอบ security — `.env` ไม่ถูก stage
- Commit 72 files (initial)
- Commit requirements.txt (pip freeze)
- Push สำเร็จ

### Output
- https://github.com/idev006/OmniSight — 2 commits

---

## Sprint 6 — Project Management Documentation
**วันที่:** 2026-05-17 (Session 3 ต่อ)  
**เป้าหมาย:** สร้างเอกสาร PM เพื่อ track ความคืบหน้า

### สิ่งที่ทำ
- `doc/project_management/PROJECT_STATUS.md` — dashboard + phase tracking
- `doc/project_management/DECISIONS_LOG.md` — ADR 8 รายการ
- `doc/project_management/SPRINT_LOG.md` — ไฟล์นี้

---

## Sprint 7 — Attendance Auto-Logging ✅ DONE
**วันที่:** 2026-05-17 (Session 4)  
**เป้าหมาย:** บันทึก attendance เมื่อ scan match + cooldown ป้องกัน log ซ้ำ

### สิ่งที่ทำ

1. **`backend/app/db/redis.py`** — เพิ่ม cooldown functions
   - `check_attendance_cooldown(employee_id, station_id)` — ตรวจ Redis key
   - `set_attendance_cooldown(employee_id, station_id)` — ตั้ง TTL 300s
   - เพิ่ม try/except + fallback สำหรับกรณี Redis ล่ม

2. **`backend/app/services/attendance_service.py`** — NEW FILE
   - `log_attendance(db, employee_id, station_id, confidence_score)` → bool
   - Flow: check cooldown → INSERT AttendanceLog → set cooldown → return True/False
   - rollback on exception

3. **`backend/app/api/websocket.py`** — FULL REWRITE
   - ใช้ `async with async_session_factory() as db:` สำหรับ DB session
   - เรียก `log_attendance()` ทุกครั้งที่ Qdrant match
   - ส่ง `attendance_logged` field ใน FaceResult

4. **`backend/app/db/postgres.py`** — เพิ่ม alias
   - `async_session_factory = AsyncSessionLocal` สำหรับใช้นอก FastAPI DI

5. **`backend/app/models/schemas.py`** — เพิ่ม field
   - `attendance_logged: bool = False` ใน FaceResult

6. **`backend/test_sprint7_attendance.py`** — Test script
   - ยืนยัน match, DB insert, cooldown ครบ

### ผลการทดสอบ (test_sprint7_attendance.py)

```
[OK] Token acquired
[OK] Face matched!
     - Status: match
     - Confidence: 0.9976 (99.76%)
     - attendance_logged: True
[OK] 1 new attendance log inserted in DB (1 -> 2)
[OK] Cooldown working — second scan not logged (attendance_logged: False)
Sprint 7 attendance auto-logging: COMPLETE
```

### GitHub
- Commit: `dac4ab2` — feat(sprint7): attendance auto-logging with Redis cooldown
- Push: origin/master

---

## Sprint 8 — Next (TODO)
**เป้าหมาย:** User Management + Authorization

### งานที่ต้องทำถัดไป (ลำดับความสำคัญ)

1. **[HIGH] User Management + RBAC**
   - สร้าง `users` table: id, username, hashed_password, role (ADMIN/HR/OPERATOR)
   - สร้าง `user_stations` table: user_id, station_id (OPERATOR access control)
   - `/api/v1/users` CRUD endpoints
   - bcrypt password hashing แทน hardcoded admin/admin

2. **[HIGH] WebSocket station authorization**
   - ตรวจสอบ JWT token จริง (ตอนนี้แค่ไม่ว่าง)
   - OPERATOR ต้องมี station_id ใน JWT claims หรือ user_stations table
   - ปฏิเสธ connection ถ้า user ไม่มีสิทธิ์ใช้ station นั้น

3. **[HIGH] JWT fix (BUG-001)**
   - เพิ่ม `ACCESS_TOKEN_EXPIRE_HOURS=8` ใน config
   - หรือเพิ่ม refresh token endpoint

4. **[MED] BUG-002: Orphaned Qdrant vector**
   - เขียน reconcile script: ลบ Qdrant points ที่ไม่มีใน face_templates table

5. **[MED] Attendance Report page**
   - Frontend: daily/monthly summary
   - Backend: aggregate query (GROUP BY date/dept)
   - Export CSV button

6. **[MED] Face quality gate ก่อน enrollment**
   - Reject ถ้า quality_score < 0.6

7. **[LOW] Camera agent (RTSP bridge)**
   - `camera_agent.py`: RTSP → JPEG → WebSocket
   - รองรับ IP camera / CCTV

---

## Context สำหรับ AI Session ถัดไป

เมื่อเริ่ม session ใหม่ให้อ่าน:
1. `doc/project_management/PROJECT_STATUS.md` — ภาพรวม + phase progress
2. `doc/project_management/SPRINT_LOG.md` — Sprint 7 done, Sprint 8 TODO
3. `backend/app/api/auth.py` — JWT (ตอนนี้ hardcoded admin/admin)
4. `backend/app/api/websocket.py` — WebSocket scan (attendance logging สมบูรณ์แล้ว)

**Environment:**
- venv: `F:\programming\python\OmniSight\my_env`
- Backend start: `start-backend.bat` (uvicorn ที่ port 8000)
- DB migration: `migrate.bat upgrade`
- Services: Docker Desktop → PostgreSQL (5432), Qdrant (6333), Redis (6379)
- Test script: `backend/test_sprint7_attendance.py`

**State ปัจจุบัน:**
- emp1 (db421a76): enrolled 6/6 slots ✅
- emp2 (848449d0): enrolled 0/6
- sta1 (ccd829a0): ไม่มี dept filter (scan พนักงานทุกคน)
- attendance_logs: 2 records (emp1 + sta1, 2026-05-17)
- Qdrant: 7 vectors (6 จริง + 1 orphaned จาก BUG-002)
