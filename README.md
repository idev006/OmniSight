# OmniSight — AI Face Recognition Attendance System

ระบบลงเวลางานด้วย Face Recognition สำหรับองค์กร, โรงเรียน และงาน Event
พัฒนาด้วย FastAPI + Vue 3 + InsightFace + Qdrant + PostgreSQL + Redis

---

## คุณสมบัติหลัก

| Feature | รายละเอียด |
|---------|-----------|
| **Face Recognition** | InsightFace buffalo_l — ความแม่นยำสูง, รองรับใบหน้าไทย |
| **Real-time** | WebSocket binary pipeline, latency < 500ms |
| **Multi-Camera** | รองรับกล้อง WebSocket + RTSP (IP Camera/CCTV) พร้อมกันไม่จำกัด |
| **Mobile Scan** | ใช้สมาร์ทโฟนเป็นกล้องสแกนได้ทันที |
| **Anti-Spoofing** | MiniFASNet V2 liveness detection — ป้องกันการใช้รูปภาพ |
| **PDF Report** | รายงานรายวัน + รายเดือน รองรับภาษาไทย |
| **Monitoring** | Grafana dashboard + Prometheus metrics + auto alerting |
| **Role-based Auth** | ADMIN / HR / OPERATOR |
| **Notifications** | Discord, Telegram, Slack, Line Notify, Email |
| **Backup/Restore** | 7-day rotation, script พร้อมใช้ทั้ง Linux/Windows |

---

## Quick Start (4 ขั้นตอน)

> ใช้เวลาประมาณ **5–10 นาที**

### 1. ติดตั้ง Prerequisites

| ซอฟต์แวร์ | เวอร์ชัน | ลิงก์ |
|-----------|---------|-------|
| Python | **3.12** | https://www.python.org/downloads/release/python-3120/ |
| Node.js | LTS | https://nodejs.org |
| Docker Desktop | latest | https://www.docker.com/products/docker-desktop |
| Git | any | https://git-scm.com |

> Python: ✅ check "Add Python to PATH" ตอนติดตั้ง

### 2. Clone โปรเจกต์

```bash
git clone https://github.com/idev006/OmniSight.git
cd OmniSight
```

### 3. Setup (ครั้งเดียว)

เปิด Docker Desktop ก่อน แล้วรัน:

```
setup.bat
```

สคริปต์จะ:
- ตรวจสอบ Python 3.12, Node.js, Docker
- สร้าง Python virtual environment
- ติดตั้ง packages ทั้งหมด
- เปิด Docker services (PostgreSQL, Qdrant, Redis)
- รัน database migration
- ติดตั้ง Node.js packages

### 4. เริ่มใช้งาน

```
start-dev.bat
```

เปิด browser:

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | http://localhost:5173 | admin / admin |
| API Docs | http://localhost:8000/docs | - |
| Grafana | http://localhost:3000 | admin / admin |
| Qdrant | http://localhost:6333/dashboard | - |

---

## โครงสร้างโปรเจกต์

```
OmniSight/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── api/                # Endpoints (auth, employees, attendance, ws, ...)
│   │   ├── core/               # Face engine, tracker, security, metrics
│   │   ├── db/                 # PostgreSQL, Qdrant, Redis clients
│   │   ├── models/             # SQLAlchemy ORM + Pydantic schemas
│   │   ├── services/           # Camera manager, notifications, absent alert
│   │   └── assets/fonts/       # Leelawadee TTF (Thai font for PDF)
│   ├── alembic/                # Database migrations
│   ├── scripts/                # Utilities (load_test, seed, download_models)
│   ├── tests/
│   │   ├── unit/               # 56 unit tests (security, tracker, config)
│   │   └── integration/        # Integration tests (requires backend running)
│   └── .env                    # Dev config (localhost defaults)
├── frontend/                   # Vue 3 application
│   └── src/
│       ├── views/              # Pages (Dashboard, Employees, Attendance, ...)
│       ├── components/         # UI components
│       └── stores/             # Pinia stores (auth, camera)
├── grafana/
│   └── provisioning/
│       ├── dashboards/         # Auto-provisioned dashboards
│       └── alerting/           # 5 alert rules (auto-provisioned)
├── nginx/                      # Reverse proxy config + SSL
├── scripts/                    # Ops scripts
│   ├── backup.sh / backup.ps1  # Backup (7-day rotation)
│   ├── restore.sh              # Restore from backup
│   └── smoke_test.py           # Production smoke test
├── docs/                       # Documentation
│   ├── USER_GUIDE.md           # คู่มือใช้งาน
│   ├── DEPLOYMENT.md           # คู่มือ deploy production
│   └── API_REFERENCE.md        # API reference
├── docker-compose.yml          # Dev services
├── docker-compose.prod.yml     # Production full stack
├── docker-compose.rtsp.yml     # RTSP camera bridge
├── setup.bat                   # First-time setup
└── start-dev.bat               # Start dev servers
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.12) + SQLAlchemy async + Alembic |
| AI Engine | InsightFace `buffalo_l` (ONNX Runtime) |
| Anti-Spoofing | MiniFASNet V2 |
| Vector DB | Qdrant (HNSW + SQ8 quantization) |
| Cache / Event Bus | Redis (Pub/Sub, cooldown, live settings) |
| SQL Database | PostgreSQL 16 |
| Frontend | Vue 3 + Vite + Tailwind CSS + DaisyUI |
| Monitoring | Prometheus + Grafana |
| Production | nginx SSL + Docker Compose |

---

## คำสั่งที่ใช้บ่อย

```powershell
# First-time setup
setup.bat

# เริ่ม development servers
start-dev.bat

# รัน migration (หลัง pull code ใหม่)
migrate.bat upgrade

# รัน unit tests
my_env\Scripts\pytest backend\tests\unit\ -v

# รัน integration tests (ต้องเปิด backend ก่อน)
my_env\Scripts\pytest backend\tests\integration\ -m integration -v

# Production smoke test
my_env\Scripts\python.exe scripts\smoke_test.py

# ติดตั้ง package ใหม่
my_env\Scripts\pip.exe install <package>

# หยุด Docker services
docker compose down

# ดู logs
docker compose logs -f backend
```

---

## Production Deploy

ดูรายละเอียดใน [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

```bash
# 1. สร้าง SSL cert
sh nginx/generate_self_signed_cert.sh

# 2. ตั้งค่า environment
cp .env.prod.example .env.prod
# แก้ไข .env.prod ใส่ password จริง

# 3. Deploy
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# 4. ยืนยัน
python scripts/smoke_test.py --url https://your-server --insecure
```

---

## เอกสารประกอบ

| เอกสาร | เนื้อหา |
|--------|---------|
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | คู่มือใช้งานสำหรับ HR / Admin / Operator |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | คู่มือ deploy production ทีละขั้นตอน |
| [docs/API_REFERENCE.md](docs/API_REFERENCE.md) | API endpoints, request/response format |
| [CLAUDE.md](CLAUDE.md) | AI Session handover + project status |

---

## Team Workflow

```bash
# 1. Pull latest
git checkout master && git pull origin master

# 2. สร้าง feature branch
git checkout -b feature/your-feature

# 3. พัฒนา + commit
git add <files>
git commit -m "feat: describe your change"

# 4. Push + Pull Request
git push origin feature/your-feature
```

> หลัง pull code ใหม่: รัน `migrate.bat upgrade` ก่อนเริ่มงาน

---

## Environment Variables (Dev)

ไฟล์ `backend/.env` — ค่า default สำหรับ local dev (ปลอดภัยที่จะ commit)

| Variable | Default |
|----------|---------|
| `DATABASE_URL` | `postgresql+asyncpg://omnisight:omnisight_pass@localhost:5432/omnisight` |
| `REDIS_URL` | `redis://localhost:6379/0` |
| `QDRANT_HOST` | `localhost` |
| `SECRET_KEY` | dev value |
| `ONNXRUNTIME_PROVIDER` | `cpu` |

Production: ใช้ `.env.prod` — ดู [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

---

## Troubleshooting

**`setup.bat` ล้มเหลวที่ pip install InsightFace**
→ ติดตั้ง [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) แล้วรันใหม่

**Port 8000 already in use**
→ `start-dev.bat` kill Python process เก่าให้อัตโนมัติ
→ ถ้ายังไม่หาย: `taskkill /F /IM python.exe`

**Docker services ไม่ start**
→ ตรวจสอบว่า Docker Desktop เปิดอยู่
→ รัน `docker compose down` แล้ว `docker compose up -d`

**alembic upgrade ล้มเหลว**
→ PostgreSQL อาจยังไม่พร้อม รอ 10 วินาที แล้วรันใหม่

**Face model ไม่ load**
→ `my_env\Scripts\python.exe backend\scripts\download_models.py`

---

*อัปเดตล่าสุด: 2026-05-21 (Sprint 24 — Phase 5 Complete)*
