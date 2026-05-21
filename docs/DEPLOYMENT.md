# คู่มือ Deploy OmniSight สู่ Production

> สำหรับ System Administrator / DevOps

---

## สารบัญ

1. [Requirements](#1-requirements)
2. [Architecture Overview](#2-architecture-overview)
3. [ขั้นตอน Deploy (Step-by-Step)](#3-ขั้นตอน-deploy-step-by-step)
4. [RTSP Camera (IP Camera / CCTV)](#4-rtsp-camera-ip-camera--cctv)
5. [Monitoring (Grafana + Prometheus)](#5-monitoring-grafana--prometheus)
6. [Backup & Restore](#6-backup--restore)
7. [Smoke Test](#7-smoke-test)
8. [Troubleshooting](#8-troubleshooting)
9. [Security Checklist](#9-security-checklist)

---

## 1. Requirements

### Hardware (ขั้นต่ำ)

| Component | Spec |
|-----------|------|
| CPU | 4 cores (Intel/AMD 64-bit) |
| RAM | 8 GB |
| Disk | 50 GB SSD (ขึ้นกับจำนวนพนักงานและ snapshot) |
| OS | Ubuntu 22.04 LTS / Windows Server 2019+ / Debian 12 |

### Hardware (แนะนำ สำหรับ 10+ กล้อง)

| Component | Spec |
|-----------|------|
| CPU | 8+ cores |
| RAM | 16 GB |
| Disk | 200 GB SSD |
| GPU | NVIDIA (optional) — เพิ่มความเร็ว inference 3–5× |

### Software

| Software | เวอร์ชัน | หมายเหตุ |
|---------|---------|---------|
| Docker | 24+ | [ติดตั้ง Docker Engine](https://docs.docker.com/engine/install/) |
| Docker Compose | 2.x | มากับ Docker Desktop |
| Git | any | |

> **Windows:** ใช้ Docker Desktop + WSL 2 backend

---

## 2. Architecture Overview

```
Internet / LAN
      │
      ▼
 ┌──────────┐
 │  nginx   │  :443 (HTTPS)  ←─ SSL termination
 └────┬─────┘
      │
      ├──→ Frontend (Vue 3)       :5173 (internal)
      │
      └──→ Backend API (FastAPI)  :8000 (internal)
               │
               ├──→ PostgreSQL    :5432
               ├──→ Qdrant        :6333
               ├──→ Redis         :6379
               └──→ Prometheus    :9090
                        │
                        └──→ Grafana :3000
```

**Port ที่ต้อง expose:**

| Port | Service | เปิดสู่ภายนอก? |
|------|---------|--------------|
| 443 | nginx (HTTPS) | ✅ ใช่ |
| 80 | nginx (HTTP redirect) | ✅ ใช่ (redirect → 443) |
| 8000 | Backend API | ❌ ปิด (ผ่าน nginx เท่านั้น) |
| 3000 | Grafana | ⚠️ optional (แนะนำให้เข้าผ่าน VPN) |
| 5432/6333/6379 | DB services | ❌ ปิดทั้งหมด |

---

## 3. ขั้นตอน Deploy (Step-by-Step)

### Step 1 — Clone โปรเจกต์

```bash
git clone https://github.com/idev006/OmniSight.git
cd OmniSight
```

### Step 2 — สร้าง SSL Certificate

**ตัวเลือก A: Self-signed (สำหรับ internal network)**

```bash
sh nginx/generate_self_signed_cert.sh
```

**ตัวเลือก B: Let's Encrypt (ต้องมี domain name)**

```bash
# ติดตั้ง certbot
sudo apt install certbot

# ขอ certificate
sudo certbot certonly --standalone -d your-domain.com

# copy ไฟล์ไปที่ nginx/ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/key.pem
```

### Step 3 — ตั้งค่า Environment

```bash
cp .env.prod.example .env.prod
nano .env.prod   # หรือ editor ที่ถนัด
```

แก้ไข **ทุกค่า** ที่ขึ้นต้นด้วย `CHANGE_ME_`:

```env
# PostgreSQL
POSTGRES_PASSWORD=ใส่_password_ที่_แข็งแรง_ที่นี่

# Redis
REDIS_PASSWORD=ใส่_password_redis_ที่นี่

# JWT Secret — generate ด้วย:
# python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=ใส่_secret_key_64_ตัวอักษรที่นี่

# Grafana
GRAFANA_PASSWORD=ใส่_password_grafana_ที่นี่
```

> ⚠️ **ห้าม commit ไฟล์ `.env.prod`** — มันอยู่ใน `.gitignore` แล้ว

### Step 4 — Download AI Models

```bash
# ดาวน์โหลด InsightFace buffalo_l (ครั้งแรกอาจใช้เวลา 5–10 นาที)
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm backend \
  python scripts/download_models.py
```

### Step 5 — Start Production Stack

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

ตรวจสอบว่า container ทั้งหมดรัน:

```bash
docker compose -f docker-compose.prod.yml ps
```

ผลลัพธ์ที่ต้องการ:

```
NAME                  STATUS    PORTS
omnisight_postgres    Up
omnisight_qdrant      Up
omnisight_redis       Up
omnisight_backend     Up
omnisight_nginx       Up        0.0.0.0:443->443/tcp
omnisight_grafana     Up        0.0.0.0:3000->3000/tcp
omnisight_prometheus  Up
```

### Step 6 — Run Database Migration

```bash
docker compose -f docker-compose.prod.yml exec backend \
  alembic upgrade head
```

### Step 7 — ยืนยัน Deploy สำเร็จ

```bash
# Smoke test
python scripts/smoke_test.py --url https://your-server --insecure

# หรือถ้ามี domain
python scripts/smoke_test.py --url https://your-domain.com
```

ผลที่ต้องการ:
```
[PASS] GET /health -> 200 + status=ok
[PASS] GET /metrics -> 200 + omnisight_ metrics
[PASS] POST /auth/login -> token received
...
All checks passed [OK]
```

---

## 4. RTSP Camera (IP Camera / CCTV)

ใช้ **RTSP Bridge** สำหรับกล้อง IP Camera หรือ CCTV ที่รองรับ RTSP protocol

### 4.1 ตรวจสอบ RTSP URL

ทดสอบ RTSP URL ด้วย VLC หรือ ffplay:

```bash
ffplay rtsp://admin:password@192.168.1.100:554/stream1
```

### 4.2 Start RTSP Agent

```bash
# แก้ไข RTSP_URL ในคำสั่ง
docker compose -f docker-compose.rtsp.yml up -d \
  -e RTSP_URL="rtsp://admin:password@192.168.1.100:554/stream1" \
  -e WS_URL="ws://localhost:8000/ws/camera" \
  -e STATION_ID="your-station-id" \
  -e CAMERA_ID="cctv-front-door"
```

### 4.3 รัน RTSP Agent หลายกล้อง

สร้างไฟล์ `docker-compose.cameras.yml`:

```yaml
version: '3.8'
services:
  rtsp-cam1:
    image: omnisight-rtsp
    environment:
      RTSP_URL: rtsp://admin:pass@192.168.1.101:554/stream1
      WS_URL: ws://backend:8000/ws/camera
      STATION_ID: sta1
      CAMERA_ID: cam-front

  rtsp-cam2:
    image: omnisight-rtsp
    environment:
      RTSP_URL: rtsp://admin:pass@192.168.1.102:554/stream1
      WS_URL: ws://backend:8000/ws/camera
      STATION_ID: sta1
      CAMERA_ID: cam-back
```

```bash
docker compose -f docker-compose.cameras.yml up -d
```

---

## 5. Monitoring (Grafana + Prometheus)

### 5.1 เข้าใช้ Grafana

```
http://your-server:3000
Username: admin
Password: [GRAFANA_PASSWORD ใน .env.prod]
```

### 5.2 Dashboard ที่มีให้

| Dashboard | ข้อมูลที่แสดง |
|-----------|------------|
| OmniSight Overview | Frames/sec, Error rate, Active cameras |
| AI Performance | Inference latency p50/p95/p99 |
| Qdrant Search | Search latency, Vector count |
| System | CPU, RAM, Disk |

### 5.3 Alert Rules (Auto-provisioned)

ระบบตั้งค่า alert อัตโนมัติเมื่อ:

| Alert | เงื่อนไข | Severity |
|-------|---------|---------|
| Frame Error Rate | > 1% นาน 5 นาที | Warning |
| No Active Cameras | กล้องทั้งหมด disconnect นาน 2 นาที | **Critical** |
| Inference Latency | p95 > 3 วินาที นาน 5 นาที | Warning |
| Qdrant Latency | p95 > 500ms นาน 5 นาที | Warning |
| Cache Hit Rate | < 20% นาน 10 นาที | Info |

### 5.4 ตั้งค่า Notification Channel

1. Grafana → **Alerting → Contact points**
2. กด **"+ Add contact point"**
3. เลือก type: Email / Slack / Telegram / Discord
4. ตั้งค่าตามแต่ละ service

---

## 6. Backup & Restore

### 6.1 Backup (อัตโนมัติ)

ตั้ง cron job รัน backup ทุกคืน:

**Linux:**
```bash
# เพิ่มใน crontab (crontab -e)
0 2 * * * cd /path/to/OmniSight && bash scripts/backup.sh
```

**Windows (Task Scheduler):**
```powershell
# สร้าง scheduled task รัน backup.ps1 เวลา 02:00 น.
New-ScheduledTask ...  # หรือใช้ Task Scheduler GUI
```

### 6.2 Manual Backup

```bash
# Linux
bash scripts/backup.sh

# Windows
powershell -File scripts\backup.ps1
```

ไฟล์ backup จะอยู่ที่ `backups/YYYY-MM-DD_HH-MM/` ประกอบด้วย:
- `postgres_dump.sql.gz` — ข้อมูล database ทั้งหมด
- `qdrant_snapshot.tar.gz` — vectors ทั้งหมด
- `storage.tar.gz` — ไฟล์ snapshot รูปภาพ

### 6.3 Restore

```bash
# Linux
bash scripts/restore.sh backups/2026-05-21_02-00/

# Windows
powershell -File scripts\restore.ps1 backups\2026-05-21_02-00\
```

> ⚠️ **Restore จะ overwrite ข้อมูลปัจจุบัน** — ทำเฉพาะเมื่อจำเป็น

### 6.4 Retention Policy

Script ลบ backup เก่ากว่า **7 วัน** อัตโนมัติ
เปลี่ยนได้ใน `scripts/backup.sh` บรรทัด `RETENTION_DAYS=7`

---

## 7. Smoke Test

ทดสอบหลัง deploy และหลัง maintenance ทุกครั้ง:

```bash
# Dev
python scripts/smoke_test.py

# Production (self-signed cert)
python scripts/smoke_test.py \
  --url https://your-server \
  --user admin \
  --password your_admin_password \
  --insecure

# Production (valid cert)
python scripts/smoke_test.py \
  --url https://your-domain.com \
  --user admin \
  --password your_admin_password
```

### Checks ที่รัน

| Check | ผ่านเมื่อ |
|-------|---------|
| GET /health | status = "ok" |
| GET /metrics | มี `omnisight_` metrics |
| Auth | login ได้รับ token |
| GET /employees | ได้ list |
| GET /attendance/kpi | มี date/today/weekly/by_dept |
| GET /attendance/daily-report/pdf | ได้ PDF bytes |
| GET /settings | ได้ list |
| GET /stations | ได้ list |
| GET /departments | ได้ list |

---

## 8. Troubleshooting

### Container ไม่ Start

```bash
# ดู logs
docker compose -f docker-compose.prod.yml logs backend
docker compose -f docker-compose.prod.yml logs postgres
```

**กรณีที่พบบ่อย:**

| อาการ | สาเหตุ | แก้ไข |
|-------|--------|-------|
| `port already in use` | Port ซ้ำกับ service อื่น | เปลี่ยน port ใน `.env.prod` |
| `password authentication failed` | Password ใน `.env.prod` ไม่ตรง | ตรวจสอบ POSTGRES_PASSWORD |
| `no such file: nginx/ssl/cert.pem` | ยังไม่ได้สร้าง SSL cert | รัน `generate_self_signed_cert.sh` ก่อน |
| Backend crash loop | Model ไม่พบ | รัน `download_models.py` |

### Performance ช้า

1. ดู Grafana → inference latency
2. เพิ่ม `inference_workers` ใน Settings UI (ไม่ต้อง restart)
3. ถ้า CPU > 80% ตลอด → เพิ่ม server หรือใช้ GPU

### Disk เต็ม

```bash
# ดูขนาด storage
du -sh data/storage/

# ลบ snapshot เก่า (เก็บแค่ 30 วัน)
find data/storage/ -name "*.jpg" -mtime +30 -delete
```

---

## 9. Security Checklist

ก่อน go-live ตรวจสอบทุกข้อ:

- [ ] เปลี่ยน `POSTGRES_PASSWORD` จาก default
- [ ] เปลี่ยน `REDIS_PASSWORD` จาก default
- [ ] ตั้ง `SECRET_KEY` เป็น random 64 chars
- [ ] เปลี่ยน `GRAFANA_PASSWORD` จาก default
- [ ] เปลี่ยน admin password ใน OmniSight UI (`admin/admin`)
- [ ] ใช้ SSL certificate จริง (ไม่ใช่ self-signed สำหรับ internet-facing)
- [ ] ปิด port 3000 (Grafana) จาก internet — เข้าได้แค่ VPN
- [ ] ตั้ง firewall: เปิดแค่ 80 และ 443 จาก internet
- [ ] ตั้ง backup schedule (cron)
- [ ] ทดสอบ restore จาก backup อย่างน้อย 1 ครั้ง
- [ ] รัน smoke test ผ่านทุกข้อ

---

*อัปเดตล่าสุด: 2026-05-21 (Sprint 24)*
