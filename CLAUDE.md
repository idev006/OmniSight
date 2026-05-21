# OmniSight — AI Session Handover

> อ่านไฟล์นี้ก่อนทุกครั้งที่เริ่ม session ใหม่
> 📖 หลักการทำงาน: `doc/project_management/PHILOSOPHY.md`

---

## ⚠️ Path สำคัญ — ห้ามผิด

| สิ่งของ | Path |
|---------|------|
| **เอกสารทุกฉบับ** | `F:\programming\python\OmniSight\doc\claude_version\` |
| **PM docs** | `F:\programming\python\OmniSight\doc\project_management\` |
| **Python venv (3.12)** | `F:\programming\python\OmniSight\my_env\` ← **ที่เดียวเท่านั้น** |
| Python exe | `F:\programming\python\OmniSight\my_env\Scripts\python.exe` |
| pip | `F:\programming\python\OmniSight\my_env\Scripts\pip.exe` |
| Backend | `F:\programming\python\OmniSight\backend\` |
| Frontend | `F:\programming\python\OmniSight\frontend\` |

> **หมายเหตุ:** โฟลเดอร์เอกสารชื่อ `claude_version`

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
Phase 2 — AI Core        ████████████████████ 100%  ✅ DONE
Phase 3 — HR Features    ████████████████████ 100%  ✅ DONE
Phase 4 — Multi-Camera   ████████████████████ 100%  ✅ DONE
Phase 5 — Production     █████████████████░░░  85%  🔄 IN PROGRESS
```

### Data ใน DB (ณ Sprint 15d)
| รายการ | ค่า |
|--------|-----|
| Employee | emp1 (6/6 enrolled ✅), emp2 (0/6), seed 1,000 (EMP00001–EMP01000) |
| Station | sta1 (ccd829a0), sta2 (07464848) |
| Users | admin (ADMIN), hr1 (HR), operator1 (OPERATOR) |
| Attendance logs | 27+ records, id≥27 มี snapshot_path |
| Qdrant vectors | 6,006 (6 real + 6,000 seed) |
| inference_workers | 4 (default, เปลี่ยนได้ใน Settings UI — ไม่ต้อง restart) |

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

## Mobile Scan Architecture (Sprint 20b — ✅ DONE)

| Component | รายละเอียด |
|-----------|-----------|
| Layout | 3-panel: 50vh camera / flex event feed / fixed controls |
| Event feed | `_faceMap` Map 7s TTL — แสดงเฉพาะ `attendance_logged===true` หรือ `status==='spoof'` |
| Audio cooldown | fresh check-in 5s / repeat match 60s / spoof+unknown 5s |
| Backpressure | `_waitingResponse` flag — ไม่ส่ง frame ถัดไปจนกว่า backend จะตอบ |
| Frame timeout | 2500ms safety net — clear bbox + unblock ถ้า backend ไม่ตอบ |
| Stale bbox | `_clearBBoxCanvas()` เรียกใน `ws.onclose` — clean state ทุกครั้ง reconnect |
| Recognition cache TTL | `recognition_cache_ttl` setting (5–300s, default 30s) — reuse Qdrant result ต่อ tracking_id |

---

## Performance Architecture (Sprint 15b–15c — ✅ DONE)

| Component | รายละเอียด |
|-----------|-----------|
| AsyncQdrantClient | `search_batch()` — 1 HTTP round-trip สำหรับ N faces ต่อ frame |
| Anti-spoof batch | `predict_batch()` — N faces → 1 ONNX call |
| Settings cache | 5s TTL + `asyncio.Lock` (stampede-safe) ใน `_get_frame_settings()` |
| cv2.imdecode | รันใน executor — unblock event loop |
| Dynamic workers | Admin เปลี่ยน `inference_workers` ใน Settings UI → ไม่ต้อง restart |
| Hungarian tracker | `scipy.optimize.linear_sum_assignment` — globally optimal face matching |
| FaceEngine warmup | `face_engine.warmup()` at startup — ไม่มี first-camera stall |
| Prometheus metrics | `GET /metrics` — 14 omnisight metrics, Grafana-ready |
| Load test result (Sprint 21) | 10 cameras × 2fps: **error=0%**, p50=1.2s, p95=2.0s, CPU avg=297% (2.5× faster than Sprint 15d) |

---

## 2-Phase Pipeline Architecture (Sprint 20 — ✅ DONE)

```
Frame → detect → anti-spoof batch → search_batch → WHERE id IN(...)
     → check_and_reserve() [Phase 1, Redis parallel]
     → send_text()          ← frontend รับผลทันที
     → asyncio.create_task(_persist_and_broadcast())  ← Phase 2 bg
          ├─ own DB session
          ├─ single INSERT + flush + commit
          ├─ snapshot write in executor (non-blocking)
          └─ Redis publish notifications
```

| Component | รายละเอียด |
|-----------|-----------|
| `check_and_reserve()` | Phase 1 — parallel Redis EXISTS + SET ก่อน send_text |
| `persist_attendance_batch()` | Phase 2 — own session, single transaction, N records |
| Race condition guard | Cooldown set ใน Phase 1 ก่อน DB write → ป้องกัน double-log |
| Employee lookup | `WHERE id IN (...)` — 1 query + dict lookup (thread-safe) |
| Disk write | `run_in_executor(None, write_bytes, data)` — non-blocking |

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

## ⚠️ Worktree Rule — ห้ามผิดทุก session

Session อาจรันอยู่ใน worktree (`.claude/worktrees/...`) ซึ่งมีโค้ดเวอร์ชันเก่ากว่า main repo:

| กฎ | รายละเอียด |
|----|-----------|
| **อ่านจาก main repo เสมอ** | ใช้ path `F:\programming\python\OmniSight\...` ไม่ใช่ worktree path |
| **เช็คก่อน implement** | Grep/Read main repo ก่อนทุกครั้งเพื่อดูว่ามี feature นั้นอยู่แล้วหรือยัง |
| **แก้ใน main repo โดยตรง** | ไม่แก้ใน worktree แล้วค่อย copy กลับ |
| **ก่อน commit** | `git diff --stat` จาก `F:\programming\python\OmniSight` เสมอ |

---

## สถานะ Sprint 22 (✅ DONE — 2026-05-21)

| งาน | สถานะ |
|-----|-------|
| Unit tests (pytest) — 56 tests: security, tracker, config, health, auth | ✅ Done |
| Pre-commit hooks (.pre-commit-config.yaml) — ruff + prettier + hygiene | ✅ Done |
| pyproject.toml — ruff rules + pytest config (asyncio_mode=auto) | ✅ Done |
| requirements-dev.txt — dev deps pinned | ✅ Done |
| docker-compose.prod.yml — Prometheus + Grafana prod services | ✅ Done |
| prometheus.prod.yml — prod scrape config | ✅ Done |

## งานที่ต้องทำถัดไป (Sprint 23+)

### ลำดับความสำคัญ
1. 🟡 **Export PDF report** — HR ต้องการ attendance report ดาวน์โหลดเป็น PDF
2. 🟢 **Phase 5 → 100%** — unit tests ✅, Grafana ✅, เหลือ production smoke test
3. 🟢 **GitHub push** — Sprint 21–22 ยังไม่ได้ push (รอ approval)

---

## Bug ที่ยังเปิดอยู่

| ID | ปัญหา | Severity | สถานะ |
|----|-------|----------|-------|
| (none) | — | — | — |

---

## เอกสารสำคัญ

| ไฟล์ | เนื้อหา |
|------|---------|
| `doc/project_management/PHILOSOPHY.md` | **หลักการทำงาน 7 ข้อ** — อ่านก่อนเริ่มงานทุก session |
| `doc/project_management/PROJECT_STATUS.md` | Dashboard + phase tracking |
| `doc/project_management/SPRINT_LOG.md` | Sprint 1–22 history + context |
| `doc/project_management/DECISIONS_LOG.md` | ADR-001 ถึง ADR-011 |
| `doc/claude_version/chapter_17_multi_camera_pilot_console.md` | Multi-camera & Pilot Console design |
| `doc/claude_version/chapter_22_auth_authorization.md` | Auth/Authz — seq diagrams + API matrix |

---

## GitHub

- Repository: https://github.com/idev006/OmniSight
- Branch: master
- Latest push: Sprint 20c (`98b52c6`) — team setup + README rewrite
- All sprints through Sprint 20c: **pushed ✅**
- .gitignore excludes: `my_env/`, `storage/`, `frontend/node_modules/`, `models/`, `data/`, `backups/`
- `backend/.env` is now **tracked** (localhost defaults only — no real secrets)

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

*อัพเดทล่าสุด: 2026-05-21 (Sprint 22 — unit tests 56 tests 100% pass, pre-commit hooks, prod Prometheus+Grafana)*
