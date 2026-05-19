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
- AI: InsightFace buffalo_l (ONNX) + MiniFASNet anti-spoofing (optional)
- Vector DB: Qdrant (HNSW + SQ8)
- Cache: Redis (station filter, attendance cooldown, settings)
- SQL DB: PostgreSQL 16
- Frontend: Vue 3 + Vite + Tailwind CSS + DaisyUI
- Services: Docker (Postgres 5432, Qdrant 6333, Redis 6379)
- Production: nginx SSL reverse proxy, docker-compose.prod.yml

---

## Environment Setup

```powershell
# Start backend (dev)
cd F:\programming\python\OmniSight
.\start-dev.bat           # kills old python, then uvicorn at http://localhost:8000

# Start frontend (dev)
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

# Production deploy
sh nginx/generate_self_signed_cert.sh
cp .env.prod.example .env.prod    # fill in real passwords
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Backup
bash scripts/backup.sh            # Linux/WSL
powershell -File scripts\backup.ps1  # Windows
```

---

## สถานะปัจจุบัน

### Phase Progress
```
Phase 1 — Foundation     ████████████████████ 100%  ✅ DONE
Phase 2 — AI Core        █████████████████░░░  85%  🔄 IN PROGRESS
Phase 3 — HR Features    ████████████████████ 100%  ✅ DONE
Phase 4 — Multi-Camera   ████████████████████ 100%  ✅ DONE
Phase 5 — Production     ████████░░░░░░░░░░░░  40%  🔄 IN PROGRESS
```

### Data ใน DB (ณ Sprint 13)
| รายการ | ค่า |
|--------|-----|
| Employee | emp1 (6/6 enrolled ✅), emp2 (0/6) |
| Station | sta1 (ccd829a0), sta2 (07464848) |
| Users | admin (ADMIN), hr1 (HR), operator1 (OPERATOR) |
| Attendance logs | 27+ records, id≥27 มี snapshot_path |
| Qdrant vectors | 6 (0 orphaned — BUG-002 ✅ fixed) |

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

## Anti-Spoofing Architecture (Sprint 13 — ✅ DONE)

| Component | รายละเอียด |
|-----------|-----------|
| Model | MiniFASNet V2 (`2.7_80x80_MiniFASNetV2.onnx`, 1.7MB) |
| Path | `models/anti_spoof/2.7_80x80_MiniFASNetV2.onnx` |
| Input | `(batch, 3, 80, 80)` NCHW float32 ImageNet-normalized |
| Output | `(batch, 3)` logits → `softmax()[1]` = liveness score |
| Degradation | ถ้าไม่มีไฟล์ → `available=False` → ทุก check ผ่าน (True, 1.0) |
| Enrollment gate | HTTP 422 ถ้า liveness < threshold |
| Scan gate | `status="spoof"` FaceResult — ไม่ log attendance |
| Enable | ตั้ง `anti_spoof_enabled=1` ใน Settings UI |

---

## Production Architecture (Sprint 13 — ✅ DONE)

| Component | รายละเอียด |
|-----------|-----------|
| `docker-compose.prod.yml` | postgres + qdrant + redis + backend + nginx |
| Storage | `./data/storage` bind mount (host-accessible for backup) |
| InsightFace models | `insightface_models` named volume (survives `docker build --no-cache`) |
| SSL | nginx/ssl/ (generate with `sh nginx/generate_self_signed_cert.sh`) |
| Env | `.env.prod` from `.env.prod.example` |
| Backup | `scripts/backup.sh` / `scripts/backup.ps1` — 7-day rotation |
| Restore | `scripts/restore.sh <backup-dir>` |

---

## งานที่ต้องทำถัดไป (Sprint 14)

### ลำดับความสำคัญ
1. 🟢 **GitHub push** — Sprint 9–13 (ต้องขออนุญาต user)
2. 🟡 **Logging & monitoring** — structured JSON logs + file rotation
3. 🟢 **Performance test** — 1000 employees, 10+ cameras
4. 🟢 **rtsp_agent Dockerfile** — สำหรับ production CCTV deploy

---

## Bug ที่ยังเปิดอยู่

| ID | ปัญหา | Severity | สถานะ |
|----|-------|----------|-------|
| (none) | — | — | — |

---

## เอกสารสำคัญ

| ไฟล์ | เนื้อหา |
|------|---------|
| `doc/project_management/PROJECT_STATUS.md` | Dashboard + phase tracking |
| `doc/project_management/SPRINT_LOG.md` | Sprint 1–13 history + context |
| `doc/project_management/DECISIONS_LOG.md` | ADR-001 ถึง ADR-011 |
| `doc/cluade_version/chapter_17_multi_camera_pilot_console.md` | Multi-camera & Pilot Console design |
| `doc/cluade_version/chapter_22_auth_authorization.md` | Auth/Authz — seq diagrams + API matrix |

---

## GitHub

- Repository: https://github.com/idev006/OmniSight
- Branch: master
- Latest push: Sprint 8 (`652c445`)
- Sprint 9–13 changes: **ยังไม่ได้ push** (รอ approval)
- .gitignore excludes: `my_env/`, `.env`, `storage/`, `frontend/node_modules/`, `models/`, `data/`, `backups/`

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

*อัพเดทล่าสุด: 2026-05-18 (Sprint 13 — Production Docker stack, backup system, anti-spoofing, late/absent detection)*
