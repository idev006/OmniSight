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
- **ไฟล์ใหม่:** `doc/cluade_version/chapter_22_auth_authorization.md`
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

## Context สำหรับ AI Session ถัดไป

เมื่อเริ่ม session ใหม่ให้อ่าน:
1. `doc/project_management/PROJECT_STATUS.md` — ภาพรวม + phase progress (Phase 1-5 + Sprint 8)
2. `doc/project_management/SPRINT_LOG.md` — Sprint 7 (attendance ✅), Sprint 8 (auth/security ✅)
3. `doc/cluade_version/chapter_17_multi_camera_pilot_console.md` — Multi-camera design ครบ
4. `doc/cluade_version/chapter_22_auth_authorization.md` — Auth/Authz ครบ (seq diagrams + matrix)
5. `doc/project_management/DECISIONS_LOG.md` — ADR-009/010/011 (multi-camera decisions)

**⚠️ Path สำคัญ — ห้ามผิด:**
| สิ่งของ | Path |
|---------|------|
| เอกสารทุกฉบับ | `F:\programming\python\OmniSight\doc\cluade_version\` |
| PM docs | `F:\programming\python\OmniSight\doc\project_management\` |
| Python venv (3.12) | `F:\programming\python\OmniSight\my_env\` ← **ที่เดียวเท่านั้น** |
| Python exe | `F:\programming\python\OmniSight\my_env\Scripts\python.exe` |
| pip | `F:\programming\python\OmniSight\my_env\Scripts\pip.exe` |

**Environment:**
- Backend start: `start-backend.bat` (uvicorn port 8000)
- DB migration: `migrate.bat upgrade`
- Services: Docker → PostgreSQL (5432), Qdrant (6333), Redis (6379)

**State ปัจจุบัน (Sprint 8 done):**
- emp1 (db421a76): enrolled 6/6 slots ✅
- emp2 (848449d0): enrolled 0/6
- sta1 (ccd829a0): ไม่มี dept filter
- attendance_logs: 2 records (Sprint 7 verified)
- Qdrant: 7 vectors (6 จริง + 1 orphaned, BUG-002 open)
- GitHub: https://github.com/idev006/OmniSight (commit 6bb79e9, ยังไม่ push Sprint 8)
- Users: admin (ADMIN), hr1 (HR), operator1 (OPERATOR) — bcrypt hashed

**Auth Architecture (Sprint 8):**
- Frontend SSOT: `auth.js` Pinia store — token expiry computed, no stale state
- localStorage key: `omnisight-token` (legacy `token` key cleaned on init)
- 401 interceptor: redirect `/login?reason=expired` หรือ `/login?reason=deactivated`
- Backend: 17 endpoints ทั้งหมดมี `Depends(require_hr/require_admin/get_current_user)` แล้ว
- JWT expire: admin ตั้งค่าได้ผ่าน /settings → Security → access_token_expire_hours

**งานถัดไป (Sprint 9):**
1. Camera model + CRUD API (cameras table, /api/v1/cameras)
2. WebSocket อัพเดทรับ camera_id
3. CameraManager service + Redis Pub/Sub
4. BUG-002: Orphaned Qdrant vector reconcile

**⚠️ GitHub push policy:** ต้องขออนุญาต user ก่อนทุกครั้ง — ห้าม push โดยไม่บอก
