# OmniSight — Project Status Dashboard

> **อัปเดตล่าสุด:** 2026-05-20 (Sprint 20 — 2-phase multi-face pipeline redesign)  
> **Project Manager / Lead Dev:** idev006  
> **AI Pair:** Claude Sonnet 4.6  
> **Repository:** https://github.com/idev006/OmniSight  

---

## Overall Progress

```
Phase 1 — Foundation     ████████████████████ 100%  ✅ DONE
Phase 2 — AI Core        ████████████████████ 100%  ✅ DONE
Phase 3 — HR Features    ████████████████████ 100%  ✅ DONE
Phase 4 — Multi-Camera   ████████████████████ 100%  ✅ DONE
Phase 5 — Production     █████████████████░░░  85%  🔄 IN PROGRESS  (Grafana dashboard optional)
```

---

## Phase 1 — Foundation ✅ COMPLETE

**เป้าหมาย:** โครงสร้างระบบพร้อมทดสอบ end-to-end

| # | งาน | สถานะ | วันที่เสร็จ | หมายเหตุ |
|---|-----|--------|-------------|---------|
| 1.1 | Project structure & scaffolding | ✅ Done | 2026-05-16 | backend/frontend/doc/docker |
| 1.2 | Docker Compose (Postgres + Qdrant + Redis) | ✅ Done | 2026-05-16 | port 5432/6333/6379 |
| 1.3 | Database ORM models | ✅ Done | 2026-05-16 | 6 tables: Employee, Department, Shift, Station, FaceTemplate, AttendanceLog |
| 1.4 | Alembic async migration | ✅ Done | 2026-05-16 | migration `31da62320adf` applied |
| 1.5 | Backend API — Auth | ✅ Done | 2026-05-16 | JWT, admin/admin hardcoded |
| 1.6 | Backend API — Departments / Shifts | ✅ Done | 2026-05-16 | CRUD |
| 1.7 | Backend API — Employees | ✅ Done | 2026-05-16 | CRUD + enrollment_count |
| 1.8 | Backend API — Stations | ✅ Done | 2026-05-16 | dept filter sync → Redis |
| 1.9 | Backend API — Enrollment | ✅ Done | 2026-05-16 | 6 slots, Qdrant upsert, quality score |
| 1.10 | Backend API — Attendance | ✅ Done | 2026-05-16 | query by date/dept |
| 1.11 | Backend API — WebSocket scan | ✅ Done | 2026-05-16 | binary JPEG frame, Qdrant search |
| 1.12 | Frontend — Login | ✅ Done | 2026-05-16 | JWT store (Pinia) |
| 1.13 | Frontend — Departments / Shifts | ✅ Done | 2026-05-16 | CRUD table + modal |
| 1.14 | Frontend — Employees | ✅ Done | 2026-05-16 | enrollment progress dots |
| 1.15 | Frontend — Enrollment | ✅ Done | 2026-05-16 | 6-slot webcam capture |
| 1.16 | Frontend — Stations | ✅ Done | 2026-05-16 | dept assignment checkboxes |
| 1.17 | Frontend — Attendance | ✅ Done | 2026-05-16 | date/dept filter table |
| 1.18 | Frontend — Scan (WebSocket live) | ✅ Done | 2026-05-16 | video overlay + identity cards |
| 1.19 | InsightFace buffalo_l install | ✅ Done | 2026-05-16 | MSVC บน F: drive (lesson learned) |
| 1.20 | End-to-end test: Enrollment | ✅ Done | 2026-05-17 | 6/6 slots, quality=0.799 |
| 1.21 | End-to-end test: WebSocket scan | ✅ Done | 2026-05-17 | confidence=99.57%, match ถูกต้อง |
| 1.22 | GitHub push | ✅ Done | 2026-05-17 | 72 files, pip freeze locked |
| 1.23 | GitHub push (Sprint 7) | ✅ Done | 2026-05-17 | commit dac4ab2, requirements.txt updated |

---

## Phase 2 — AI Core 🔄 IN PROGRESS (85%)

**เป้าหมาย:** ระบบ recognition เต็มรูปแบบ + attendance logging อัตโนมัติ

| # | งาน | สถานะ | Priority | หมายเหตุ |
|---|-----|--------|----------|---------|
| 2.1 | Attendance auto-logging เมื่อ scan match | ✅ Done | 🔴 HIGH | Sprint 7: INSERT + service layer |
| 2.2 | Cooldown ป้องกัน log ซ้ำ (≤5 นาที) | ✅ Done | 🔴 HIGH | Sprint 7: Redis TTL 300s verified |
| 2.3 | JWT refresh token / expiry ยาวขึ้น | ✅ Done | 🔴 HIGH | Sprint 8: admin ตั้งค่า expire_hours ผ่าน UI Settings ได้ |
| 2.4 | Anti-spoofing MiniFASNet | ✅ Done | 🟡 MED | Sprint 13: AntiSpoofEngine graceful degradation, enrollment+scan gates |
| 2.5 | Face quality gate ก่อน enrollment | ✅ Done | 🟡 MED | Sprint 12: HTTP 422 reject, threshold configurable |
| 2.6 | Multi-face tracking (Hungarian algorithm) | ✅ Done | 🟢 LOW | Sprint 15c: `scipy.optimize.linear_sum_assignment` — globally optimal |
| 2.7 | ONNX provider auto-detect (CUDA→DirectML→ROCm→CPU) | ✅ Done | 🟢 LOW | Sprint 16: `get_best_provider(override)` + config `onnxruntime_provider=auto` |

---

## Sprint 8 — Auth & Security ✅ DONE

**เป้าหมาย:** ระบบ Auth/Authz ครบถ้วน, SSOT, ป้องกัน endpoint ทุกตัว

| # | งาน | สถานะ | วันที่เสร็จ |
|---|-----|--------|------------|
| S8.1 | User Management + RBAC (users table, bcrypt, roles) | ✅ Done | 2026-05-17 |
| S8.2 | Auth Store SSOT rewrite (expiry check, legacy key cleanup) | ✅ Done | 2026-05-17 |
| S8.3 | GET /auth/me endpoint (server-side session verify) | ✅ Done | 2026-05-17 |
| S8.4 | Axios interceptors (token inject, 401/403 handler, no dup redirect) | ✅ Done | 2026-05-17 |
| S8.5 | Router guards (meta.roles array, expiry-aware isLoggedIn) | ✅ Done | 2026-05-17 |
| S8.6 | SettingsView rewrite (4 groups + JWT expire control) | ✅ Done | 2026-05-17 |
| S8.7 | Login expire_hours from DB system_settings | ✅ Done | 2026-05-17 |
| S8.8 | 13 unprotected endpoints hardened (departments/employees/stations/attendance/enrollment/shifts) | ✅ Done | 2026-05-17 |
| S8.9 | useConfirm composable + ConfirmModal (no native browser dialogs) | ✅ Done | 2026-05-17 |
| S8.10 | DataTable inline button threshold fix (operator1 row) | ✅ Done | 2026-05-17 |
| S8.11 | LoginView session-expired/deactivated banner | ✅ Done | 2026-05-17 |
| S8.12 | AppLayout logout confirm dialog | ✅ Done | 2026-05-17 |
| S8.13 | chapter_22_auth_authorization.md (4 seq diagrams, auth matrix, SSOT design) | ✅ Done | 2026-05-17 |

---

## Sprint 11 — Face Snapshot Evidence ✅ DONE
**วันที่:** 2026-05-18 (Session 8)  
**เป้าหมาย:** บันทึกรูปใบหน้าตอน scan match เป็นหลักฐาน + แสดงใน Attendance page

| # | งาน | สถานะ | วันที่เสร็จ |
|---|-----|--------|------------|
| S11.1 | `snapshot_path` column ใน AttendanceLog ORM | ✅ Done | 2026-05-18 |
| S11.2 | Alembic migration `c3f8a92b1d74` — add snapshot_path | ✅ Done | 2026-05-18 |
| S11.3 | `config.py` — `storage_path` absolute path ด้วย `_PROJECT_ROOT` | ✅ Done | 2026-05-18 |
| S11.4 | `websocket.py` — crop face (25% padding) → JPEG bytes | ✅ Done | 2026-05-18 |
| S11.5 | `attendance_service.py` — save JPEG to `storage/snapshots/{date}/{log_id}.jpg` | ✅ Done | 2026-05-18 |
| S11.6 | `attendance.py` — `snapshot_url` field + `GET /{id}/snapshot` endpoint (HR auth) | ✅ Done | 2026-05-18 |
| S11.7 | `AttendanceView.vue` — SnapshotImg lazy-load thumbnail + fullscreen evidence modal | ✅ Done | 2026-05-18 |
| S11.8 | `main.py` — `logging.getLogger("app").setLevel(INFO)` + mobile CORS origin | ✅ Done | 2026-05-18 |

**ผลลัพธ์:** attendance log id=27 เป็น record แรกที่มี `snapshot_path` (verified บน disk)

---

## Sprint 12 — All Settings Live + AI Gates ✅ DONE
**วันที่:** 2026-05-18 (Session 8 ต่อ)  
**เป้าหมาย:** ทุก setting ใน Settings UI ต้องทำงานจริง + face quality gate + unknown face alert

| # | งาน | สถานะ | วันที่เสร็จ |
|---|-----|--------|------------|
| S12.1 | `main.py` startup — sync ทุก setting จาก DB → Redis (แก้ setting ไม่ทำงาน) | ✅ Done | 2026-05-18 |
| S12.2 | `websocket.py` — `_get_match_threshold()` อ่านจาก Redis แบบ live (ก่อนหน้า hardcoded) | ✅ Done | 2026-05-18 |
| S12.3 | `redis.py` — `get_min_face_quality()`, `increment_unknown_count()`, `get_unknown_alert_threshold()` | ✅ Done | 2026-05-18 |
| S12.4 | `enrollment.py` — face quality gate: reject upload ถ้า score < threshold (HTTP 422) | ✅ Done | 2026-05-18 |
| S12.5 | `websocket.py` — unknown face rolling counter (Redis INCR + 5 min expire) + alert publish | ✅ Done | 2026-05-18 |
| S12.6 | `start-dev.bat` — `taskkill /F /IM python.exe` ก่อน start (ป้องกัน zombie process) | ✅ Done | 2026-05-18 |
| S12.7 | Debug instrumentation cleanup (module marker, file-write diagnostic, print statements) | ✅ Done | 2026-05-18 |

**Settings ที่ทำงานครบแล้ว (8/8):**
| Setting Key | ค่าที่ admin ตั้ง | ทำงานผ่าน |
|-------------|-----------------|---------|
| `access_token_expire_hours` | 8h | DB query ตอน login |
| `match_threshold` | 0.70 | Redis `setting:match_threshold` |
| `min_face_quality` | 0.60 | Redis `setting:min_face_quality` |
| `cooldown_seconds` | 10s | Redis `setting:cooldown_seconds` |
| `unknown_face_alert` | 5 | Redis `setting:unknown_face_alert` |
| `max_fps_per_camera` | 15 | Redis `setting:max_fps_per_camera` |
| `inference_workers` | 2 | Config at startup (restart required) |
| `face_detect_size` | 640 | Config at startup (restart required) |

---

## Phase 3 — HR Features 🔄 IN PROGRESS (80%)

**เป้าหมาย:** รายงาน HR, export, user management

| # | งาน | สถานะ | Priority |
|---|-----|--------|----------|
| 3.1 | Attendance report (daily/monthly summary) | ✅ Done | 🔴 HIGH | Sprint 9: bar chart + dept breakdown |
| 3.2 | Export CSV / Excel | ✅ Done | 🔴 HIGH | Sprint 9: logs CSV + summary CSV |
| 3.3 | Late / Absent detection ตาม Shift | ✅ Done | 🟡 MED | Sprint 13: `GET /attendance/daily-report` + Daily Status tab in AttendanceView |
| 3.4 | User management (multi-user login) | ✅ Done | 🟡 MED | Sprint 8 |
| 3.5 | Dashboard KPI (present %, late %, absent %) | ✅ Done | 🟢 LOW | Sprint 14: `/attendance/kpi` + DashboardView KPI cards + weekly chart |
| 3.6 | Line Notify + Email + Absent alert | ✅ Done | 🟢 LOW | Sprint 16: Line Notify API, SMTP email, absent_alert_service.py (5-min scan) |

---

## Phase 4 — Multi-Camera & Pilot Console ✅ DONE (100%)

**เป้าหมาย:** รองรับกล้องทุกประเภท + ศูนย์ควบคุม Pilot Console

> Architecture Design เสร็จแล้วใน `doc/claude_version/chapter_17_multi_camera_pilot_console.md`  
> ADR-009, ADR-010, ADR-011 บันทึกใน `DECISIONS_LOG.md`

### Sprint 9 — Camera Backend + Pilot Console
| # | งาน | สถานะ | วันที่เสร็จ |
|---|-----|--------|------------|
| 4.1 | `cameras` table + Alembic migration | ✅ Done | 2026-05-17 |
| 4.2 | Camera CRUD API (`/api/v1/cameras`) | ✅ Done | 2026-05-17 |
| 4.3 | อัพเดท WebSocket: รับ `camera_id` parameter | ✅ Done | 2026-05-17 |
| 4.4 | `CameraManager` service (Redis state + FPS tracker) | ✅ Done | 2026-05-17 |
| 4.5 | Pilot Console WebSocket (`/ws/console`) + Redis Pub/Sub | ✅ Done | 2026-05-17 |
| 4.6 | `CamerasView.vue` — camera CRUD frontend | ✅ Done | 2026-05-17 |
| 4.7 | `PilotConsoleView.vue` — real-time monitor + event feed | ✅ Done | 2026-05-17 |
| 4.8 | Heartbeat monitor (background task, 30s timeout) | ✅ Done | 2026-05-17 |

### Sprint 10 — RTSP Agent + Mobile ✅ DONE
| # | งาน | สถานะ | วันที่เสร็จ |
|---|-----|--------|------------|
| 4.9  | `rtsp_agent.py` — IP Camera / CCTV bridge (RTSP → WS) | ✅ Done | 2026-05-18 |
| 4.10 | `backend/agents/.env.example` สำหรับ RTSP agent config | ✅ Done | 2026-05-18 |
| 4.11 | `MobileScanView.vue` — Smartphone full-screen web app | ✅ Done | 2026-05-18 |
| 4.12 | Pause/Resume/set_fps/disconnect (server → all cameras) | ✅ Done | 2026-05-18 |
| 4.13 | `/mobile-scan` standalone route (no AppLayout sidebar) | ✅ Done | 2026-05-18 |
| 4.14 | WebSocket FPS gate per camera (`_last_processed` dict) | ✅ Done | 2026-05-18 |
| 4.15 | ThreadPoolExecutor for face inference (keeps event loop free) | ✅ Done | 2026-05-18 |
| 4.16 | Redis-cached `max_fps_per_camera` — live admin control | ✅ Done | 2026-05-18 |
| 4.17 | camera_id conflict prevention (last-writer-wins) | ✅ Done | 2026-05-18 |
| 4.18 | FaceResult populated with full_name/emp_code/dept_name from DB | ✅ Done | 2026-05-18 |
| 4.19 | ScanView.vue: TOKEN_KEY bug fix + pause/resume overlay | ✅ Done | 2026-05-18 |

---

## Phase 5 — Production 🔄 IN PROGRESS (85%)

**เป้าหมาย:** ระบบพร้อม deploy จริง

### Sprint 13 — Production Docker Stack + Backup System
| # | งาน | สถานะ | วันที่เสร็จ |
|---|-----|--------|------------|
| S13.1 | `backend/Dockerfile` — Python 3.12-slim + pre-download buffalo_l | ✅ Done | 2026-05-18 |
| S13.2 | `nginx/Dockerfile` — multi-stage: build Vue + nginx SSL proxy | ✅ Done | 2026-05-18 |
| S13.3 | `nginx/nginx.conf` — HTTP→HTTPS, WebSocket proxy, security headers | ✅ Done | 2026-05-18 |
| S13.4 | `nginx/generate_self_signed_cert.sh` — dev SSL cert generator | ✅ Done | 2026-05-18 |
| S13.5 | `docker-compose.prod.yml` — full production stack | ✅ Done | 2026-05-18 |
| S13.6 | `.env.prod.example` — template with CHANGE_ME placeholders | ✅ Done | 2026-05-18 |
| S13.7 | Fix `storage` → `./data/storage` bind mount (host-accessible) | ✅ Done | 2026-05-18 |
| S13.8 | Add `insightface_models` named volume (survive rebuild) | ✅ Done | 2026-05-18 |
| S13.9 | Add Qdrant healthcheck + backend `depends_on: qdrant: healthy` | ✅ Done | 2026-05-18 |
| S13.10 | `scripts/backup.sh` — pg_dump + Qdrant snapshot + storage tar (7-day rotation) | ✅ Done | 2026-05-18 |
| S13.11 | `scripts/restore.sh` — full restore from backup date | ✅ Done | 2026-05-18 |
| S13.12 | `scripts/backup.ps1` — Windows PowerShell backup (dev machine) | ✅ Done | 2026-05-18 |
| S13.13 | BUG-002 — orphaned Qdrant vector reconcile script (`backend/scripts/reconcile_qdrant.py`) | ✅ Done | 2026-05-18 |
| S13.14 | Anti-spoofing MiniFASNet — `AntiSpoofEngine` in `face_engine.py` | ✅ Done | 2026-05-18 |
| S13.15 | Anti-spoof gate in `enrollment.py` (HTTP 422) + `websocket.py` (status="spoof") | ✅ Done | 2026-05-18 |
| S13.16 | Late/Absent detection — `GET /attendance/daily-report` + Daily Status tab | ✅ Done | 2026-05-18 |

### Sprint 14 — Performance Testing & Dashboard KPI ✅ DONE
**วันที่:** 2026-05-19 (Session 14)

| # | งาน | สถานะ | วันที่เสร็จ |
|---|-----|--------|------------|
| S14.1 | `backend/scripts/seed_performance.py` — 1,000 employees + 6,000 face vectors | ✅ Done | 2026-05-19 |
| S14.2 | `backend/scripts/load_test.py` — WebSocket camera simulator (p50/p95/p99, CPU/RAM monitor) | ✅ Done | 2026-05-19 |
| S14.3 | Dashboard KPI widgets — Present%, Late% real-time counters + bar chart | ✅ Done | 2026-05-19 |
| S14.4 | Multi-channel notifications — Discord, Telegram, Slack, Line webhooks | ✅ Done | 2026-05-19 |

### Sprint 15 — Structured Logging + RTSP Docker ✅ DONE
**วันที่:** 2026-05-19 (Session 15)

| # | งาน | สถานะ | วันที่เสร็จ |
|---|-----|--------|------------|
| S15.1 | `app/core/logging_config.py` — JSON structured logging, TimedRotatingFileHandler, 7-day retention | ✅ Done | 2026-05-19 |
| S15.2 | `main.py` — `setup_logging(settings.log_dir)` on startup | ✅ Done | 2026-05-19 |
| S15.3 | `backend/agents/Dockerfile` + `docker-compose.rtsp.yml` (overlay pattern) | ✅ Done | 2026-05-19 |

### Sprint 15b — Performance Architecture ✅ DONE
**วันที่:** 2026-05-19 (Session 15 ต่อ)

| # | งาน | สถานะ | วันที่เสร็จ |
|---|-----|--------|------------|
| S15b.1 | AsyncQdrantClient + `search_batch()` — 1 HTTP round-trip for N faces | ✅ Done | 2026-05-19 |
| S15b.2 | `face_detect_size` applied at engine load time (320px fast mode ใช้ได้แล้ว) | ✅ Done | 2026-05-19 |
| S15b.3 | `predict_batch()` anti-spoof — N faces → 1 ONNX call | ✅ Done | 2026-05-19 |
| S15b.4 | `_get_frame_settings()` cache 5s TTL + `asyncio.Lock` (stampede-safe) | ✅ Done | 2026-05-19 |
| S15b.5 | `cv2.imdecode` in executor (unblocks event loop) | ✅ Done | 2026-05-19 |
| S15b.6 | `inference_workers` default 4 (เพิ่มจาก 2) | ✅ Done | 2026-05-19 |

### Sprint 15c — Prometheus Metrics + Tracker ✅ DONE
**วันที่:** 2026-05-19 (Session 15 ต่อ)

| # | งาน | สถานะ | วันที่เสร็จ |
|---|-----|--------|------------|
| S15c.1 | `app/core/metrics.py` — 14 Prometheus metrics (3 histograms + 8 counters + 3 gauges) | ✅ Done | 2026-05-19 |
| S15c.2 | Dynamic `ThreadPoolExecutor` scaling (admin เปลี่ยน `inference_workers` → ไม่ต้อง restart) | ✅ Done | 2026-05-19 |
| S15c.3 | `app/core/tracker.py` rewrite — Hungarian algorithm (`scipy.optimize.linear_sum_assignment`) | ✅ Done | 2026-05-19 |
| S15c.4 | `FaceEngine.warmup()` at startup — ไม่มี first-camera stall อีกต่อไป | ✅ Done | 2026-05-19 |

### Sprint 15d — Load Test Verification + Prometheus Endpoint ✅ DONE
**วันที่:** 2026-05-19 (Session 15 ต่อ)

| # | งาน | สถานะ | วันที่เสร็จ |
|---|-----|--------|------------|
| S15d.1 | `main.py` — `GET /metrics` endpoint (Prometheus text format, `include_in_schema=False`) | ✅ Done | 2026-05-19 |
| S15d.2 | Load test verified: 10 cameras @ 2fps/30s — **0% error rate** ✅ | ✅ Done | 2026-05-19 |
| S15d.3 | `PROJECT_STATUS.md` + `SPRINT_LOG.md` + `CLAUDE.md` synced to Sprint 15d | ✅ Done | 2026-05-19 |

### Sprint 16 — Phase 2/3 Completion ✅ DONE
**วันที่:** 2026-05-19 (Session 16)

| # | งาน | สถานะ | วันที่เสร็จ |
|---|-----|--------|------------|
| S16.1 | `get_best_provider(override)` — CUDA→DirectML→ROCm→CPU fallback + manual override via config | ✅ Done | 2026-05-19 |
| S16.2 | `config.py` — `onnxruntime_provider` default `"auto"` + `/health` exposes active provider | ✅ Done | 2026-05-19 |
| S16.3 | `notification_service.py` — Line Notify API + SMTP Email (asyncio.to_thread) | ✅ Done | 2026-05-19 |
| S16.4 | `absent_alert_service.py` — background scan every 5 min, Redis dedup key per day | ✅ Done | 2026-05-19 |
| S16.5 | `main.py` — seed 6 new settings (line/email/notify_on_absent) + start absent_alert_loop | ✅ Done | 2026-05-19 |
| S16.6 | `SettingsView.vue` — Line Notify + Email (SMTP) fields in Notifications group | ✅ Done | 2026-05-19 |
| S16.7 | Phase 2 → 100%, Phase 3 → 100% ✅ | ✅ Done | 2026-05-19 |

### Sprint 18b — Bug Fixes + Anti-Spoof Analysis ✅ DONE
**วันที่:** 2026-05-20

| # | งาน | สถานะ | วันที่เสร็จ |
|---|-----|--------|------------|
| S18b.1 | BUG-007: `absent_alert_service.py` — `check_in_time` → `timestamp` | ✅ Done | 2026-05-20 |
| S18b.2 | BUG-008: anti-spoof WARNING log เมื่อ reject — วิเคราะห์ mobile JPEG compression | ✅ Done | 2026-05-20 |
| S18b.3 | `.gitignore` — เพิ่ม `logs/` | ✅ Done | 2026-05-20 |

### Sprint 19 — System Info Admin Dashboard ✅ DONE
**วันที่:** 2026-05-20

| # | งาน | สถานะ | วันที่เสร็จ |
|---|-----|--------|------------|
| S19.1 | `backend/app/api/system.py` — `GET /api/v1/system/info` (admin-only, 7 services) | ✅ Done | 2026-05-20 |
| S19.2 | `frontend/src/views/SystemView.vue` — dashboard cards: App, Face Engine, Anti-Spoof, Postgres, Qdrant, Redis, Storage | ✅ Done | 2026-05-20 |
| S19.3 | `router/index.js` — `/system` route (ADMIN only) | ✅ Done | 2026-05-20 |
| S19.4 | `AppLayout.vue` — "System Info" menu item ใน System section | ✅ Done | 2026-05-20 |

### Sprint 20 — 2-Phase Multi-Face Pipeline Redesign ✅ DONE
**วันที่:** 2026-05-20

| # | งาน | สถานะ | วันที่เสร็จ |
|---|-----|--------|------------|
| S20.1 | `websocket.py` — remove async with wrapper from while loop, add `_persist_and_broadcast()` bg task | ✅ Done | 2026-05-20 |
| S20.2 | `attendance_service.py` — `check_and_reserve()` Phase 1 + `persist_attendance_batch()` Phase 2 | ✅ Done | 2026-05-20 |
| S20.3 | `redis.py` — expose `get_cooldown_seconds()` as public | ✅ Done | 2026-05-20 |
| S20.4 | Employee lookup: N concurrent queries → `WHERE id IN (...)` (1 round-trip, thread-safe) | ✅ Done | 2026-05-20 |
| S20.5 | Sync disk write → `run_in_executor(None, write_bytes, data)` | ✅ Done | 2026-05-20 |

### Sprint 20b — Mobile Scan UX Overhaul + Recognition Cache TTL ✅ DONE
**วันที่:** 2026-05-20–21

| # | งาน | สถานะ | วันที่เสร็จ |
|---|-----|--------|------------|
| S20b.1 | MobileScanView.vue — 3-panel layout redesign (wireframe-based) | ✅ Done | 2026-05-21 |
| S20b.2 | Event feed pattern — panel shows only logged/spoof (ตัด Unknown ออก) | ✅ Done | 2026-05-21 |
| S20b.3 | Audio cooldown — fresh 5s / repeat 60s / alert 5s | ✅ Done | 2026-05-21 |
| S20b.4 | Backpressure gate — `_waitingResponse` flag + 2500ms auto-clear timeout | ✅ Done | 2026-05-21 |
| S20b.5 | `_clearBBoxCanvas()` on WS disconnect — no stale bbox on reconnect | ✅ Done | 2026-05-21 |
| S20b.6 | fps display hidden when WS not open (`v-if="wsState === 'open'"`) | ✅ Done | 2026-05-21 |
| S20b.7 | `recognition_cache_ttl` setting — configurable tracker cache (5–300s, default 30s) | ✅ Done | 2026-05-21 |
| S20b.8 | `tracker.get_cached_result(tid, ttl=cache_ttl)` — TTL read from Redis live | ✅ Done | 2026-05-21 |

### Sprint 20c — Team Setup (Magic Onboarding) ✅ DONE
**วันที่:** 2026-05-21

| # | งาน | สถานะ | วันที่เสร็จ |
|---|-----|--------|------------|
| S20c.1 | `setup.bat` — one-click first-time setup (5 steps, full error handling) | ✅ Done | 2026-05-21 |
| S20c.2 | `backend/.env` — committed to git (localhost dev defaults, no real secrets) | ✅ Done | 2026-05-21 |
| S20c.3 | `.gitignore` — unblock backend/.env tracking | ✅ Done | 2026-05-21 |
| S20c.4 | `README.md` — complete rewrite: 4-step quick start, troubleshooting, team workflow | ✅ Done | 2026-05-21 |

### Remaining Production Work
| # | งาน | สถานะ | Priority |
|---|-----|--------|----------|
| 5.3 | Logging & monitoring | ✅ Done (Sprint 15) | — |
| 5.5 | Performance test (10 cameras) | ✅ Done (Sprint 15d) | — |
| 5.9 | rtsp_agent Dockerfile | ✅ Done (Sprint 15) | — |
| 5.10 | Grafana dashboard (visualize Prometheus metrics) | 🔄 In Progress (Sprint 21) | 🟢 LOW |
| 5.11 | System Info admin dashboard | ✅ Done (Sprint 19) | — |
| 5.12 | 2-phase multi-face pipeline | ✅ Done (Sprint 20) | — |
| 5.13 | Team onboarding (setup.bat + README) | ✅ Done (Sprint 20c) | — |

---

## Known Issues 🐛

| ID | ปัญหา | Severity | สถานะ |
|----|-------|----------|-------|
| BUG-001 | JWT token หมดอายุเร็ว — test script fail slot 0 overwrite | Medium | ✅ Fixed Sprint 8: admin-configurable via Settings UI |
| BUG-002 | Orphaned Qdrant vector (7 vectors แทนที่จะเป็น 6) | Low | ✅ Fixed Sprint 13: reconcile_qdrant.py ลบ 4 orphans, collection = 6 |
| BUG-003 | Face detection ล้มเหลวสำหรับรูปขนาดเล็ก 640x480 (biden.jpg แนวตั้ง) | Info | ✅ By Design |
| BUG-004 | `PointIdsList` แทน raw list ใน Qdrant delete — แก้แล้ว | Medium | ✅ Fixed |
| BUG-005 | uvicorn `--reload` Windows zombie process — กระบวนการเก่าถือ port 8000 หลังปิด terminal | High | ✅ Fixed Sprint 12: `taskkill` ใน `start-dev.bat` |
| BUG-006 | Settings ทุกตัว (ยกเว้น `access_token_expire_hours`) ไม่ทำงาน — Redis key ว่างเปล่า | High | ✅ Fixed Sprint 12: startup DB→Redis sync + `_get_match_threshold()` |
| BUG-007 | `AbsentAlertService` crash: `AttendanceLog` has no attribute `check_in_time` | High | ✅ Fixed Sprint 18b: เปลี่ยนเป็น `.timestamp` |
| BUG-008 | Anti-spoof reject ทุก face จาก mobile (score 0.018–0.049) — JPEG compression ทำลาย texture | Medium | ✅ By Design: ปิด anti-spoof สำหรับ mobile scan, เปิดเฉพาะ enrollment |

---

## Decisions Log (สรุป)

| วันที่ | การตัดสินใจ | เหตุผล |
|--------|------------|--------|
| 2026-05-16 | ใช้ InsightFace buffalo_l (ไม่ใช่ ArcFace standalone) | all-in-one: detection + landmark + embedding |
| 2026-05-16 | Qdrant HNSW + SQ8 quantization | RAM ต่ำ, ค้นหาเร็ว, 10k+ employees |
| 2026-05-16 | Redis เก็บ station dept_filter | ไม่ query Postgres ทุก frame |
| 2026-05-16 | 6 face templates ต่อคน | ครอบคลุมมุม/แสงต่างกัน |
| 2026-05-16 | WebSocket binary JPEG (ไม่ใช่ Base64) | ลด overhead ~33% |
| 2026-05-16 | MSVC บน F: drive ใช้ DISTUTILS_USE_SDK=1 | C: drive พื้นที่จำกัด |

---

## Metrics (ผลการทดสอบจริง)

| Metric | ค่าที่ได้ | เป้าหมาย |
|--------|----------|---------|
| Face detection confidence | 99.76% | ≥ 72% |
| Enrollment quality score | 0.799 | ≥ 0.75 |
| WebSocket round-trip | ~10s (cold) / <2s (warm) CPU | < 500ms (GPU) |
| Attendance log insert | ✅ verified (DB: +1 record) | — |
| Cooldown ป้องกัน duplicate | ✅ verified (2nd scan: logged=False) | configurable (default 300s) |
| Face snapshot saved | ✅ verified (id=27, 8468 bytes JPEG) | per match |
| Unknown face alert | ✅ verified (Redis INCR + publish) | threshold configurable |
| Min face quality gate | ✅ verified (HTTP 422 if below threshold) | threshold configurable |
| Settings live reload | ✅ 8/8 settings working (DB→Redis sync) | no restart needed |
| Qdrant collection status | 🟢 green (6 vectors, 0 orphans) | green |
| Anti-spoofing | ✅ framework ready (model required at `models/anti_spoof/`) | graceful degradation |
| Late/Absent detection | ✅ PRESENT/LATE/ABSENT per shift | configurable threshold |
| Production Docker stack | ✅ nginx SSL + backend + postgres + qdrant + redis | `docker-compose.prod.yml` |
| Backup automation | ✅ scripts/backup.sh + backup.ps1 + restore.sh | 7-day rotation |
| API health | ✅ all endpoints 200 | — |
| **Load test (10 cam × 2fps × 30s)** | **error=0.00% ✅  p50=3,023ms  p95=3,547ms  CPU avg=395%  RAM avg=837MB** | error < 5% |
| Prometheus metrics endpoint | ✅ `GET /metrics` — 14 omnisight metrics + python runtime | Grafana-ready |
| Structured JSON logging | ✅ `logs/omnisight.log` daily rotation, 7-day retention | — |
