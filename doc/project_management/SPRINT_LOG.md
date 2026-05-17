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

## Sprint 7 — Next (TODO)
**เป้าหมาย:** Phase 2 เริ่ม

### งานที่ต้องทำถัดไป (ลำดับความสำคัญ)

1. **[HIGH] Attendance auto-logging**
   - ไฟล์: `backend/app/api/websocket.py`
   - เมื่อ Qdrant search match → INSERT AttendanceLog
   - ใช้ Redis TTL (`attendance:{emp_id}:{date}`) ป้องกัน log ซ้ำใน 5 นาที

2. **[HIGH] JWT expiry fix**
   - ไฟล์: `backend/app/api/auth.py`, `backend/.env`
   - เพิ่ม `ACCESS_TOKEN_EXPIRE_HOURS=8` (ปัจจุบันน้อยกว่านี้)
   - หรือเพิ่ม refresh token endpoint

3. **[HIGH] Clean orphaned Qdrant vector**
   - BUG-002: มี 7 vectors แทนที่จะเป็น 6
   - รัน script ลบ point ที่ไม่มีใน FaceTemplate table

4. **[MED] Face quality gate**
   - ไฟล์: `backend/app/api/enrollment.py`
   - ก่อน save: check `quality_score >= MIN_FACE_QUALITY`
   - ตอบ 422 พร้อม message ถ้าคุณภาพต่ำเกินไป

5. **[MED] Anti-spoofing**
   - ไฟล์: `backend/app/core/face_engine.py`
   - เพิ่ม MiniFASNet model
   - เรียกก่อน embedding extraction

---

## Context สำหรับ AI Session ถัดไป

เมื่อเริ่ม session ใหม่ให้อ่าน:
1. `doc/project_management/PROJECT_STATUS.md` — ภาพรวม
2. `doc/project_management/SPRINT_LOG.md` — สิ่งที่ทำล่าสุด (Sprint นี้)
3. `backend/app/api/websocket.py` — จุดที่ต้องแก้ถัดไป (attendance logging)
4. `backend/app/api/auth.py` — JWT fix

**Environment:**
- venv: `F:\programming\python\OmniSight\my_env`
- Backend start: `start-backend.bat`
- DB migration: `migrate.bat upgrade`
- Services: Docker Desktop → Qdrant (6333), Redis (6379), PostgreSQL (5432)
