# OmniSight — Project Status Dashboard

> **อัปเดตล่าสุด:** 2026-05-18 (Sprint 10 Multi-Camera plug-and-play done)  
> **Project Manager / Lead Dev:** idev006  
> **AI Pair:** Claude Sonnet 4.6  
> **Repository:** https://github.com/idev006/OmniSight  

---

## Overall Progress

```
Phase 1 — Foundation     ████████████████████ 100%  ✅ DONE
Phase 2 — AI Core        ████████████░░░░░░░░  60%  🔄 IN PROGRESS
Phase 3 — HR Features    ████████████░░░░░░░░  60%  🔄 IN PROGRESS
Phase 4 — Multi-Camera   ████████████████░░░░  80%  🔄 IN PROGRESS
Phase 5 — Production     ░░░░░░░░░░░░░░░░░░░░   0%  ⏳ PENDING
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

## Phase 2 — AI Core 🔄 IN PROGRESS (20%)

**เป้าหมาย:** ระบบ recognition เต็มรูปแบบ + attendance logging อัตโนมัติ

| # | งาน | สถานะ | Priority | หมายเหตุ |
|---|-----|--------|----------|---------|
| 2.1 | Attendance auto-logging เมื่อ scan match | ✅ Done | 🔴 HIGH | Sprint 7: INSERT + service layer |
| 2.2 | Cooldown ป้องกัน log ซ้ำ (≤5 นาที) | ✅ Done | 🔴 HIGH | Sprint 7: Redis TTL 300s verified |
| 2.3 | JWT refresh token / expiry ยาวขึ้น | ✅ Done | 🔴 HIGH | Sprint 8: admin ตั้งค่า expire_hours ผ่าน UI Settings ได้ |
| 2.4 | Anti-spoofing MiniFASNet | ⬜ Todo | 🟡 MED | เพิ่มหลัง attendance log เสร็จ |
| 2.5 | Face quality gate ก่อน enrollment | ⬜ Todo | 🟡 MED | reject blur/dark images |
| 2.6 | Multi-face tracking (ByteTrack) | ⬜ Todo | 🟢 LOW | กรณีกล้องเห็นหลายคน |
| 2.7 | ONNX provider auto-detect (CUDA/DML) | ⬜ Todo | 🟢 LOW | ตอนนี้ fixed เป็น CPU |

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

## Phase 3 — HR Features ⏳ PENDING

**เป้าหมาย:** รายงาน HR, export, user management

| # | งาน | สถานะ | Priority |
|---|-----|--------|----------|
| 3.1 | Attendance report (daily/monthly summary) | ✅ Done | 🔴 HIGH | Sprint 9: bar chart + dept breakdown |
| 3.2 | Export CSV / Excel | ✅ Done | 🔴 HIGH | Sprint 9: logs CSV + summary CSV |
| 3.3 | Late / Absent detection ตาม Shift | ⬜ Todo | 🟡 MED |
| 3.4 | User management (multi-user login) | ✅ Done | 🟡 MED | Sprint 8 |
| 3.5 | Dashboard KPI (present %, late %) | ⬜ Todo | 🟢 LOW |
| 3.6 | Email/Line notification เมื่อ absent | ⬜ Todo | 🟢 LOW |

---

## Phase 4 — Multi-Camera & Pilot Console 📐 DESIGNED

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

## Phase 5 — Production ⏳ PENDING

**เป้าหมาย:** ระบบพร้อม deploy จริง

| # | งาน | สถานะ | Priority |
|---|-----|--------|----------|
| 5.1 | Docker production compose (nginx + SSL) | ⬜ Todo | 🔴 HIGH |
| 5.2 | Strong SECRET_KEY + env hardening | ⬜ Todo | 🔴 HIGH |
| 5.3 | Logging & monitoring (structured logs) | ⬜ Todo | 🟡 MED |
| 5.4 | Backup strategy (Postgres + Qdrant) | ⬜ Todo | 🟡 MED |
| 5.5 | Performance test (1000 employees, 10+ cameras) | ⬜ Todo | 🟡 MED |
| 5.6 | README.md สำหรับ GitHub | ⬜ Todo | 🟢 LOW |
| 5.7 | CLAUDE.md สำหรับ AI session ถัดไป | ⬜ Todo | 🟢 LOW |

---

## Known Issues 🐛

| ID | ปัญหา | Severity | สถานะ |
|----|-------|----------|-------|
| BUG-001 | JWT token หมดอายุเร็ว — test script fail slot 0 overwrite | Medium | ✅ Fixed Sprint 8: admin-configurable via Settings UI |
| BUG-002 | Orphaned Qdrant vector (7 vectors แทนที่จะเป็น 6) | Low | 🟡 Open |
| BUG-003 | Face detection ล้มเหลวสำหรับรูปขนาดเล็ก 640x480 (biden.jpg แนวตั้ง) | Info | ✅ By Design |
| BUG-004 | `PointIdsList` แทน raw list ใน Qdrant delete — แก้แล้ว | Medium | ✅ Fixed |

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
| Cooldown ป้องกัน duplicate | ✅ verified (2nd scan: logged=False) | 5 min |
| Qdrant collection status | 🟢 green | green |
| API health | ✅ all endpoints 200 | — |
