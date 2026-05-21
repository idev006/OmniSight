# 👁️ OmniSight — AI Face Recognition Attendance System

ระบบลงเวลางานด้วย Face Recognition สำหรับองค์กร, โรงเรียน และงาน Event  
พัฒนาด้วย FastAPI + Vue 3 + InsightFace buffalo_l + Qdrant + PostgreSQL + Redis

---

## ✨ Quick Start (4 Steps)

> ใช้เวลาประมาณ **5–10 นาที** ขึ้นอยู่กับความเร็ว internet

### Step 1 — ติดตั้ง Prerequisites

| ซอฟต์แวร์ | เวอร์ชัน | ลิงก์ดาวน์โหลด |
|-----------|---------|----------------|
| Python | **3.12** | https://www.python.org/downloads/release/python-3120/ (✅ check "Add Python to PATH") |
| Node.js | LTS | https://nodejs.org |
| Docker Desktop | latest | https://www.docker.com/products/docker-desktop |
| Git | any | https://git-scm.com |

### Step 2 — Clone โปรเจกต์

```bash
git clone https://github.com/idev006/OmniSight.git
cd OmniSight
```

### Step 3 — เปิด Docker Desktop แล้วรัน setup

```
setup.bat
```

สคริปต์จะทำทุกอย่างให้อัตโนมัติ:
- ✅ ตรวจสอบ Python 3.12, Node.js, Docker
- ✅ สร้าง Python virtual environment (`my_env/`)
- ✅ ติดตั้ง Python packages (`pip install -r requirements.txt`)
- ✅ เปิด Docker services (PostgreSQL, Qdrant, Redis)
- ✅ รัน database migration (`alembic upgrade head`)
- ✅ ติดตั้ง Node.js packages (`npm install`)

### Step 4 — เริ่มพัฒนา

```
start-dev.bat
```

เปิด browser ไปที่:

| Service | URL |
|---------|-----|
| 🖥️ Frontend | http://localhost:5173 |
| 📖 API Docs (Swagger) | http://localhost:8000/docs |
| 📊 Qdrant Dashboard | http://localhost:6333/dashboard |
| 📈 Grafana Dashboard | http://localhost:3000 (admin / admin) |
| 🔬 Prometheus | http://localhost:9090 |

**Default login:** `admin` / `admin`

---

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.12) + SQLAlchemy async + Alembic |
| AI Engine | InsightFace `buffalo_l` (ONNX Runtime) |
| Anti-Spoofing | MiniFASNet V2 (optional — download separately) |
| Vector DB | Qdrant (HNSW + SQ8 quantization) |
| Cache / Event Bus | Redis (Pub/Sub, cooldown, live settings) |
| SQL Database | PostgreSQL 16 |
| Frontend | Vue 3 + Vite + Tailwind CSS + DaisyUI |
| Production | nginx SSL reverse proxy + Docker Compose |

---

## 📁 Project Structure

```
OmniSight/
├── backend/              # FastAPI app
│   ├── app/
│   │   ├── api/          # Routers (auth, employees, attendance, websocket, …)
│   │   ├── core/         # Face engine, tracker, security, config
│   │   ├── db/           # PostgreSQL, Qdrant, Redis clients
│   │   ├── models/       # SQLAlchemy ORM + Pydantic schemas
│   │   └── services/     # Camera manager, notifications, absent alert
│   ├── alembic/          # Database migrations
│   ├── scripts/          # Utility scripts (load test, seed, model download)
│   └── .env              # Dev environment (localhost defaults — safe to commit)
├── frontend/             # Vue 3 app
│   └── src/
│       ├── views/        # Pages (Dashboard, Employees, MobileScan, …)
│       ├── components/   # Reusable UI components
│       └── stores/       # Pinia stores (auth, camera, …)
├── docker-compose.yml    # Dev services (PostgreSQL + Qdrant + Redis)
├── setup.bat             # ✨ First-time setup (run once)
├── start-dev.bat         # Start backend + frontend
├── migrate.bat           # Run Alembic migrations
└── requirements.txt      # Python dependencies
```

---

## 🛠️ Common Commands

```powershell
# First-time setup (run once)
setup.bat

# Start development servers
start-dev.bat

# Run database migration after pulling new code
migrate.bat upgrade

# Install a new Python package
my_env\Scripts\pip.exe install <package>

# Run a Python script
my_env\Scripts\python.exe backend\scripts\<script>.py

# Stop Docker services
docker compose down
```

---

## 🤝 Team Workflow (Git)

```bash
# 1. Before starting work — always pull latest
git checkout master
git pull origin master

# 2. Create a feature branch
git checkout -b feature/your-feature-name

# 3. Work, commit often
git add .
git commit -m "feat: describe what you did"

# 4. Push and open a Pull Request
git push origin feature/your-feature-name
```

> **หลังจาก pull โค้ดใหม่:** ถ้ามี migration ใหม่ ให้รัน `migrate.bat upgrade` ก่อนเริ่มงาน

---

## ⚙️ Environment Variables

ไฟล์ `backend/.env` เก็บค่า default สำหรับ local development — ปลอดภัยที่จะ commit เพราะไม่มี secret จริง

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://omnisight:omnisight_pass@localhost:5432/omnisight` | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `QDRANT_HOST` | `localhost` | Qdrant host |
| `SECRET_KEY` | *(dev value)* | JWT signing key — **เปลี่ยนใน production!** |
| `ONNXRUNTIME_PROVIDER` | `cpu` | `cpu` \| `cuda` \| `dml` |

สำหรับ **production** ให้ copy `.env.prod.example` → `.env.prod` และใส่ค่าจริง (ห้าม commit ไฟล์นี้)

---

## 🚀 Production Deploy

```bash
# Generate SSL cert (self-signed for internal use)
sh nginx/generate_self_signed_cert.sh

# Configure production env
cp .env.prod.example .env.prod
# แก้ไข .env.prod: ใส่ passwords จริง, SECRET_KEY จริง

# Start production stack
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

---

## 🔧 Troubleshooting

**`setup.bat` ล้มเหลวที่ pip install**
- InsightFace อาจต้องการ Visual C++ Build Tools → ติดตั้ง [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
- หรือรัน `install_insightface_win.bat` แยกต่างหาก

**Port 8000 already in use**
- `start-dev.bat` จะ kill Python process เก่าให้อัตโนมัติ
- ถ้ายังไม่หาย: `taskkill /F /IM python.exe`

**Docker services not starting**
- ตรวจสอบว่า Docker Desktop เปิดอยู่และ WSL 2 backend ทำงานปกติ
- รัน `docker compose down` แล้ว `docker compose up -d` อีกครั้ง

**`alembic upgrade head` ล้มเหลว**
- PostgreSQL อาจยังไม่พร้อม รอ 5–10 วินาทีหลัง `docker compose up -d` แล้วรันใหม่

**Face model ไม่ load**
- ตรวจสอบว่า `models/` มีไฟล์ buffalo_l ครบ หรือรัน: `my_env\Scripts\python.exe backend\scripts\download_models.py`

---

## 📊 Key Features

- 👤 **Face Enrollment** — บันทึกใบหน้า 6 template ต่อคน (multi-angle)
- 🎯 **Real-time Recognition** — WebSocket binary JPEG pipeline, ≤ 500ms latency
- 📹 **Multi-Camera** — รองรับกล้องหลายตัวพร้อมกัน (WebSocket + RTSP bridge)
- 📱 **Mobile Scan** — หน้าสแกนบน smartphone เต็มจอ ไม่มี sidebar
- ⏰ **Attendance Tracking** — Late detection, absent alert, cooldown 5 min
- 🔔 **Notifications** — Discord, Telegram, Slack, Line Notify, Email (SMTP)
- 🛡️ **Anti-Spoofing** — MiniFASNet V2 liveness detection (optional)
- 📈 **Analytics Dashboard** — Present%, Late%, department charts
- 🔐 **Role-based Auth** — ADMIN / HR / OPERATOR

---

*อัปเดตล่าสุด: 2026-05-20 (Sprint 20 — team setup)*
