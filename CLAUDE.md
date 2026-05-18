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
- Frontend: Vue 3 + Vite + Tailwind CSS + DaisyUI
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
Phase 2 — AI Core        ████████████░░░░░░░░  60%  🔄 IN PROGRESS
Phase 3 — HR Features    ████████████████░░░░  80%  🔄 IN PROGRESS
Phase 4 — Multi-Camera   ████████████████████ 100%  ✅ DONE
Phase 5 — Production     ░░░░░░░░░░░░░░░░░░░░   0%  ⏳ PENDING
```

### Data ใน DB (ณ Sprint 11)
| รายการ | ค่า |
|--------|-----|
| Employee | emp1 (6/6 enrolled ✅), emp2 (0/6) |
| Station | sta1 (ccd829a0), sta2 (07464848) |
| Users | admin (ADMIN), hr1 (HR), operator1 (OPERATOR) |
| Attendance logs | 2+ records (snapshot_path ยังว่าง — เพิ่งแก้ bug) |
| Qdrant vectors | 7 (6 จริง + 1 orphaned, BUG-002) |

---

## Auth Architecture (Sprint 8 — ✅ DONE)

| Component | รายละเอียด |
|-----------|-----------|
| Frontend SSOT | `auth.js` Pinia store — `user` computed ตรวจ expiry อัตโนมัติ |
| localStorage key | `omnisight-token` (legacy `token` key ถูก cleanup on init) |
| 401 handler | Axios interceptor → redirect `/login?reason=expired\|deactivated` |
| Backend guards | ทุก endpoint มี `Depends(require_hr/require_admin/get_current_user)` |
| JWT expire | Admin ตั้งค่าได้ผ่าน /settings → Security → access_token_expire_hours |
| No native dialogs | ใช้ `useConfirm()` composable + `<ConfirmModal>` แทน `window.confirm()` |

---

## Multi-Camera Architecture (Sprint 10 — ✅ DONE)

| Component | รายละเอียด |
|-----------|-----------|
| Protocol | ทุกกล้องใช้ binary JPEG over WebSocket เหมือนกัน |
| FPS Gate | `_last_processed` dict ใน `websocket.py` — drop frames per camera |
| Thread pool | `ThreadPoolExecutor(inference_workers)` — face_engine ไม่บล็อก event loop |
| Redis FPS cap | `setting:max_fps_per_camera` — admin เปลี่ยนได้ realtime |
| camera_id | auto-gen: `{sm/wc}-{uid[:6]}-{sid[:6]}` ถ้า client ไม่ระบุ |
| RTSP Bridge | `backend/agents/rtsp_agent.py` — IP Camera/CCTV → WebSocket |
| Mobile | `MobileScanView.vue` — fullscreen `/mobile-scan` route (ไม่มี sidebar) |
| FaceResult | JOIN employees+departments → full_name, emp_code, dept_name ครบ |

---

## Sprint 11 — สิ่งที่ทำเสร็จแล้ว (session นี้)

### ✅ Face Snapshot Evidence (Attendance)
**ปัญหา:** หน้า Attendance ไม่แสดงใบหน้าหลักฐานการลงเวลา  
**Root cause:** `websocket.py` ใช้ตัวแปร `img` ที่ไม่มีอยู่จริง (ควรเป็น `frame`) → NameError ถูก except กลืนเงียบ → crop ไม่เคยสำเร็จ  
**แก้ไขใน:** `backend/app/api/websocket.py` lines 239, 246 — เปลี่ยน `img` → `frame`

**ไฟล์ที่เปลี่ยนในหัวข้อนี้:**
- `backend/app/api/websocket.py` — fix `img` → `frame`, crop error log debug→warning
- `backend/app/services/attendance_service.py` — เพิ่ม `face_crop_jpg` param, save snapshot, absolute path
- `backend/app/models/orm.py` — เพิ่ม `snapshot_path` column
- `backend/app/api/attendance.py` — เพิ่ม `snapshot_url` field + `/attendance/{id}/snapshot` endpoint
- `backend/alembic/versions/c3f8a92b1d74_...py` — migration เพิ่ม snapshot_path column ✅ ran
- `frontend/src/views/AttendanceView.vue` — SnapshotImg component, thumbnail, modal

### ✅ Enrolled Face Viewing (Enrollment Page)
**ปัญหา:** Admin ดูรูปใบหน้าที่ enroll ไว้ไม่ได้  
**แก้ไขใน:**
- `backend/app/api/enrollment.py` — เพิ่ม `image_url` ใน response + endpoint `/employees/{id}/enroll/{index}/image`
- `backend/app/models/schemas.py` — เพิ่ม `image_url: Optional[str]` ใน FaceTemplateOut
- `frontend/src/views/EnrollmentView.vue` — load existing slots with auth-header image fetch

### ✅ Re-enrollment IntegrityError Fix
**Root cause:** SQLAlchemy ไม่ flush DELETE ก่อน INSERT  
**แก้ไขใน:** `backend/app/api/enrollment.py` — เพิ่ม `await db.flush()` หลัง `await db.delete(existing)`

### ✅ Mobile Scan HUD — Dual Overlay Fix
**ปัญหา:** แสดงทั้ง unknown (แดง) และ match (เขียว) พร้อมกัน  
**แก้ไขใน:** `frontend/src/views/MobileScanView.vue`
- Single `<Transition mode="out-in">` + `:key="overlay.type"`
- `_transitioning` flag + `_pendingFace` queue
- `UNKNOWN_HOLD_FRAMES = 2` debounce — ไม่แสดง unknown ทันที รอ 2 frames

### ✅ Camera Selection (Multi-camera Support)
**ปัญหา:** ผู้ใช้เลือกกล้องไม่ได้ทั้ง ScanView และ MobileScanView  
**แก้ไขใน:**
- `frontend/src/views/ScanView.vue` — dropdown เมื่อมี >1 กล้อง, watch + restart
- `frontend/src/views/MobileScanView.vue`:
  - 3+ กล้อง → dropdown; 2 กล้อง → flip button; 0-1 → hidden
  - สลับกล้องระหว่าง streaming ได้ (WS ไม่ reconnect)
  - `watch(selectedCameraId)` → `_switchCamera()` — stop media only, keep WS
  - `switchingCamera` loading state ป้องกัน double-tap

### ✅ Bounding Box Alignment Fix
**ปัญหา:** กรอบสีเขียวไม่อยู่ตรงใบหน้า  
**แก้ไขใน:**
- `MobileScanView.vue` — `_sendFrame` reproduce CSS object-cover crop; `drawBBoxes` scale from sent frame (640×SEND_H)
- `ScanView.vue` — calculate letterbox/pillarbox offset; scale from 640×480

---

## ⚠️ สิ่งที่ต้อง Verify ใน Session ถัดไป

1. **Restart backend** แล้ว scan ใหม่ → ดู log `Snapshot saved:` → ถ้าขึ้น = แก้แล้ว
2. หลัง scan → หน้า Attendance ต้องแสดง thumbnail ใบหน้า (คลิกขยายได้)
3. ถ้า log ขึ้น `WARNING Face crop failed:` ให้ส่ง error มาดู

---

## งานที่ต้องทำถัดไป (Sprint 12)

### ลำดับความสำคัญ
1. 🔴 **Verify snapshot fix** — restart backend + test scan → ดู thumbnail ที่หน้า Attendance
2. 🟡 **BUG-002** — ลบ orphaned Qdrant vector (reconcile script)
3. 🟡 **Anti-spoofing MiniFASNet** — Phase 2 AI feature
4. 🟡 **Face quality gate** — reject blur/dark during enrollment
5. 🟢 **rtsp_agent Dockerfile** — สำหรับ production deploy
6. 🟢 **GitHub push** — Sprint 8+9+10+11 (ต้องขออนุญาต user)

---

## Bug ที่ยังเปิดอยู่

| ID | ปัญหา | Severity | สถานะ |
|----|-------|----------|-------|
| BUG-002 | Orphaned Qdrant vector (7 แทน 6) | Low | Open |

---

## เอกสารสำคัญ

| ไฟล์ | เนื้อหา |
|------|---------|
| `doc/project_management/PROJECT_STATUS.md` | Dashboard + phase tracking |
| `doc/project_management/SPRINT_LOG.md` | Sprint history + context |
| `doc/project_management/DECISIONS_LOG.md` | ADR-001 ถึง ADR-011 |
| `doc/cluade_version/chapter_17_multi_camera_pilot_console.md` | Multi-camera & Pilot Console design |
| `doc/cluade_version/chapter_22_auth_authorization.md` | Auth/Authz — seq diagrams + API matrix |
| `doc/cluade_version/chapter_23_mobile_scan_hud.md` | Mobile Scan HUD — persona, audio, wake lock, state machine |
| `doc/cluade_version/chapter_24_bugs_and_solutions.md` | Bugs BUG-005 ถึง BUG-010 — Docker, Vite proxy, mobile camera, HTTPS |

---

## GitHub

- Repository: https://github.com/idev006/OmniSight
- Branch: master
- Latest commit: `6bb79e9` — multi-camera architecture design
- Sprint 8+9+10+11 changes: **ยังไม่ได้ push** (รอ approval)
- .gitignore excludes: `my_env/`, `.env`, `storage/`, `frontend/node_modules/`

> **⚠️ ห้าม push GitHub โดยไม่ขออนุญาต user ก่อนทุกครั้ง**

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

## Snapshot Evidence — Architecture

```
Scan frame (JPEG) → websocket.py
  → cv2.imdecode → frame (numpy)
  → face detected → bbox (x1,y1,x2,y2)
  → crop frame[y1-pad:y2+pad, x1-pad:x2+pad]   ← ใช้ frame ไม่ใช่ img!
  → cv2.imencode('.jpg') → face_crop_jpg (bytes)
  → log_attendance(face_crop_jpg=...)
      → save to storage/faces/snapshots/YYYY-MM-DD/{log_id}.jpg
      → log.snapshot_path = absolute path

GET /api/v1/attendance/{id}/snapshot  (require_hr)
  → FileResponse(log.snapshot_path)

Frontend AttendanceView.vue
  → SnapshotImg component: api.get(url, {responseType:'blob'})
    → URL.createObjectURL() → <img src>
```

*อัพเดทล่าสุด: 2026-05-18 (Sprint 11 — Face snapshot fix, Camera selection, BBox alignment, Dual overlay fix)*
