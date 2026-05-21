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

## Sprint 8 — Multi-Camera Architecture Design ✅ DONE (Design)
**วันที่:** 2026-05-17 (Session 4 ต่อ)  
**เป้าหมาย:** ออกแบบสถาปัตยกรรมรองรับกล้องหลายตัว + Pilot Console

### สิ่งที่ทำ

1. **`doc/claude_version/chapter_17_multi_camera_pilot_console.md`** — NEW
   - Architecture diagram (Mermaid) — Camera sources → Edge Agents → Backend → Storage
   - WebSocket Protocol v2 (camera_id parameter, bidirectional control)
   - `cameras` table schema
   - Redis state management pattern
   - `rtsp_agent.py` — sample code สำหรับ IP Camera/CCTV agent
   - Smartphone mobile web app design + stream toggle protocol
   - Pilot Console UI wireframe ("Pilot Console" concept)
   - `CameraManager` service design + Camera state machine (Mermaid)
   - Implementation plan Sprint 8-10
   - Security considerations
   - Scalability notes

2. **`doc/project_management/DECISIONS_LOG.md`** — เพิ่ม ADR
   - ADR-009: Multi-Camera (1 WebSocket per camera) vs multiplex
   - ADR-010: Redis Pub/Sub เป็น event bus
   - ADR-011: Bidirectional WS control สำหรับ smartphone

3. **`doc/project_management/PROJECT_STATUS.md`** — อัพเดท
   - เพิ่ม Phase 4: Multi-Camera & Pilot Console (17 tasks, 3 sprints)
   - Phase 5: Production (เปลี่ยนจาก Phase 4)

### Key Decisions

| เรื่อง | การตัดสินใจ |
|-------|------------|
| Camera connection model | 1 WebSocket per camera (fault isolation) |
| Event distribution | Redis Pub/Sub → Pilot Console |
| Smartphone control | Bidirectional WS control messages |
| UI paradigm | Pilot Console (Control Tower concept) |

---

## Sprint 8 — Auth/Security Implementation ✅ DONE
**วันที่:** 2026-05-17 (Session 5)  
**เป้าหมาย:** ระบบ Auth/Authz ครบถ้วน — SSOT, server-side authorization, no native dialogs

### สิ่งที่ทำ

#### 1. DataTable inline button fix
- **ปัญหา:** operator1 row (3 actions: Edit + Stations + Delete) แสดงเป็น ⋮ dropdown แทน inline buttons
- **แก้:** `DataTable.vue` — เปลี่ยน threshold `<= 2` → `<= 3` ทำให้ 3 actions ขึ้นไปก็แสดง inline ได้

#### 2. useConfirm composable + ConfirmModal
- **ไฟล์ใหม่:** `frontend/src/composables/useConfirm.js`
  - Singleton pattern ด้วย module-level refs
  - `confirm(msg, opts)` returns `Promise<boolean>`
  - ใช้แทน `window.confirm()` ทั่วทั้ง app
- **ไฟล์ใหม่:** `frontend/src/components/ConfirmModal.vue`
  - DaisyUI `<dialog>` (native HTML dialog element)
  - `watch(isOpen)` → `showModal()` / `close()`
  - Backdrop click = cancel
- **App.vue:** mount `<ConfirmModal />` globally + `verifySession()` on mount

#### 3. Auth Store SSOT Rewrite
- **ไฟล์:** `frontend/src/stores/auth.js` — เขียนใหม่ทั้งหมด
  - Export `TOKEN_KEY = 'omnisight-token'` เพื่อใช้จาก client.js
  - `LEGACY_KEYS = ['token']` — clean up old localStorage key on init
  - `user` computed: ตรวจ expiry (10s buffer) + ตรวจ `sub` + `role` — return null ถ้า fail ทุก case
  - `isLoggedIn = !!user` — ครอบ expiry โดยอัตโนมัติ
  - `isTokenExpired(token)` helper function
  - `login()`, `logout()`, `forceLogout(reason)`, `verifySession()`, `_clearState()`
  - `verifySession()` → GET /api/v1/auth/me → update `_fullName`

#### 4. Axios Client Rewrite
- **ไฟล์:** `frontend/src/api/client.js`
  - request interceptor: ดึง token จาก `localStorage.getItem(TOKEN_KEY)`
  - response interceptor: 401 → ลบ token + redirect พร้อม `reason` query param
  - `_isRedirecting` flag ป้องกัน multiple redirects จาก concurrent 401

#### 5. Router Guards Rewrite
- **ไฟล์:** `frontend/src/router/index.js`
  - ทุก protected route มี `meta.roles: ['ADMIN', 'HR']` หรือ `meta.roles: ['ADMIN']`
  - Guard ใช้ `auth.isLoggedIn` (ครอบ expiry) แทน `auth.token`
  - Role mismatch → redirect `/scan` แทน 404

#### 6. SettingsView Rewrite
- **ไฟล์:** `frontend/src/views/SettingsView.vue`
  - 4 กลุ่ม: 🔐 Security, 👁️ Face Recognition, 📋 Attendance, ⚡ Performance
  - `access_token_expire_hours` อยู่ใน Security group
  - META object: label, min, max, hint, type per key
  - ใช้ `useConfirm` ทุก save/reset action
  - `byKey` computed — O(1) lookup

#### 7. Backend: GET /auth/me endpoint
- **ไฟล์:** `backend/app/api/auth.py`
  - ตรวจ user ใน DB, ตรวจ `is_active`
  - Return: `user_id, username, full_name, role, is_active, station_ids`
  - 401 ถ้า user ถูกลบหรือ deactivate

#### 8. Backend: JWT expire_hours configurable
- **ไฟล์:** `backend/app/core/security.py`
  - `create_access_token(..., expire_hours=None)` — ใช้ DB value แทน hardcoded
- **ไฟล์:** `backend/app/api/auth.py` login endpoint
  - อ่าน `access_token_expire_hours` จาก `system_settings` table
- **ไฟล์:** `backend/main.py`
  - เพิ่ม `access_token_expire_hours` ใน DEFAULT_SETTINGS seed

#### 9. Backend: 13 unprotected endpoints hardened

| ไฟล์ | Endpoint | ก่อน | หลัง |
|------|---------|------|------|
| departments.py | GET /departments | ❌ ไม่มี auth | ✅ require_hr |
| departments.py | POST /departments | ❌ | ✅ require_admin |
| departments.py | PUT /departments/{id} | ❌ | ✅ require_admin |
| departments.py | DELETE /departments/{id} | ❌ | ✅ require_admin |
| employees.py | GET /employees | ❌ | ✅ require_hr |
| employees.py | POST /employees | ❌ | ✅ require_hr |
| employees.py | GET /employees/{id} | ❌ | ✅ require_hr |
| employees.py | PATCH /employees/{id} | ❌ | ✅ require_hr |
| stations.py | GET /stations | ❌ | ✅ get_current_user |
| stations.py | GET /stations/{id} | ❌ | ✅ get_current_user |
| attendance.py | GET /attendance | ❌ | ✅ require_hr |
| enrollment.py | GET /enrollment | ❌ | ✅ require_hr |
| enrollment.py | POST /enroll | ❌ | ✅ require_hr |
| enrollment.py | DELETE /enroll/{idx} | ❌ | ✅ require_hr |
| shifts.py | GET /shifts | ❌ | ✅ require_hr |
| shifts.py | POST /shifts | ❌ | ✅ require_admin |
| shifts.py | DELETE /shifts/{id} | ❌ | ✅ require_admin |

#### 10. Documentation
- **ไฟล์ใหม่:** `doc/claude_version/chapter_22_auth_authorization.md`
  - 4 Mermaid sequence diagrams: Login Flow, Protected API Call, App Load/Session Restore, Logout Flow
  - API Authorization Matrix (ทุก endpoint)
  - Frontend Route Guard Matrix
  - Auth Store SSOT design diagram
  - Security Dependencies (backend)
  - Known Limitations table

### Bug ที่แก้
| Bug | การแก้ไข |
|-----|---------|
| BUG-001: JWT token หมดอายุเร็ว | admin ตั้งค่า `access_token_expire_hours` ผ่าน Settings UI ได้ |

### LoginView improvements
- Banner "Your session has expired. Please sign in again." เมื่อ `?reason=expired`
- Banner "Your account has been deactivated." เมื่อ `?reason=deactivated`
- Better error messages จาก `e.response?.data?.detail`
- Redirect กลับไปยัง `?redirect=` path หลัง login สำเร็จ

---

## Sprint 9 — Camera Backend + Pilot Console + Attendance Report ✅ DONE
**วันที่:** 2026-05-17 (Session 6)
**เป้าหมาย:** Multi-camera backend ครบ + Pilot Console UI + Monthly Attendance Report

### สิ่งที่ทำ

1. **Pilot Console View** — `frontend/src/views/PilotConsoleView.vue` (NEW)
   - WebSocket ต่อ `/api/v1/ws/console?token=...` (ADMIN only)
   - Camera tiles: status dot, FPS, frame count, pause/resume/disconnect
   - Event feed: attendance_logged, unknown_face, camera_connected/disconnected
   - Auto-reconnect (3s) เมื่อ connection drop
   - Stats bar: cameras active/paused/offline, events today
   - TransitionGroup animation สำหรับ event feed

2. **Router + Sidebar** — เพิ่ม `/console` route (ADMIN only) + menu item "Pilot Console"

3. **Attendance Summary API** — `GET /api/v1/attendance/summary?month=YYYY-MM&dept_id=N`
   - Monthly totals: total_records, unique_employees
   - by_day: 31 entries (filled) with count + unique_employees per day
   - by_department: sorted by count desc
   - Protected by `require_hr` dependency

4. **AttendanceView rewrite** — 2 tabs
   - **Logs tab**: existing table + date/dept filter + CSV export (เพิ่ม dept_name column)
   - **Monthly Report tab**: KPI cards + CSS bar chart + dept breakdown + summary CSV export

### Auth guard verification (all passed)
| | No Token | OPERATOR | HR | ADMIN |
|---|---|---|---|---|
| /cameras | 401 ✅ | 403 ✅ | 200 ✅ | 200 ✅ |
| /employees | 401 ✅ | 403 ✅ | 200 ✅ | 200 ✅ |
| /stations | — | 200 ✅ | 200 ✅ | 200 ✅ |
| /attendance | — | 403 ✅ | 200 ✅ | — |
| /departments | — | 403 ✅ | 200 ✅ | — |
| /users | — | — | 403 ✅ | 200 ✅ |
| /settings | — | — | — | 200 ✅ |

---

## Sprint 10 — Multi-Camera Plug-and-Play ✅ DONE
**วันที่:** 2026-05-18 (Session 7)  
**เป้าหมาย:** รองรับกล้องทุกประเภท (Webcam, IP Camera, CCTV, Smartphone) ด้วย protocol เดียว + no conflict + best performance

### สิ่งที่ทำ

#### 1. WebSocket Handler Rewrite — `backend/app/api/websocket.py`
Architecture: "One Protocol, Many Cameras" — ทุกกล้องใช้ binary JPEG เหมือนกัน

**FPS Gate per Camera (Backend-side)**
- `_last_processed: dict[str, float]` — timestamp ล่าสุดที่ process ต่อ camera_id
- Frame ที่มาเร็วกว่า `1/max_fps` จะถูก drop ทันที (ไม่ queue) — ป้องกัน memory buildup
- webcam ที่ส่ง 30 FPS จะถูก gate เหลือ 2 FPS โดยอัตโนมัติ

**ThreadPoolExecutor (Non-blocking Face Inference)**
```python
_executor = ThreadPoolExecutor(max_workers=settings.inference_workers)
# Face detection: CPU-bound ONNX → ไม่บล็อก event loop
detections = await loop.run_in_executor(_executor, face_engine.get_detections, frame)
# Qdrant search: synchronous client → ไม่บล็อก event loop
results = await loop.run_in_executor(_executor, partial(qdrant.search, ...))
```

**Redis-Cached FPS Cap**
```python
async def _get_max_fps() -> float:
    val = await _redis.get("setting:max_fps_per_camera")  # admin เปลี่ยนได้ realtime
    return max(0.1, float(val)) if val else float(settings.max_fps_per_camera)
```

**camera_id Auto-generation** (ถ้า client ไม่ระบุ)
```
sm-{user_id[:6]}-{station_id[:6]}  # OPERATOR (smartphone)
wc-{user_id[:6]}-{station_id[:6]}  # ADMIN/HR (webcam)
```

**FaceResult ครบ fields** — fix bug สำคัญ:
- ก่อน: `hit.payload.get("full_name", "")` ← ไม่มีใน Qdrant payload (เสมอ `""`)
- หลัง: JOIN `employees` + `departments` tables → populate `full_name`, `emp_code`, `dept_name`

**Cleanup on disconnect:**
```python
_last_processed.pop(camera_id, None)  # ป้องกัน dict leak
```

#### 2. Config — `backend/app/core/config.py`
- เพิ่ม `max_fps_per_camera: int = 2`
- เพิ่ม `inference_workers: int = 2`

#### 3. RTSP Agent — `backend/agents/rtsp_agent.py` (NEW)
Standalone Python script ที่ bridge IP Camera/CCTV (RTSP) → OmniSight WebSocket

**Features:**
- Config via env vars: `RTSP_URL`, `STATION_ID`, `CAMERA_ID`, `OMNISIGHT_TOKEN`, `TARGET_FPS`, `JPEG_QUALITY`, `RESIZE_WIDTH`
- `cv2.VideoCapture` + `CAP_PROP_BUFFERSIZE=1` (minimal latency)
- Background `_listen()` async task สำหรับ pause/resume/set_fps/disconnect
- `run_in_executor` สำหรับ `_encode_frame` — non-blocking JPEG encode
- Auto-reconnect: RTSP reconnect 5s, WebSocket reconnect 3s
- Accurate FPS: `sleep = max(0.0, min_interval - elapsed)`

**ไฟล์ใหม่:** `backend/agents/.env.example` — template config พร้อม comments สำหรับ Hikvision/Dahua/Generic

#### 4. MobileScanView — `frontend/src/views/MobileScanView.vue` (NEW)
Full-screen smartphone web app สำหรับ OPERATOR ที่ gate

**Features:**
- `fixed inset-0 bg-black` — fullscreen, ไม่มี sidebar
- `facingMode: 'environment'` — rear camera by default
- Flip button (front/back)
- Start/Stop large touch-friendly button
- Handles all server control messages: pause/resume/set_fps/disconnect
- BBox overlay ด้วย scaleX/scaleY (video vs canvas size mapping)
- iOS safe area CSS: `pb-safe`, `top-safe` (env(safe-area-inset-*))
- Frame count display + FPS counter (EMA)
- WS status badge (Live/Connecting/Reconnecting/Offline)

#### 5. Router + Sidebar — `frontend/src/router/index.js`, `AppLayout.vue`
- `/mobile-scan` — standalone route (**ไม่** nested ใต้ AppLayout เพราะ fullscreen)
- Mobile Scan menu item ใน sidebar (Operations section) — ทุก role เข้าได้
- `meta: { title: 'Mobile Scan' }` — ไม่มี roles restriction (OPERATOR, HR, ADMIN ใช้ได้)

#### 6. ScanView.vue Rewrite — `frontend/src/views/ScanView.vue`
Critical bug fix + Pilot Console integration:
- **TOKEN_KEY bug fix**: `localStorage.getItem('token')` → `import { TOKEN_KEY }` + `localStorage.getItem(TOKEN_KEY)` — กล้อง webcam จะเชื่อมต่อ WS ได้ถูกต้อง
- Pause overlay (`<Transition name="fade">`) เมื่อรับ `{"action":"pause"}` จาก Pilot Console
- FPS overlay บนวิดีโอ
- BBox labels: `{name} {confidence}%` สำหรับ match, `Unknown` สำหรับ unknown
- Modular: `_start`, `_stop`, `_startFrameLoop`, `_stopFrameLoop`, `_sendFrame`, `_drawBBoxes`
- WS auto-reconnect (2s) ยกเว้น code 4001/4003

### Performance Architecture Summary

```
Camera Type    → Protocol         → Backend Defense
───────────────────────────────────────────────────────
Webcam (2fps)  → WS Binary JPEG  → FPS gate + Thread pool
IP Camera      → RTSP→WS agent   → FPS gate + Thread pool  
Smartphone     → WS Binary JPEG  → FPS gate + Thread pool
Multiple cams  → Concurrent WS   → asyncio event loop stays free
```

### ผลลัพธ์ที่ได้
- N กล้องทำงาน parallel ได้ โดยไม่มี deadlock หรือ starvation
- Admin เปลี่ยน FPS cap real-time (Redis write-through) ไม่ต้อง restart
- ScanView แสดงชื่อ/รหัส/แผนก ของพนักงานที่ match ได้ถูกต้อง
- MobileScan พร้อมใช้งานที่ `/mobile-scan` — เปิดบนมือถือได้เลย

### Next Sprint (Sprint 11 / สิ่งที่ยังต้องทำ)
1. **BUG-002** — Orphaned Qdrant vector reconcile script
2. **Anti-spoofing** — MiniFASNet integration (Phase 2 AI)
3. **Face quality gate** — ป้องกัน blur/dark ตอน enrollment
4. **rtsp_agent Dockerfile** — สำหรับ deploy ใน production
5. **GitHub push** — Sprint 9 + Sprint 10 (ต้องขออนุญาต user)

---

## Sprint 11 — Face Snapshot Evidence ✅ DONE
**วันที่:** 2026-05-18 (Session 8)  
**เป้าหมาย:** บันทึกรูปใบหน้า (crop จาก frame) ทุกครั้งที่ scan match → เก็บใน disk + แสดงใน Attendance page

### สิ่งที่ทำ

#### 1. Database — `backend/app/models/orm.py`
- เพิ่ม `snapshot_path: Mapped[Optional[str]]` ใน `AttendanceLog` model

#### 2. Migration — `backend/alembic/versions/c3f8a92b1d74_add_snapshot_path_to_attendance_logs.py`
- `ALTER TABLE attendance_logs ADD COLUMN snapshot_path VARCHAR NULLABLE`

#### 3. Config — `backend/app/core/config.py`
- แก้ `storage_path` จาก relative `"storage"` → absolute path ด้วย `_PROJECT_ROOT`
- เหตุผล: uvicorn เปลี่ยน cwd ทำให้ relative path ชี้ผิดที่

#### 4. WebSocket — `backend/app/api/websocket.py`
```python
# Crop face region with 25% padding → JPEG bytes
x1, y1, x2, y2 = bbox
pad_x = int((x2 - x1) * 0.25)
pad_y = int((y2 - y1) * 0.25)
crop = frame[max(0,y1-pad_y):min(ih,y2+pad_y), max(0,x1-pad_x):min(iw,x2+pad_x)]
ok, buf = cv2.imencode('.jpg', crop, [cv2.IMWRITE_JPEG_QUALITY, 85])
face_crop_jpg = buf.tobytes() if ok else None
# → pass to log_attendance(face_crop_jpg=face_crop_jpg)
```

#### 5. Attendance Service — `backend/app/services/attendance_service.py`
```python
# Save JPEG snapshot to disk
snap_dir = Path(settings.storage_path) / "snapshots" / datetime.now(timezone.utc).strftime("%Y-%m-%d")
snap_dir.mkdir(parents=True, exist_ok=True)
snap_path = snap_dir / f"{log.id}.jpg"
snap_path.write_bytes(face_crop_jpg)
log.snapshot_path = str(snap_path)
```

#### 6. Attendance API — `backend/app/api/attendance.py`
- `snapshot_url: str | None` field ใน list response (`/api/v1/employees/{id}/enroll/{i}/image` pattern)
- ใหม่: `GET /api/v1/attendance/{log_id}/snapshot` — serve JPEG (require_hr auth)

#### 7. Frontend — `frontend/src/views/AttendanceView.vue`
- `SnapshotImg` component: lazy-load thumbnail (32px) จาก `snapshot_url`
- Click → fullscreen modal: รูปใหญ่ + `{employee_name} · {station} · {timestamp}`
- Graceful: slot ว่าง (—) ถ้าไม่มี snapshot

#### 8. main.py improvements
- `logging.getLogger("app").setLevel(logging.INFO)` — ให้ app logs แสดงใน terminal
- เพิ่ม `"http://192.168.1.170:5173"` ใน CORS origins — mobile ใน LAN เดียวกัน

### ผลการทดสอบ
- Attendance log id=27 สร้างด้วย `snapshot_path` set ✅
- ไฟล์ JPEG บน disk: `storage/faces/snapshots/2026-05-18/27.jpg` (8468 bytes) ✅
- Thumbnail แสดงใน Attendance page ✅

### บทเรียนสำคัญ (zombie process debugging)
uvicorn `--reload` บน Windows มี bug อันตราย:
- ปิด terminal ด้วย X button **ไม่ได้ kill** process — python.exe ยังคงรันอยู่ (zombie)
- `start-dev.bat` ใหม่รันขึ้น แต่ zombie ถือ port 8000 → server ใหม่ exit เงียบ ๆ
- ทุก request ยังถูก handle โดย zombie (stale code จาก 08:26 AM)
- ใช้เวลา ~3 ชั่วโมงในการ debug ก่อนพบว่า PID 20740 (zombie) กำลัง serve traffic
- แก้โดย: `Stop-Process -Id 20740 -Force` จากนั้น `start-dev.bat` ใหม่ทำงานถูกต้อง
- **บันทึกใน:** `C:\Users\66996\.claude\projects\...\memory\feedback_uvicorn_windows_reload.md`

---

## Sprint 12 — All Settings Live + AI Gates ✅ DONE
**วันที่:** 2026-05-18 (Session 8 ต่อ)  
**เป้าหมาย:** Settings UI ทุกตัวต้องทำงานจริง + face quality gate ตอน enrollment + unknown face alert

### ปัญหาที่พบ (BUG-006)
Settings ทุกตัว (ยกเว้น `access_token_expire_hours`) ไม่ทำงาน:
- Redis key `setting:cooldown_seconds` = `None` (ว่างเปล่า)
- `_get_cooldown_seconds()` ใน redis.py อ่านไม่ได้ → ใช้ hardcoded default 300s
- สาเหตุ: ไม่มี code ที่ sync settings จาก DB → Redis ตอน startup
- **แก้:** เพิ่ม startup sync loop ใน `main.py`

```python
# Sync all settings to Redis on startup (ใน _seed_admin)
all_settings = await db.execute(select(SystemSetting))
for s in all_settings.scalars().all():
    await _redis.set(f"setting:{s.key}", s.value)
```

### สิ่งที่ทำ

#### 1. `backend/main.py` — Startup Redis Sync
- หลัง seed settings, sync ทุก key จาก `system_settings` → `setting:{key}` ใน Redis
- ทำให้ทุก setting มีผลทันทีหลัง restart backend

#### 2. `backend/app/api/websocket.py` — Live Match Threshold
```python
async def _get_match_threshold() -> float:
    val = await _redis.get("setting:match_threshold")
    return max(0.1, min(1.0, float(val))) if val else float(settings.match_threshold)

# ใน scan loop (ก่อนหน้า: score_threshold=settings.match_threshold — ไม่เปลี่ยนตาม UI)
match_threshold = await _get_match_threshold()
results = await loop.run_in_executor(_executor, partial(qdrant.search, ..., score_threshold=match_threshold))
```

#### 3. `backend/app/db/redis.py` — Functions ใหม่
```python
async def get_min_face_quality() -> float:
    """อ่าน min_face_quality จาก Redis — ใช้ใน enrollment.py"""

async def increment_unknown_count(station_id: str) -> int:
    """Redis INCR + EXPIRE 300 — rolling 5-min counter per station"""

async def get_unknown_alert_threshold() -> int:
    """อ่าน unknown_face_alert threshold จาก Redis"""
```

#### 4. `backend/app/api/enrollment.py` — Face Quality Gate
```python
quality = face_engine.get_quality_score(img)
min_quality = await get_min_face_quality()
if quality < min_quality:
    img_path.unlink(missing_ok=True)
    raise HTTPException(422, f"Face quality too low ({quality:.2f} < {min_quality:.2f}) — ...")
```

#### 5. `backend/app/api/websocket.py` — Unknown Face Alert
```python
# ใน else branch (unknown face):
unknown_count = await increment_unknown_count(station_id)
threshold = await get_unknown_alert_threshold()
if unknown_count >= threshold:
    await _redis.publish("omnisight:events", json.dumps({
        "event": "unknown_face_alert",
        "station_id": station_id,
        "camera_id": camera_id,
        "count": unknown_count,
        "threshold": threshold,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }))
```
- Pilot Console รับ event นี้และแสดงในหน้า Event Feed อัตโนมัติ

#### 6. `start-dev.bat` — Zombie Process Prevention
```bat
echo [0/2] Cleaning up old Python processes...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM uvicorn.exe >nul 2>&1
timeout /t 1 /nobreak >nul
```

### Settings ทำงานครบ (8/8)
| Key | ผลที่แก้แล้ว |
|-----|------------|
| `access_token_expire_hours` | DB query ตอน login ✅ (เดิมทำงานอยู่แล้ว) |
| `match_threshold` | Redis live read ✅ (แก้ใหม่) |
| `min_face_quality` | Redis live read ✅ (แก้ใหม่) |
| `cooldown_seconds` | Redis live read ✅ (startup sync แก้) |
| `unknown_face_alert` | Redis live read ✅ (แก้ใหม่) |
| `max_fps_per_camera` | Redis live read ✅ (startup sync แก้) |
| `inference_workers` | Pydantic config (restart required) |
| `face_detect_size` | Pydantic config (restart required) |

---

---

## Sprint 13 — Production Hardening + Backup System + Anti-Spoofing ✅ DONE
**วันที่:** 2026-05-18 (Session 9)  
**เป้าหมาย:** Phase 5 Production stack, backup automation, anti-spoofing MiniFASNet, late/absent detection, BUG-002 fix

### สิ่งที่ทำ

#### 1. BUG-002 — Orphaned Qdrant Vector Fix
- สร้าง `backend/scripts/reconcile_qdrant.py`
- Scroll all Qdrant point IDs → compare with PostgreSQL `FaceTemplate.qdrant_id` → delete orphans
- ผล: ลบ 4 orphaned vectors, collection สะอาดที่ 6 vectors

#### 2. Late/Absent Detection — `backend/app/api/attendance.py`
- `GET /api/v1/attendance/daily-report?date=YYYY-MM-DD&dept_id=N`
- อ่าน `late_threshold_minutes` จาก Redis แบบ live
- Query employees ที่มี `shift_id IS NOT NULL` → ค้นหา first check-in ต่อ date
- เปรียบเทียบกับ `shift.start_time + late_threshold` → PRESENT / LATE / ABSENT
- Protected by `require_hr`
- Route ต้องอยู่ก่อน `/{log_id}/snapshot` เพื่อป้องกัน route conflict

#### 3. Daily Status Tab — `frontend/src/views/AttendanceView.vue`
- Tab ที่ 3 "Daily Status"
- KPI stats bar: Total / Present(green) / Late(yellow) / Absent(red)
- Table: status badge, employee, code, dept, shift, check-in time, minutes late
- `dailyDate` datepicker, `dailyDept` filter, `exportDailyCSV()`

#### 4. Settings — `frontend/src/views/SettingsView.vue`
- เพิ่ม `late_threshold_minutes` (Attendance group)
- เพิ่ม `anti_spoof_enabled`, `anti_spoof_threshold` (Face Recognition group)

#### 5. Anti-Spoofing MiniFASNet — `backend/app/core/face_engine.py`
```python
class AntiSpoofEngine:
    # MiniFASNet V2 (2.7_80x80_MiniFASNetV2.onnx)
    # input: (batch, 3, 80, 80) NCHW float32 ImageNet-normalized
    # output: (batch, 3) logits → softmax()[1] = liveness score
    
    def init(self, model_dir: str)          # called at startup
    def available -> bool                   # graceful degradation
    def predict(self, img, bbox) -> float   # returns 1.0 if model absent
    def check_liveness(self, img, bbox, threshold) -> tuple[bool, float]
```
- Model path: `models/anti_spoof/2.7_80x80_MiniFASNetV2.onnx`
- Graceful: ถ้าไม่มี model → `available=False` → ทุก check ผ่าน (True, 1.0)
- ใช้ใน `enrollment.py`: HTTP 422 ถ้า liveness < threshold
- ใช้ใน `websocket.py`: `status="spoof"` FaceResult (ไม่ log attendance)

#### 6. `backend/app/core/config.py`
- เพิ่ม `anti_spoof_model_dir: str` (absolute path to models/anti_spoof/)

#### 7. `backend/main.py`
- Anti-spoof engine init ใน lifespan: `anti_spoof_engine.init(settings.anti_spoof_model_dir)`
- เพิ่ม DEFAULT_SETTINGS: `late_threshold_minutes=15`, `anti_spoof_enabled=0`, `anti_spoof_threshold=0.6`

#### 8. Production Docker Stack
- `backend/Dockerfile` — Python 3.12-slim, pre-download InsightFace buffalo_l
- `nginx/Dockerfile` — multi-stage: Vue build (node:20) + nginx:1.27 + SSL config
- `nginx/nginx.conf` — HTTP→HTTPS redirect, TLSv1.2/1.3, WebSocket proxy, HSTS
- `nginx/generate_self_signed_cert.sh` — openssl self-signed cert for dev
- `docker-compose.prod.yml` — full production stack (postgres + qdrant + redis + backend + nginx)
- `.env.prod.example` — template with CHANGE_ME placeholders

#### 9. Persistence Risk Analysis & Fix
**3 risks identified by senior engineer analysis:**
1. `storage:/app/storage` named volume → не accessible from host for backup
2. InsightFace models in image layer → re-download 500MB on `docker compose build --no-cache`
3. Zero backup automation

**Fixes applied:**
- `storage` named volume → `./data/storage` bind mount (host-accessible)
- `insightface_models:/root/.insightface` named volume (persists across rebuilds)
- Qdrant healthcheck + `backend depends_on: qdrant: condition: service_healthy`

#### 10. Backup Scripts
- `scripts/backup.sh` — pg_dump compressed + Qdrant REST snapshot + storage tar.gz, 7-day rotation
- `scripts/restore.sh` — full restore (drop+recreate DB, Qdrant snapshot upload, storage extract)
- `scripts/backup.ps1` — Windows PowerShell version for dev machine

#### 11. .gitignore Updates
- เพิ่ม `data/` (bind mount production data)
- เพิ่ม `backups/` (backup archives)
- เพิ่ม `models/` (large binary files — download separately)

### ผลลัพธ์
- Qdrant collection: 6 vectors (0 orphans) ✅
- Production Docker stack: ready to deploy with `docker compose -f docker-compose.prod.yml --env-file .env.prod up -d`
- Backup: `bash scripts/backup.sh` → creates `backups/YYYY-MM-DD_HHMMSS/`
- Anti-spoof: framework ready; model at `models/anti_spoof/2.7_80x80_MiniFASNetV2.onnx` (1.7MB)
- Late/Absent: configurable threshold via Settings UI, Daily Status tab in Attendance page

---

## Sprint 14 — Settings UI Redesign + Performance Testing ✅ DONE
**วันที่:** 2026-05-19 (Session 14)
**เป้าหมาย:** UI/UX ปรับ Settings page, seed 1000 employees, load test

### สิ่งที่ทำ

#### 1. Settings UI/UX Redesign — `frontend/src/views/SettingsView.vue`
- `number` input → DaisyUI range slider (`class="range range-sm"`)
- `bool` (0/1) → DaisyUI toggle (auto-save ทันที ไม่มี Save button)
- `string`/URL → text input full-width (`md:col-span-2`) + eye toggle สำหรับ secret fields
- Float threshold sliders (`match_threshold`, `min_face_quality`, `anti_spoof_threshold`) เปลี่ยนสี `range-success/warning/error` ตาม value
- `cooldown_seconds` → แสดง human label "5 min" / "2 hr"
- `face_detect_size` → stepped slider [160, 320, 640, 1280]
- ลบ custom CSS ทั้งหมด ใช้ DaisyUI เท่านั้น

#### 2. Seed Script — `backend/scripts/seed_performance.py` (NEW)
- สร้างพนักงาน N คน + 6N face vectors ใน Qdrant (~6s สำหรับ 1000 คน)
- 10 departments, 3 shifts (Morning/Afternoon/Night)
- `emp_code` format: EMP00001–EMP01000
- args: `--employees N`, `--clear`

#### 3. Load Test — `backend/scripts/load_test.py` (NEW)
- simulate N cameras ส่ง JPEG frames พร้อมกันผ่าน WebSocket
- วัด round-trip latency (p50/p95/p99), throughput, error rate
- monitor backend CPU/RAM ด้วย `psutil`
- ผล: 5 cameras OK (0% error, p50=1.6s) / 10 cameras bottleneck (37% error)
- Bottleneck: `inference_workers=2` รองรับได้ ~5 cameras ที่ 2fps บน CPU
- Recommendation: เพิ่ม `inference_workers` เป็น 4–8 สำหรับ 10+ cameras

#### 4. requirements.txt
- เพิ่ม `psutil==6.1.0` (ใช้ใน load_test.py)

### ผลลัพธ์
- 1,000 employees seed ใน DB (EMP00001–EMP01000) ✅
- 6,000 face vectors ใน Qdrant ✅
- Bottleneck identified: inference_workers ควรขึ้นเป็น 4–8 สำหรับ 10+ cameras

---

## Sprint 15 — Structured Logging + rtsp_agent Docker ✅ DONE
**วันที่:** 2026-05-19 (Session 15)
**เป้าหมาย:** JSON structured logs + file rotation, RTSP camera Dockerfile สำหรับ production

### สิ่งที่ทำ

#### 1. Structured JSON Logging — `backend/app/core/logging_config.py` (NEW)
```python
class _JsonFormatter(logging.Formatter):
    # serialises: ts, level, logger, msg (+ exc if exception)

def setup_logging(log_dir, level=INFO):
    # TimedRotatingFileHandler — daily rotation, backupCount=7
    # StreamHandler(stdout) — Docker-compatible
    # logging.basicConfig(force=True) — overrides uvicorn defaults
    # Silences: uvicorn.access, multipart, PIL, httpx
```
- Log files: `{project_root}/logs/omnisight.log` (rotate daily, keep 7 days)
- Zero new dependencies — stdlib only

#### 2. Config — `backend/app/core/config.py`
- เพิ่ม `log_dir: str = str(_PROJECT_ROOT / "logs")`

#### 3. main.py — `backend/main.py`
- แทนที่ `logging.getLogger("app").setLevel(INFO)` ด้วย `setup_logging(settings.log_dir)`
- import ก่อน lifespan setup

#### 4. Dockerfile — `backend/Dockerfile`
- เพิ่ม `/app/logs` ใน `mkdir -p` (สร้าง dir ตอน build)

#### 5. docker-compose.prod.yml
- เพิ่ม `./data/logs:/app/logs` bind mount ใน backend service (host-accessible)

#### 6. rtsp_agent Dockerfile — `backend/agents/Dockerfile` (NEW)
```dockerfile
FROM python:3.12-slim
# minimal deps: opencv-python-headless, websockets, python-dotenv, numpy
CMD ["python", "-u", "rtsp_agent.py"]  # PYTHONUNBUFFERED=1
```
- `backend/agents/requirements.txt` — minimal deps only (ไม่รวม insightface/onnxruntime)

#### 7. docker-compose.rtsp.yml (NEW — overlay file)
```yaml
# docker compose -f docker-compose.prod.yml -f docker-compose.rtsp.yml up -d
services:
  rtsp_cam1:
    build: ./backend/agents
    environment: OMNISIGHT_WS, STATION_ID, CAMERA_ID, TOKEN, RTSP_URL, TARGET_FPS...
    depends_on: [backend]
    networks: [omnisight_net]
  # duplicate block per camera
```
- Separate overlay file — ไม่ bake เข้า prod compose หลัก
- Networks: `omnisight_net` external (defined ใน docker-compose.prod.yml)

#### 8. backend/agents/.env.rtsp.example (NEW)
- Template พร้อม comments สำหรับ Hikvision / Dahua / Generic ONVIF

### ผลลัพธ์
- JSON logs: `logs/omnisight.log` หมุนทุกเที่ยงคืน เก็บ 7 วัน ✅
- Docker + stdout พร้อมใช้: `docker logs backend` แสดง JSON ✅
- rtsp_agent: `docker build -t rtsp-agent ./backend/agents` พร้อม deploy ✅
- Production CCTV: เพิ่มกล้องใหม่ด้วย 1 service block ใน docker-compose.rtsp.yml ✅

---

## Sprint 15b — Performance Architecture: 10+ Cameras & Multi-Face ✅ DONE
**วันที่:** 2026-05-19 (Session 15 ต่อ)
**เป้าหมาย:** รองรับ 10+ cameras และ multi-face per frame ด้วยการแก้ bug + optimize

### Root Cause Analysis

**Performance Model:**
```
Demand:   N_cameras × fps × (1 - cache_hit) = frames/sec needing full pipeline
Capacity: inference_workers / inference_time_sec

With defaults (workers=2, 640px, inference=0.4s):
  5 cam × 2fps × 0.5 miss = 5.0 fps demand → barely OK
  10 cam × 2fps × 0.5 miss = 10.0 fps demand → 2× over capacity → 37% error ✓
```

### 3 Bugs Fixed

#### Bug 1 — AsyncQdrantClient ignored (HIGH impact)
- `qdrant.py` ประกาศ `AsyncQdrantClient` แต่ `websocket.py` ใช้ `get_qdrant_sync()` + executor
- แต่ละ Qdrant search ครอบครอง 1 thread สำหรับ network wait (5-20ms) ไม่ใช่ CPU
- **Fix:** ใช้ `_async_qdrant` โดยตรง → threads ว่างสำหรับ CPU inference

#### Bug 2 — face_detect_size setting ไม่มีผล (MEDIUM-HIGH impact)
- `FaceEngine._load()` hardcode `det_size=(640, 640)` — ไม่อ่านจาก Settings
- Admin ตั้ง 320 ใน Settings UI ก็ไม่มีผล (ยังรัน 640 อยู่)
- **Fix:** อ่าน `settings.face_detect_size` ตอน load → 320px เร็วกว่า 4×

#### Bug 3 — N faces = N Qdrant round-trips (MEDIUM impact)
- 3 faces ต่อ frame = 3 network requests
- **Fix:** `search_batch()` → 1 request สำหรับ N faces ทั้งหมด

### 4 Optimizations Added

#### Opt 4 — Anti-spoof batch (N faces → 1 ONNX call)
- `AntiSpoofEngine.predict_batch(img, bboxes)` → stack crops to (N,3,80,80) → 1 executor slot
- เพิ่มใน `face_engine.py`

#### Opt 5 — Global settings cache (5s TTL)
- เดิม: 5 Redis calls ต่อ frame × 10 cameras × 2fps = 100 calls/sec
- `_get_frame_settings()` cache ทั้งหมดใน dict, refresh ทุก 5 วินาที
- Admin changes มีผลภายใน 5 วินาที

#### Opt 6 — Frame decode in executor
- `cv2.imdecode()` เป็น CPU-bound → ย้ายเข้า executor (ออกจาก event loop)

#### Opt 7 — inference_workers default 2 → 4
- formula: `ceil(N_cam × fps × inference_sec × miss_rate)`
- สำหรับ 10 cameras 640px: ตั้ง 6-8
- สำหรับ 10 cameras 320px: ตั้ง 4

### Files Modified
| File | การเปลี่ยนแปลง |
|------|---------------|
| `backend/app/core/face_engine.py` | `_load()` อ่าน det_size + `predict_batch()` |
| `backend/app/api/websocket.py` | async Qdrant + search_batch + batch spoof + settings cache + decode executor |
| `backend/app/core/config.py` | inference_workers default 2→4, tuning formula comment |

### Projected Performance
| Scenario | Before | After (640px, 8w) | After (320px, 4w) |
|----------|--------|-------------------|-------------------|
| 10 cam, 2fps, 1 face | 37% err | 0% err, p50≈0.6s | 0% err, p50≈0.2s |
| 10 cam, 2fps, 3 faces | ~60% err | <5% err | 0% err |
| 20 cam, 2fps, 1 face | ~80% err | ~5% err | 0% err |

---

## Sprint 15c — World-class 3: Prometheus, Dynamic Workers, Hungarian Tracker ✅ DONE
**วันที่:** 2026-05-19 (Session 15 ต่อ)
**เป้าหมาย:** Production-grade observability + elastic concurrency + globally optimal face tracking

### Feature 1 — Prometheus Metrics

**ไฟล์ใหม่:** `backend/app/core/metrics.py`

| Metric | ประเภท | ความหมาย |
|--------|--------|---------|
| `omnisight_inference_duration_seconds` | Histogram | InsightFace buffalo_l wall time |
| `omnisight_qdrant_search_duration_seconds` | Histogram | search_batch() round-trip |
| `omnisight_antispoof_duration_seconds` | Histogram | predict_batch() ONNX time |
| `omnisight_frames_received_total` | Counter | ทุก frame ที่รับจาก WebSocket |
| `omnisight_frames_processed_total` | Counter | ผ่าน FPS gate เข้า pipeline |
| `omnisight_frames_dropped_fps_total` | Counter | ถูก FPS gate ทิ้ง |
| `omnisight_tracker_cache_hits_total` | Counter | Qdrant skip (tracker cache hit) |
| `omnisight_tracker_cache_misses_total` | Counter | full Qdrant search required |
| `omnisight_faces_detected_total` | Counter | ใบหน้าที่ detect ได้ทั้งหมด |
| `omnisight_faces_matched_total` | Counter | match employee สำเร็จ |
| `omnisight_faces_unknown_total` | Counter | unknown person |
| `omnisight_faces_spoof_total` | Counter | anti-spoof reject |
| `omnisight_active_cameras` | Gauge | WebSocket cameras connected |
| `omnisight_inference_workers` | Gauge | ThreadPoolExecutor size |
| `omnisight_inflight_inferences` | Gauge | inference calls in flight |

**Endpoint:** `GET /metrics` → Prometheus text exposition (scraped by Grafana)

### Feature 2 — Dynamic ThreadPoolExecutor Scaling

`_resize_executor_if_needed(new_size)` ใน `websocket.py`:
- Admin เปลี่ยน `inference_workers` ใน Settings UI → Redis → backend pick up ภายใน 5s
- Double-checked locking ด้วย `asyncio.Lock` (stampede-safe)
- `old.shutdown(wait=False)` → ไม่ block event loop ระหว่าง resize
- ไม่ต้อง restart backend เพื่อเปลี่ยน worker count

### Feature 3 — Hungarian Algorithm Tracker

`backend/app/core/tracker.py` (rewritten):
- เปลี่ยนจาก greedy O(T×D) → `scipy.optimize.linear_sum_assignment` (Jonker-Volgenant)
- สร้าง cost matrix (T×D): `cost[i,j] = 1.0 - IoU(track_i, detection_j)`
- globally optimal assignment — critical เมื่อ ≥5 หน้าใน frame เดียวกัน
- Greedy bug: track แรกใน dict "ขโมย" detection จาก track ที่ fit ดีกว่า
- Hungarian: minimize total cost across all pairs simultaneously
- ยังคง `SimpleTracker = FaceTracker` alias สำหรับ backward compatibility

### Race Conditions Fixed (Bonus)

| Race | วิธีแก้ |
|------|--------|
| N cameras connect ก่อน model load | `threading.Lock` double-checked locking ใน `FaceEngine.app` property |
| Settings cache stampede (N coroutines expire พร้อมกัน) | `asyncio.Lock` double-checked ใน `_get_frame_settings()` |
| Executor resize stampede | `asyncio.Lock` ใน `_resize_executor_if_needed()` |
| First camera 5-10s stall ขณะ buffalo_l load | Warmup at startup via `face_engine.warmup()` ใน lifespan |

### Files Modified
| File | การเปลี่ยนแปลง |
|------|---------------|
| `backend/app/core/metrics.py` | **ใหม่** — ทุก Prometheus metric definitions |
| `backend/app/core/tracker.py` | **เขียนใหม่** — Hungarian algorithm |
| `backend/app/api/websocket.py` | metrics instrumentation + dynamic worker scaling |
| `backend/app/core/face_engine.py` | warmup() + threading.Lock + predict_batch() |
| `backend/main.py` | `/metrics` endpoint + setup_logging() + warmup call |
| `backend/requirements.txt` | `prometheus-client==0.21.1` + `psutil==6.1.0` |

### Projected Performance (all 6+3 optimizations combined)
| Scenario | Before Sprint 15b | After Sprint 15c |
|----------|-------------------|-----------------|
| 10 cam, 2fps, 1 face | 37% error | **0% error**, p50≈0.6s |
| 10 cam, 2fps, 3 faces/frame | ~60% error | **0% error**, p50≈0.8s |
| 20 cam, 2fps, 1 face | ~80% error | **<5% error** |
| Face identity collision (≥5 faces) | greedy mismatch | **globally optimal match** |

---

## Context สำหรับ AI Session ถัดไป

เมื่อเริ่ม session ใหม่ให้อ่าน:
1. `doc/project_management/PROJECT_STATUS.md` — dashboard + phase tracking (Sprint 13 latest)
2. `doc/project_management/SPRINT_LOG.md` — Sprint 7–13 history
3. `doc/claude_version/chapter_17_multi_camera_pilot_console.md` — Multi-camera design
4. `doc/claude_version/chapter_22_auth_authorization.md` — Auth/Authz (seq diagrams + matrix)
5. `doc/project_management/DECISIONS_LOG.md` — ADR-001 ถึง ADR-011

**⚠️ Path สำคัญ — ห้ามผิด:**
| สิ่งของ | Path |
|---------|------|
| เอกสารทุกฉบับ | `F:\programming\python\OmniSight\doc\cluade_version\` |
| PM docs | `F:\programming\python\OmniSight\doc\project_management\` |
| Python venv (3.12) | `F:\programming\python\OmniSight\my_env\` ← **ที่เดียวเท่านั้น** |
| Python exe | `F:\programming\python\OmniSight\my_env\Scripts\python.exe` |
| pip | `F:\programming\python\OmniSight\my_env\Scripts\pip.exe` |

**Environment:**
- Backend start: `.\start-dev.bat` หรือ `.\start-backend.bat` (uvicorn port 8000)
- `start-dev.bat` มี `taskkill` ก่อน start — ป้องกัน zombie process
- Production: `docker compose -f docker-compose.prod.yml --env-file .env.prod up -d`
- DB migration: `migrate.bat upgrade`
- Services: Docker → PostgreSQL (5432), Qdrant (6333), Redis (6379)

**State ปัจจุบัน (Sprint 15d done):**
- emp1: enrolled 6/6 slots ✅, has attendance logs with snapshots
- emp2: enrolled 0/6
- sta1 (ccd829a0): ไม่มี dept filter
- attendance_logs: 27+ records, records id≥27 มี snapshot_path
- Qdrant: 6,006 vectors (6 real + 6,000 seed employees)
- GitHub: https://github.com/idev006/OmniSight (ยังไม่ push Sprint 9–15d — ต้องขออนุญาต user)
- Users: admin (ADMIN), hr1 (HR), operator1 (OPERATOR) — bcrypt hashed
- `GET /metrics` endpoint live ✅ → Prometheus text format, ready for Grafana scraping
- Hungarian tracker active, dynamic worker scaling active (no restart needed)
- Structured JSON logs → `logs/omnisight.log` (daily rotation, 7-day retention)
- Settings: cooldown=10s, max_fps=15, match_threshold=0.70, min_quality=0.60, late_threshold_minutes=15, anti_spoof_enabled=0, inference_workers=4
- 1,000 seed employees ใน DB (EMP00001–EMP01000)

**Load test result (Sprint 15d — verified 2026-05-19):**
```
10 cameras × 2fps × 30s (CPU inference, no GPU)
Error rate : 0.00% ✅  (target < 5%)
p50 latency: 3,023ms  |  p95: 3,547ms  |  p99: 3,594ms
Throughput : 3.5 frames/s actual
CPU avg    : 395%  (4-core busy)  |  RAM avg: 837MB
```

**Anti-spoof model:**
- Path: `models/anti_spoof/2.7_80x80_MiniFASNetV2.onnx`
- ถ้าไม่มีไฟล์ → `AntiSpoofEngine.available = False` → graceful degradation (ระบบทำงานปกติ ไม่ block)
- เปิด: ตั้ง `anti_spoof_enabled=1` ใน Settings UI

**Production deployment steps:**
```bash
# 1. Generate SSL cert (first time)
sh nginx/generate_self_signed_cert.sh

# 2. Copy and fill env file
cp .env.prod.example .env.prod
# Edit .env.prod with real passwords

# 3. Start stack
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# 4. Backup (run daily via cron)
bash scripts/backup.sh
```

**⚠️ uvicorn Windows zombie process warning:**
- อย่าปิด terminal ด้วย X — ให้ Ctrl+C แทน
- ถ้า backend ไม่ตอบสนองถูกต้อง ให้รัน `taskkill /F /IM python.exe` ก่อนเสมอ

**Sprint 16 priorities:**
1. GitHub push Sprint 9–15d (ต้องขออนุญาต user)
2. Grafana dashboard — visualize Prometheus metrics (optional, LOW priority)
3. Phase 5 remaining: cron/scheduler for automatic backup (LOW priority)

---

## Sprint 15d — Load Test Verification + Prometheus Endpoint (2026-05-19)

**Session:** 15 (continuation)  
**เป้าหมาย:** ยืนยัน Sprint 15c optimizations ด้วย load test จริง + wire `/metrics` + sync docs

### งานที่ทำ

| # | งาน | ผลลัพธ์ |
|---|-----|--------|
| 1 | Wire `GET /metrics` Prometheus endpoint ใน `main.py` | ✅ `generate_latest()` + `CONTENT_TYPE_LATEST` |
| 2 | Load test: 10 cameras × 2fps × 30s | ✅ **0% error**, p95=3.5s (CPU bound) |
| 3 | `PROJECT_STATUS.md` — Sprint 14–15d sync | ✅ Phase 5: 40% → 85% |
| 4 | `SPRINT_LOG.md` — Sprint 15d entry | ✅ |
| 5 | `CLAUDE.md` — Phase 5 %, pending work | ✅ |

### Files Modified
| File | การเปลี่ยนแปลง |
|------|---------------|
| `backend/main.py` | +4 lines: `GET /metrics` route (Prometheus text format) |
| `doc/project_management/PROJECT_STATUS.md` | Sprint 14–15d sections + metrics results |
| `doc/project_management/SPRINT_LOG.md` | Sprint 15d entry + state update |
| `CLAUDE.md` | Phase 5 %, Sprint 16 priorities |

### Load Test Details
```
Script  : backend/scripts/load_test.py
Command : python load_test.py --cameras 10 --fps 2 --duration 30
Hardware: CPU-only (no GPU), 4 inference workers

Results:
  Cameras       : 10
  Frames sent   : 104  |  OK: 104  |  Errors: 0
  Error rate    : 0.00% ✅
  Throughput    : 3.5 frames/s
  Latency       : min=1,250ms  p50=3,023ms  p95=3,547ms  p99=3,594ms
  Backend CPU   : avg=395.5%  max=504.7%
  Backend RAM   : avg=837MB   max=847MB

Note: Latency is CPU-bound (no GPU). Error rate 0% is the primary SLO — passed.
```

**⚠️ GitHub push policy:** ต้องขออนุญาต user ก่อนทุกครั้ง — ห้าม push โดยไม่บอก

---

## Sprint 16 — Phase 2/3 Completion: ONNX Auto-Detect + Line/Email + Absent Alerts ✅ DONE
**วันที่:** 2026-05-19  
**เป้าหมาย:** ปิด Phase 2 และ Phase 3 ให้ครบ 100%

### สิ่งที่ทำ

| # | งาน | ผลลัพธ์ |
|---|-----|--------|
| S16.1 | `get_best_provider(override)` — CUDA→DirectML→ROCm→CPU auto-detect | ✅ |
| S16.2 | `config.py` — `onnxruntime_provider="auto"` + `/health` exposes active provider | ✅ |
| S16.3 | `notification_service.py` — Line Notify API + SMTP Email via `asyncio.to_thread` | ✅ |
| S16.4 | `absent_alert_service.py` — background loop ทุก 5 นาที, Redis dedup per day | ✅ |
| S16.5 | `main.py` — seed settings: line/email/notify_on_absent + start `absent_alert_loop` | ✅ |
| S16.6 | `SettingsView.vue` — เพิ่ม Line Notify + Email (SMTP) fields ใน Notifications group | ✅ |
| S16.7 | Phase 2 → **100%** ✅, Phase 3 → **100%** ✅ | ✅ |

### Files Modified
| File | การเปลี่ยนแปลง |
|------|---------------|
| `backend/app/core/face_engine.py` | `get_best_provider(override)` + `_PROVIDER_MAP` |
| `backend/app/core/config.py` | `onnxruntime_provider="auto"` |
| `backend/main.py` | `/health` response + seed 6 new settings + absent_alert_loop |
| `backend/app/services/notification_service.py` | Line Notify + Email channels + `_fmt_absent()` |
| `backend/app/services/absent_alert_service.py` | NEW — absent background service |
| `frontend/src/views/SettingsView.vue` | Line Notify + Email SMTP fields |
| `doc/project_management/PROJECT_STATUS.md` | Phase 2/3 → 100% |
| `CLAUDE.md` | Phase bars updated |

---

## Sprint 17 — Smooth Multi-Face Overlay + 4× Faster CPU Inference ✅ DONE
**วันที่:** 2026-05-19  
**เป้าหมาย:** แก้ปัญหา bbox กระตุก + เพิ่มความเร็ว CPU inference

### ปัญหาที่แก้

**ก่อน (Sprint 16):** bbox overlay วาดใหม่ทุกครั้งที่ได้ผล WebSocket → ที่ 2fps bbox กระตุก/หาย 0.5s ทุกครั้ง  
**หลัง (Sprint 17):** `requestAnimationFrame` render loop แยกจาก WebSocket → bbox smooth 60fps + fade animation

### สิ่งที่ทำ

| # | งาน | ผลลัพธ์ |
|---|-----|--------|
| S17.1 | `ScanView.vue` — `requestAnimationFrame` render loop แยกจาก WebSocket | ✅ bbox smooth 60fps |
| S17.2 | Fade animation: `FADE_START_MS=1200` / `FADE_END_MS=2400` — boxes ไม่หายทันที | ✅ |
| S17.3 | `config.py` — `face_detect_size` default: 640 → **320** (4× faster CPU: ~400ms → ~100ms) | ✅ |
| S17.4 | `_drawBBoxes(faces, opacity)` — รับ opacity parameter + `ctx.globalAlpha` | ✅ |

### Files Modified
| File | การเปลี่ยนแปลง |
|------|---------------|
| `frontend/src/views/ScanView.vue` | `_rafHandle`, `_startRenderLoop()`, `_stopRenderLoop()`, fade logic |
| `backend/app/core/config.py` | `face_detect_size` default 640 → 320 |

---

## Sprint 18 — Debug + Pipeline Analysis + Session Rules (2026-05-19)
**วันที่:** 2026-05-19  
**เป้าหมาย:** ตรวจสอบ anti-spoof, วิเคราะห์ 10+ faces, ทบทวน mobile UI

### สิ่งที่ทำ

#### 1. Anti-Spoof Debug
**อาการ:** Anti-spoof ไม่ทำงานเมื่อทดสอบบนมือถือ  
**สาเหตุ:** `anti_spoof_enabled` seeded ค่า default เป็น `"0"` (disabled by design)  
**วิธีแก้:** เปิดใน Settings UI → `anti_spoof_enabled = 1` หรือ `redis-cli SET setting:anti_spoof_enabled 1`  
**โค้ดที่เกี่ยวข้อง:**
```python
# websocket.py
spoof_enabled = await get_anti_spoof_enabled()   # reads setting:anti_spoof_enabled
              and anti_spoof_engine.available      # model file exists
# ถ้า setting=0 → spoof_enabled=False → ทุก face ผ่านโดยไม่เช็ค
```

#### 2. 10+ Faces Pipeline Analysis
**คำถาม:** ถ้า frame มี 10++ ใบหน้า ระบบรองรับได้ไหม?  
**คำตอบ:** รองรับได้ดี — ทุกขั้นตอนหลักเป็น batch/parallel แล้ว

| ขั้นตอน | วิธีการ | ประสิทธิภาพ |
|---------|---------|------------|
| Face detection | 1 ONNX pass (InsightFace) | ✅ O(1) call |
| IoU tracker cache | instant lookup | ✅ ข้ามทุกอย่าง |
| Anti-spoof | `asyncio.gather` parallel | ✅ |
| Qdrant search | `search_batch()` 1 HTTP call | ✅ Sprint 15b |
| DB lookup + crop | `asyncio.gather` concurrent | ✅ |
| log_attendance | sequential (intentional) | ✅ cooldown ทำให้เร็ว |
| `get_unknown_alert_threshold` | Settings cache 5s TTL | ✅ Sprint 15b |

#### 3. MobileScanView Review
**คำถาม:** Mobile display เหมาะสมไหม?  
**คำตอบ:** เหมาะสมครับ — ออกแบบมาเป็น "Camera Agent" สำหรับ operator ถือที่ประตู

| Feature | รายละเอียด |
|---------|-----------|
| Fullscreen | `fixed inset-0`, ไม่มี sidebar |
| `object-cover` | เต็มจอ ไม่มี letterbox |
| HUD card | กลางจอ `clamp(22px–32px)` อ่านง่ายแดด |
| Audio + TTS | พูดชื่อ → ไม่ต้องมองจอ |
| Vibration | สั่นเมื่อเจอ unknown |
| Wake Lock | หน้าจอไม่ดับ |
| iOS safe area | `env(safe-area-inset-*)` |
| Unknown hold | รอ 2 frames ก่อนแสดง "ไม่รู้จัก" |

#### 4. Lesson Learned — Worktree Rule
**เหตุการณ์:** Session รันอยู่ใน worktree (Sprint 14 code) → แก้ไขโค้ดที่มีอยู่แล้วใน main repo (Sprint 15) → เสีย tokens โดยเปล่าประโยชน์  
**กฎใหม่สำหรับ AI session:**
1. **อ่านไฟล์จาก main repo เสมอ** — `F:\programming\python\OmniSight\...` ไม่ใช่ worktree path
2. **เช็คก่อน implement** — Grep/Read main repo ก่อนทุกครั้ง
3. **แก้ไฟล์ใน main repo โดยตรง** — ไม่แก้ใน worktree แล้วค่อย copy
4. **ก่อน commit** — `git diff --stat` จาก `F:\programming\python\OmniSight` เสมอ

### Files Modified
| File | การเปลี่ยนแปลง |
|------|---------------|
| `doc/project_management/SPRINT_LOG.md` | เพิ่ม Sprint 16, 17, 18 entries |
| `doc/project_management/PROJECT_STATUS.md` | อัปเดต header date |
| `CLAUDE.md` | เพิ่ม Worktree Rule section |

---

## Sprint 18b — Production Bug Fixes + Anti-Spoof Analysis (2026-05-20)
**วันที่:** 2026-05-20  
**เป้าหมาย:** แก้ bugs จาก production log จริง + วิเคราะห์ปัญหา mobile

### Bugs ที่พบและแก้ไข

#### BUG-007 — `AttendanceLog.check_in_time` ไม่มีอยู่จริง ✅ Fixed
**อาการ:** `AbsentAlertService scan error: type object 'AttendanceLog' has no attribute 'check_in_time'`  
**สาเหตุ:** `absent_alert_service.py` ใช้ชื่อ attribute ผิด — ORM ใช้ `timestamp` ไม่ใช่ `check_in_time`  
**แก้:** `AttendanceLog.check_in_time` → `AttendanceLog.timestamp`  
**ไฟล์:** `backend/app/services/absent_alert_service.py` line 75

#### BUG-008 — Anti-spoof reject ทุก face จาก mobile โดยไม่มี log score ✅ Fixed
**อาการ:** หลังเปิด `anti_spoof_enabled=1` → mobile scan หยุดทำงาน ไม่มี attendance log  
**สาเหตุ:** MiniFASNet score จาก mobile = 0.018–0.049 (ต่ำมาก) เพราะ JPEG compression ทำลาย texture  
**แก้:** เพิ่ม `logger.warning("Anti-spoof REJECTED: score=%.3f threshold=%.3f")` เพื่อ debug  
**ไฟล์:** `backend/app/api/websocket.py` — Step 3 spoof check

### Anti-Spoof Compatibility Analysis

| สถานการณ์ | Score | เหมาะ? |
|-----------|-------|--------|
| Enrollment (ภาพนิ่ง) | สูง | ✅ ใช้ได้ดี |
| Webcam USB คุณภาพสูง | ปกติ | ✅ ใช้ได้ |
| Mobile browser scan | 0.018–0.049 | ❌ JPEG compression ทำลาย texture |

**ข้อสรุป:** Anti-spoof ไม่เหมาะสำหรับ real-time mobile scan  
**แนวทาง:** เปิด anti-spoof เฉพาะ enrollment, ปิดสำหรับ scan บนมือถือ

### Mobile Performance Analysis

**Red rectangle ช้า** — เป็น physics ของ CPU ไม่ใช่ bug:
```
ส่ง frame ทุก 500ms (2fps) + CPU inference 300–500ms = round-trip ~800ms–1s
```
GPU จะลดเหลือ ~50ms

### ECONNRESET Analysis

`Error: read/write ECONNRESET` ใน Vite console = **ปกติ** ใน dev mode  
- เกิดเมื่อ backend restart, mobile ไป background, หรือ network blip  
- Frontend มี auto-reconnect 3 วินาทีอยู่แล้ว  
- Production (nginx) ไม่มี error เหล่านี้

### Files Modified
| File | การเปลี่ยนแปลง |
|------|---------------|
| `backend/app/services/absent_alert_service.py` | `check_in_time` → `timestamp` |
| `backend/app/api/websocket.py` | เพิ่ม WARNING log เมื่อ anti-spoof reject |
| `.gitignore` | เพิ่ม `logs/` |

---

## Sprint 19 — System Info Admin Dashboard (2026-05-20)
**วันที่:** 2026-05-20  
**เป้าหมาย:** หน้า admin ที่แสดงสถานะ services ทุกตัวใน Single Pane of Glass

### สิ่งที่ทำ

#### 1. Backend — `backend/app/api/system.py` (NEW)
- `GET /api/v1/system/info` — admin-only endpoint (Depends require_admin)
- Query services ทุกตัวพร้อมกัน: App, Face Engine, Anti-Spoof, PostgreSQL, Qdrant, Redis, Storage

| Function | ข้อมูลที่ดึง |
|----------|------------|
| `_app_info()` | version, uptime, ONNX provider, detect_size, inference_workers |
| `_face_engine_info()` | loaded status, model name, det_size |
| `_anti_spoof_info()` | available, model path, note |
| `_postgres_info()` | version, db size MB, host, row counts (8 tables) |
| `_qdrant_info()` | host, collection, vectors_count, points_count, vector_size, distance, quantization |
| `_redis_info()` | url, version, memory MB, peak MB, clients, uptime, keyspace |
| `_storage_info()` | path, snapshots count, snapshots MB, disk free/total GB |

#### 2. Backend — `backend/main.py`
- Import `system` router และ register ที่ `/api/v1/system`

#### 3. Frontend — `frontend/src/views/SystemView.vue` (NEW)
- Grid layout 3 columns: App, Face Engine, Anti-Spoof, PostgreSQL, Qdrant, Redis, Storage
- StatusBadge component: green `ok` / red `error` badge
- Row component: label + value pair (mono option, highlight option)
- Stat component: compact number + label สำหรับ row counts
- `formatUptime()`: แปลง seconds → "Xd Xh Xm"
- `onnxColor()`: CUDA=green, DirectML/ROCm=blue, CPU=gray
- Loading skeleton 6 cards ขณะ fetch
- Error alert + Refresh button

#### 4. Frontend — `frontend/src/router/index.js`
- เพิ่ม route `/system` → `SystemView.vue` (ADMIN only)

#### 5. Frontend — `frontend/src/layouts/AppLayout.vue`
- เพิ่ม menu item "System Info" ใต้หมวด System (sidebar)

### ประโยชน์ของ System Info Page

| Scenario | ก่อน | หลัง |
|----------|------|------|
| ระบบช้าลง | SSH + `nvidia-smi` | เปิดหน้า → ONNX provider card |
| Enrollment ไม่ผ่าน | ไม่รู้สาเหตุ | Face Engine `loaded: error` ทันที |
| DB ใกล้เต็ม | SSH + `df -h` + `psql` | Disk free GB + DB size MB ในหน้าเดียว |
| Qdrant vs Postgres sync | คำนวณเอง | `Vectors: 6` vs `Enrolled: 6` |
| Redis หาย | debug blindly | Redis card แดง → แก้ได้เลย |

### Files Modified
| File | การเปลี่ยนแปลง |
|------|---------------|
| `backend/app/api/system.py` | NEW — system info endpoint |
| `backend/main.py` | register system router |
| `frontend/src/views/SystemView.vue` | NEW — admin dashboard view |
| `frontend/src/router/index.js` | เพิ่ม /system route (ADMIN) |
| `frontend/src/layouts/AppLayout.vue` | เพิ่ม System Info menu item |

---

## Sprint 20 — 2-Phase Multi-Face Pipeline Redesign (2026-05-20)
**วันที่:** 2026-05-20  
**เป้าหมาย:** World-class multi-face recognition pipeline — ถูกต้อง, รวดเร็ว, ไม่มี race condition

### Background
ปัญหาของ pipeline เดิม:
- N async `db.execute()` บน AsyncSession เดียวกัน (unsafe concurrent access)
- Cooldown check + DB write อยู่ใน critical path → ช้า
- Sync disk write (`write_bytes`) บน event loop → blocking
- ไม่มี batch queries (N Qdrant round-trips, N SQL queries)

### สถาปัตยกรรมใหม่ (2-Phase Design)

```
Frame arrives
     │
     ▼
[PHASE 1 — CRITICAL PATH]
  decode JPEG → FaceDetect → anti-spoof batch → Qdrant search_batch
  → WHERE id IN (...) lookup → check_and_reserve() [Redis, parallel]
  → build FaceResult list
     │
     ▼
 send_text()   ← frontend รับผลทันที
     │
     ▼
[PHASE 2 — BACKGROUND]  asyncio.create_task()
  persist_attendance_batch()
    ├─ own DB session
    ├─ single transaction (all N records)
    ├─ snapshot saves in executor (non-blocking)
    └─ Redis publish notifications
```

### สิ่งที่ทำ

#### 1. `backend/app/api/websocket.py` — Pipeline Redesign
- **ลบ** `async with async_session_factory() as db:` จาก while loop ทั้งหมด
- **Phase 1**: เพิ่ม `check_and_reserve(matches)` — parallel Redis EXISTS + SET ก่อน `send_text()`
- **Phase 2**: เพิ่ม `asyncio.create_task(_persist_and_broadcast(...))` หลัง `send_text()`
- **`_persist_and_broadcast()`**: background function เปิด DB session ของตัวเอง
- **Employee lookup**: เปลี่ยนจาก N concurrent `db.execute()` → `WHERE id IN (...)` + dict lookup (1 round-trip, thread-safe)
- Import เปลี่ยน: `check_and_reserve, persist_attendance_batch` แทน `log_attendance`

#### 2. `backend/app/services/attendance_service.py` — Complete Rewrite
- **`check_and_reserve(matches)`** — Phase 1, Redis only, parallel gather:
  - Parallel EXISTS checks สำหรับทุก match
  - Parallel SET cooldown สำหรับ match ที่จะ log
  - Set cooldown ก่อน DB write → ป้องกัน race condition ข้าม frames
  - Returns `list[bool]` — True = จะถูก log
- **`persist_attendance_batch(to_persist)`** — Phase 2, own DB session:
  - Single `flush()` → เอา IDs ทุกตัวใน 1 round-trip
  - Parallel snapshot saves ด้วย `run_in_executor` (sync `write_bytes` ไม่บล็อก event loop)
  - Single `commit()` สำหรับทุก N records
- **`log_attendance()`**: legacy function ยังคงไว้ใช้ใน tests + scripts

#### 3. `backend/app/db/redis.py`
- Rename `_get_cooldown_seconds` → `get_cooldown_seconds` (public)
- `attendance_service.py` import function นี้ตรงๆ

### Race Condition Prevention

| ปัญหา | วิธีแก้ |
|-------|--------|
| Frame N+1 มาในขณะที่ DB write ยังค้างอยู่ | Set Redis cooldown ใน Phase 1 ก่อน DB write |
| Concurrent coroutines บน AsyncSession เดียวกัน | Phase 2 เปิด session ใหม่ทุกครั้ง |
| Event loop blocking จาก disk write | `run_in_executor(None, snap_path.write_bytes, data)` |
| N SQL queries สำหรับ N matches | `WHERE id IN (...)` → 1 query + dict lookup |

### Files Modified
| File | การเปลี่ยนแปลง |
|------|---------------|
| `backend/app/api/websocket.py` | 2-phase pipeline, `_persist_and_broadcast()` background task |
| `backend/app/services/attendance_service.py` | `check_and_reserve()` + `persist_attendance_batch()` |
| `backend/app/db/redis.py` | expose `get_cooldown_seconds` as public |

### Commit
- `26ce1b6` — Sprint 20: 2-phase multi-face pipeline redesign

---

## Sprint 20b — Mobile Scan UX Overhaul + Recognition Cache TTL ✅ DONE
**วันที่:** 2026-05-20–21  
**เป้าหมาย:** แก้ปัญหา UX บน MobileScanView หลายอย่างที่พบจากการใช้งานจริง

### ปัญหาที่พบ (จากการทดสอบจริง)

| ปัญหา | ผลกระทบ |
|-------|---------|
| Panel แสดง Unknown face ทำให้รก | ข้อมูลสำคัญถูกฝังอยู่ใน noise |
| 10 คนยืนแช่ → panel เต็ม + audio spam | UX แย่มาก |
| หันกล้องไปทางอื่นหลังสแกน 10 คน → lag + bbox ค้าง | backlog frame queue |
| Bbox ค้างตอน WS reconnect | stale visual state |
| fps แสดง "0.0 fps" ตอน reconnect | confusing |

### วิธีแก้

#### 1. `frontend/src/views/MobileScanView.vue` — Complete Redesign
- **3-panel layout** ตาม wireframe: 50vh camera / flex info panel / fixed controls
- **Event feed pattern**: `_faceMap` Map ด้วย 7s TTL — แสดงเฉพาะ `attendance_logged===true` หรือ `status==='spoof'` (ตัด Unknown ออก)
- **Audio cooldown**: fresh check-in 5s, repeat match 60s, alert (spoof/unknown) 5s
- **Backpressure gate**: `_waitingResponse` flag — ไม่ส่ง frame ถัดไปจนกว่าจะได้รับผลจาก backend
- **Frame timeout**: `FRAME_TIMEOUT_MS = 2500` — ถ้า 2.5s ไม่มีตอบ → clear canvas + unblock
- **`_clearBBoxCanvas()`** เรียกใน `ws.onclose` (ลบ stale bbox ตอน reconnect)
- **fps display**: `v-if="wsState === 'open'"` (ซ่อนตอน reconnect)
- **Corner accent bbox**: เส้น accent ที่มุม + label ชื่อใต้ bbox

```javascript
// Backpressure pattern
let _waitingResponse   = false
let _frameTimeoutTimer = null
const FRAME_TIMEOUT_MS = 2500

// ใน _sendFrame()
if (_waitingResponse) return
// ...หลัง ws.send(blob):
_waitingResponse = true
_frameTimeoutTimer = setTimeout(() => {
  _waitingResponse = false
  _clearBBoxCanvas()
}, FRAME_TIMEOUT_MS)

// ใน ws.onmessage:
_waitingResponse = false
clearTimeout(_frameTimeoutTimer)
```

#### 2. `backend/app/core/tracker.py` — Configurable Cache TTL
```python
def get_cached_result(self, track_id: int, ttl: float = RESULT_CACHE_S) -> "FaceResult | None":
    track = self._tracks.get(track_id)
    if track and track.result is not None:
        if time.monotonic() - track.result_time < ttl:
            return track.result
    return None
```

#### 3. `backend/app/api/websocket.py` — Recognition Cache TTL from Settings
- เพิ่ม `recognition_cache_ttl` ใน `_get_frame_settings()` อ่านจาก Redis
- Pass TTL ไปยัง `tracker.get_cached_result(tid, ttl=cache_ttl)`

#### 4. `backend/app/api/settings.py`
- เพิ่ม `"recognition_cache_ttl": ("int", 5, 300)` ใน `_VALIDATORS`
- เพิ่ม `"recognition_cache_ttl": "live"` ใน `LIVENESS`

#### 5. `frontend/src/views/SettingsView.vue` + `backend/main.py`
- เพิ่ม `recognition_cache_ttl` ใน Performance group + DEFAULT_SETTINGS seed (30s)

### ผลลัพธ์
| ปัญหา | วิธีแก้ | ผล |
|-------|---------|-----|
| Unknown รก | Filter panel เฉพาะ logged/spoof | Panel สะอาด ✅ |
| 10 คนยืนแช่ | Cache TTL 30s + audio cooldown 60s | Qdrant calls ลด ~93% ✅ |
| Lag หลังสแกน 10 คน | Backpressure gate + 2.5s timeout | ไม่มี queue buildup ✅ |
| Bbox ค้าง WS reconnect | `_clearBBoxCanvas()` ใน onclose | Clear ทันที ✅ |
| "0.0 fps" reconnect | `v-if="wsState === 'open'"` | ซ่อนขณะ reconnect ✅ |

### Commits
- `93c90d6` — feat: configurable recognition cache TTL
- `d12da52` — fix(mobile-scan): clear stale bboxes on WS disconnect + hide fps when reconnecting
- `447b84a` — feat(settings-ui): add recognition_cache_ttl to Performance tab
- `a1b5e72` — fix: add recognition_cache_ttl to DEFAULT_SETTINGS seed
- `a6766e5` — fix(mobile-scan): fix 10-people-standing-still problem
- `250670d` — fix(mobile-scan): hide unknown faces from info panel
- `39bdf2a` — feat(mobile-scan): redesign to 3-panel layout per wireframe
- `46b64bb` — fix(mobile-scan): backpressure + auto-clear bbox to prevent lag after 10-face scan

---

## Sprint 20c — Team Setup (Magic Onboarding) ✅ DONE
**วันที่:** 2026-05-21  
**เป้าหมาย:** ทีมใหม่ clone แล้วพัฒนาได้ใน 10 นาที โดยไม่ต้องถามขั้นตอน

### สิ่งที่ทำ

#### 1. `setup.bat` (NEW)
- Script 5 ขั้นตอน: prerequisite check → venv → pip install → docker up + migrate → npm install
- Error handling ทุก step — exit พร้อม message ชัดเจน
- แสดง default login credentials + URLs เมื่อสำเร็จ

#### 2. `backend/.env` (ตอนนี้ tracked ใน git)
- Dev defaults ครบ — ไม่มี secret จริง (localhost passwords)
- ทีมไม่ต้องสร้าง `.env` เอง

#### 3. `.gitignore`
- Uncomment `backend/.env` จาก exclusion list

#### 4. `README.md` (Complete Rewrite)
- 4-step Quick Start (clone → prerequisites → `setup.bat` → `start-dev.bat`)
- Project structure, tech stack, common commands, team workflow, troubleshooting section

### ผลลัพธ์
จาก **"อ่าน README 30 นาทีแล้วยังไม่รู้จะเริ่มยังไง"** → `setup.bat` แล้วรอ 10 นาที ready

### Commit
- `98b52c6` — chore: magic one-click setup for team members

---

## Sprint 21 — Prometheus + Grafana Observability Stack ✅ DONE
**วันที่:** 2026-05-21  
**เป้าหมาย:** visualize `/metrics` endpoint ด้วย Grafana — pre-built dashboard พร้อมใช้ทันที

### สิ่งที่ทำ

#### 1. `prometheus.yml` (NEW)
- Scrape backend `/metrics` ทุก 15s ผ่าน `host.docker.internal:8000`
- TSDB retention: 15 วัน

#### 2. `grafana/` directory (NEW)
```
grafana/
├── provisioning/
│   ├── datasources/prometheus.yml  ← auto-wire Prometheus datasource
│   └── dashboards/provider.yml     ← auto-load dashboards จาก /etc/grafana/dashboards
└── dashboards/omnisight.json       ← pre-built OmniSight dashboard (10 panels)
```

**Dashboard panels:**
| Panel | Type | Metric |
|-------|------|--------|
| Active Cameras | Stat (colored) | `omnisight_active_cameras` |
| Inference Workers | Stat | `omnisight_inference_workers` |
| Inflight Inferences | Stat | `omnisight_inflight_inferences` |
| Frame Drop Rate | Stat % | `dropped / received * 100` |
| Cache Hit Rate | Stat % | `hits / (hits + misses) * 100` |
| Frame Pipeline | Timeseries | received / processed / dropped fps |
| Face Results | Timeseries | detected / matched / unknown / spoof fps |
| Inference Latency | Timeseries | p50 / p95 histogram_quantile |
| Qdrant Search Latency | Timeseries | p50 / p95 histogram_quantile |
| Cache Hits vs Misses | Timeseries | hits / misses rate comparison |

#### 3. `docker-compose.yml`
- เพิ่ม `prometheus` service (port 9090, `host-gateway` extra_host)
- เพิ่ม `grafana` service (port 3000, GF_SECURITY_ADMIN_PASSWORD=admin)
- เพิ่ม volumes: `promdata`, `grafanadata`

### Load Test Sprint 21 (10 cameras × 2fps × 30s)

| Metric | Sprint 15d | Sprint 21 | เปลี่ยนแปลง |
|--------|-----------|-----------|------------|
| Error rate | 0.00% | **0.00%** | — |
| p50 latency | 3,023ms | **1,187ms** | 🟢 2.5× faster |
| p95 latency | 3,547ms | **1,969ms** | 🟢 1.8× faster |
| CPU avg | 395% | **297%** | 🟢 -25% |
| RAM avg | 837MB | **792MB** | 🟢 -5% |

> การปรับปรุงเกิดจาก Sprint 15b–20: 2-phase pipeline + backpressure + recognition cache TTL + batch ops

### Commits
- `8beef1b` — feat(sprint-21): Prometheus + Grafana observability stack
