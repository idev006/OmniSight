# Chapter 17 — Multi-Camera Architecture & Pilot Console

> **วันที่:** 2026-05-17  
> **สถานะ:** Architecture Design (Pre-implementation)  
> **Sprint:** 8 (planned)

---

## 1. ภาพรวม (Overview)

OmniSight ต้องรองรับกล้องหลายประเภทพร้อมกัน ภายใต้แนวคิด:

> **"ทุก Station สามารถมีกล้องได้หลายตัว ทุกประเภท ควบคุมจากศูนย์กลางเดียว"**

### ประเภทกล้องที่รองรับ

| ประเภท | Protocol | Agent | Use Case |
|--------|----------|-------|----------|
| **Browser Webcam** | WebSocket (binary JPEG) | browser JS | HR desk, enrollment station |
| **IP Camera** | RTSP → WebSocket | `rtsp_agent.py` | entrance gate, hallway |
| **CCTV** | RTSP/ONVIF → WebSocket | `rtsp_agent.py` | factory floor, large area |
| **Smartphone (Authorized)** | WebSocket (binary JPEG) | mobile web app | teacher roll call, field check |

---

## 2. Camera & Station Model

### ความสัมพันธ์

```
Organization
└── Station (Location)
    ├── Camera 1 (type: WEBCAM)
    ├── Camera 2 (type: IP_CAMERA, rtsp://...)
    ├── Camera 3 (type: CCTV, rtsp://...)
    └── Camera 4 (type: SMARTPHONE, user: teacher_01)
```

### แนวคิดหลัก

- **Station** = สถานที่ (ทางเข้า, ห้องประชุม, ชั้น 3)
- **Camera** = อุปกรณ์กล้องที่ติดตั้ง ณ สถานที่นั้น
- Station หนึ่งมีกล้องได้ N ตัว
- กล้องแต่ละตัวส่ง frames ผ่าน WebSocket **แยก connection**
- Backend ประมวลผล **แบบขนาน** ทุก connection

---

## 3. System Architecture — Multi-Camera

```mermaid
graph TB
    subgraph Camera Sources
        WC[Browser Webcam<br/>JS WebRTC]
        IP[IP Camera<br/>RTSP stream]
        CC[CCTV<br/>RTSP/ONVIF]
        SM[Smartphone<br/>Mobile Web App]
    end

    subgraph Edge Agents
        BA[Browser Agent<br/>scan.vue]
        RA[RTSP Agent<br/>rtsp_agent.py]
        MA[Mobile Agent<br/>mobile-scan.vue]
    end

    subgraph Backend - FastAPI
        WSS[WebSocket Handler<br/>/ws/scan/{station_id}<br/>?camera_id={id}]
        FE[FaceEngine<br/>buffalo_l ONNX]
        AS[AttendanceService<br/>log + cooldown]
        CM[Camera Manager<br/>Redis registry]
        PC[Pilot Console WS<br/>/ws/console]
    end

    subgraph Storage
        PG[(PostgreSQL<br/>attendance_logs<br/>cameras)]
        QD[(Qdrant<br/>face vectors)]
        RD[(Redis<br/>cooldown<br/>camera status<br/>pub/sub)]
    end

    subgraph Frontend
        PILOT[Pilot Console<br/>Admin UI]
    end

    WC --> BA --> WSS
    IP --> RA --> WSS
    CC --> RA --> WSS
    SM --> MA --> WSS

    WSS --> FE
    FE --> QD
    WSS --> AS
    AS --> PG
    AS --> RD
    WSS --> CM
    CM --> RD

    RD -- pub/sub events --> PC
    PC --> PILOT

    PILOT -- control commands --> PC
    PC -- pause/resume --> WSS
```

---

## 4. WebSocket Protocol Design

### 4.1 Camera → Backend (ทุกประเภทกล้อง)

**Endpoint:**
```
ws://{host}/api/v1/ws/scan/{station_id}?token={jwt}&camera_id={camera_id}
```

**Frame ที่ส่ง:** Binary JPEG bytes (เหมือนเดิม)

**Response จาก Backend (JSON):**
```json
{
  "timestamp": "2026-05-17T10:00:00Z",
  "camera_id": "cam-001",
  "station_id": "ccd829a0-...",
  "faces": [
    {
      "tracking_id": 1,
      "status": "match",
      "employee_id": "db421a76-...",
      "full_name": "สมชาย มีใจดี",
      "dept_name": "วิศวกรรม",
      "confidence": 0.9876,
      "bbox": {"x": 100, "y": 80, "w": 120, "h": 150},
      "attendance_logged": true
    }
  ]
}
```

**Control Message จาก Backend → Camera (สำหรับ Smartphone):**
```json
{"action": "pause"}
{"action": "resume"}
{"action": "set_fps", "fps": 2}
```

### 4.2 Pilot Console → Backend

**Endpoint:**
```
ws://{host}/api/v1/ws/console?token={admin_jwt}
```

**Commands (Admin → Backend):**
```json
{"action": "pause_camera",  "camera_id": "cam-001"}
{"action": "resume_camera", "camera_id": "cam-001"}
{"action": "set_fps",       "camera_id": "cam-001", "fps": 1}
{"action": "disconnect",    "camera_id": "cam-001"}
{"action": "subscribe_station", "station_id": "..."}
```

**Events (Backend → Pilot Console):**
```json
{"event": "camera_connected",    "camera_id": "cam-001", "station_id": "...", "type": "IP_CAMERA"}
{"event": "camera_disconnected", "camera_id": "cam-001"}
{"event": "face_detected",       "camera_id": "cam-001", "employee_id": "...", "full_name": "...", "timestamp": "..."}
{"event": "unknown_face",        "camera_id": "cam-001", "bbox": {...}}
{"event": "attendance_logged",   "camera_id": "cam-001", "employee_id": "...", "full_name": "..."}
{"event": "camera_stats",        "camera_id": "cam-001", "fps": 2.1, "frame_count": 1024}
```

---

## 5. Database Schema — Cameras Table

```sql
CREATE TABLE cameras (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    station_id  UUID NOT NULL REFERENCES stations(id) ON DELETE CASCADE,
    name        VARCHAR(100) NOT NULL,
    camera_type VARCHAR(20)  NOT NULL,  -- WEBCAM | IP_CAMERA | CCTV | SMARTPHONE
    rtsp_url    VARCHAR(500),           -- สำหรับ IP_CAMERA / CCTV
    authorized_user_id UUID,            -- สำหรับ SMARTPHONE (FK → users.id)
    is_active   BOOLEAN DEFAULT TRUE,
    description TEXT,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);
```

**Alembic migration:** เพิ่ม Sprint 8

---

## 6. Redis State Management

```
# Camera registry (ต่อ station)
station:{station_id}:cameras          → SET of camera_ids

# Camera status
camera:{camera_id}:status             → "connected" | "disconnected" | "paused"
camera:{camera_id}:last_seen          → timestamp
camera:{camera_id}:fps                → float (moving average)
camera:{camera_id}:frame_count        → integer

# Pilot Console subscribers
console:subscribers                   → SET of connection_ids

# Pub/Sub channel
channel: omnisight:events             → JSON event messages
```

---

## 7. Camera Agent — RTSP Agent

### rtsp_agent.py

```python
"""
RTSP Camera Agent
รัน script นี้ใกล้กล้อง IP/CCTV เพื่อ relay ภาพไป OmniSight backend
"""
import asyncio
import cv2
import websockets
import json
import os

BACKEND_WS   = os.getenv("OMNISIGHT_WS",  "ws://192.168.1.100:8000")
STATION_ID   = os.getenv("STATION_ID",    "")
CAMERA_ID    = os.getenv("CAMERA_ID",     "")
TOKEN        = os.getenv("OMNISIGHT_TOKEN","")
RTSP_URL     = os.getenv("RTSP_URL",      "")
TARGET_FPS   = int(os.getenv("TARGET_FPS", "2"))

async def run():
    url = f"{BACKEND_WS}/api/v1/ws/scan/{STATION_ID}?token={TOKEN}&camera_id={CAMERA_ID}"
    cap = cv2.VideoCapture(RTSP_URL)

    async with websockets.connect(url, ping_timeout=None) as ws:
        paused = False
        frame_interval = 1.0 / TARGET_FPS

        async def listen():
            nonlocal paused
            async for msg in ws:
                data = json.loads(msg)
                if data.get("action") == "pause":
                    paused = True
                elif data.get("action") == "resume":
                    paused = False

        asyncio.create_task(listen())

        while True:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            if not paused:
                _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                await ws.send(buf.tobytes())

            await asyncio.sleep(frame_interval)

asyncio.run(run())
```

**Docker run:**
```bash
docker run -e RTSP_URL=rtsp://admin:pass@192.168.1.50/stream1 \
           -e STATION_ID=... -e CAMERA_ID=cam-entrance \
           -e OMNISIGHT_TOKEN=... \
           omnisight/rtsp-agent:latest
```

---

## 8. Smartphone Camera — Mobile Web App

### แนวคิด

```
Teacher/Guard opens mobile browser
→ Login (JWT with OPERATOR role + station_id)
→ Mobile Scan page
  ├── Camera live preview
  ├── Status overlay (matched names)
  ├── Stream toggle button (ON/OFF)
  └── Auto-stops when browser background
```

### Stream Toggle Design

```mermaid
sequenceDiagram
    participant Phone as Smartphone
    participant WS as Backend WebSocket
    participant Console as Pilot Console

    Phone->>WS: connect + JWT
    WS->>Console: event: camera_connected (type=SMARTPHONE)
    
    loop Stream Active
        Phone->>WS: binary JPEG frame
        WS->>Phone: JSON result
        WS->>Console: event: face_detected / attendance_logged
    end

    Console->>WS: command: pause_camera (camera_id)
    WS->>Phone: {"action": "pause"}
    Phone-->>WS: (stops sending frames)
    WS->>Console: event: camera_paused

    Console->>WS: command: resume_camera (camera_id)
    WS->>Phone: {"action": "resume"}
    Phone->>WS: (resumes sending frames)
```

---

## 9. Pilot Console — UI Design

### แนวคิด "Pilot Console"

> เหมือน Control Tower หรือ NOC (Network Operations Center) — ผู้ดูแลเห็น **ทุกอย่าง** และ **ควบคุมได้ทุกอย่าง** จากหน้าจอเดียว

### Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  🎯 OmniSight Pilot Console            [●] 12 cameras LIVE  [Admin]│
├──────────────┬───────────────────────────────────────────────────┤
│              │  CAMERA GRID                                        │
│  STATIONS    ├─────────────┬─────────────┬─────────────┐          │
│  ──────────  │ [CAM FEED]  │ [CAM FEED]  │ [CAM FEED]  │          │
│  ● Floor 1   │ Entrance    │ Hall A      │ Meeting Rm  │          │
│    3 cams    │ ▶ 2 FPS     │ ▶ 1 FPS     │ ■ PAUSED   │          │
│              │ 👤 สมชาย   │ ─           │ ─           │          │
│  ● Floor 2   ├─────────────┼─────────────┼─────────────┤          │
│    2 cams    │ [CAM FEED]  │ [CAM FEED]  │ [OFFLINE]   │          │
│              │ Parking     │ Lobby       │ Server Rm   │          │
│  ● Mobile    │ ▶ 2 FPS     │ ▶ 2 FPS     │ ⚠ No signal │          │
│    7 phones  │ ─           │ 👤 มานี    │ ─           │          │
│              └─────────────┴─────────────┴─────────────┘          │
│              │                                                     │
│  ACTIVITY    │  LIVE EVENT FEED                                    │
│  ──────────  │  10:32:15  ✅ สมชาย มีใจดี  — Entrance (99.1%)   │
│  Today       │  10:32:10  ✅ มานี สุขดี    — Lobby (97.8%)       │
│  Present: 87 │  10:31:55  ⚠  Unknown face  — Hall A              │
│  Absent:  13 │  10:31:40  ✅ วิชัย เก่งมาก — Entrance (98.3%)   │
│  Late:     5 │                                                     │
└──────────────┴───────────────────────────────────────────────────┘
```

### Camera Tile Controls (per camera)

```
┌─────────────────────────────────┐
│ [LIVE THUMBNAIL — last frame]   │
│─────────────────────────────────│
│ 📷 Entrance Cam 1   [IP_CAMERA] │
│ 📍 Floor 1 — Main Gate          │
│ ⚡ 2.1 FPS  │ 1,024 frames      │
│─────────────────────────────────│
│ [⏸ Pause] [⚙ Config] [✖ Stop] │
└─────────────────────────────────┘
```

### Global Controls

```
[+ Add Camera]  [Export Today]  [Alert Settings]  [System Health]
```

---

## 10. Camera Manager — Backend Component

### Responsibilities

```python
class CameraManager:
    """
    จัดการ lifecycle ของ camera connections
    - register / deregister cameras
    - track status ใน Redis
    - relay commands ระหว่าง Pilot Console ↔ Camera
    - publish events ไปยัง Pilot Console subscribers
    """
    
    async def register(camera_id, station_id, camera_type, websocket): ...
    async def deregister(camera_id): ...
    async def pause(camera_id): ...       # ส่ง {"action":"pause"} ไป camera
    async def resume(camera_id): ...      # ส่ง {"action":"resume"} ไป camera
    async def publish_event(event: dict): # ส่งไป Redis pub/sub → Pilot Console
    async def get_stats(camera_id) -> dict: ...
```

### State Machine ของ Camera Connection

```mermaid
stateDiagram-v2
    [*] --> Connecting : WebSocket handshake
    Connecting --> Active : connection accepted
    Connecting --> Rejected : invalid token / unauthorized station

    Active --> Paused : command: pause (from Console)
    Active --> Disconnected : network loss / close

    Paused --> Active : command: resume
    Paused --> Disconnected : network loss

    Disconnected --> [*] : cleanup Redis state
```

---

## 11. Implementation Plan

### Sprint 8 — Camera Model + Manager

| Task | ไฟล์ | Priority |
|------|------|----------|
| เพิ่ม `cameras` table + migration | `models/orm.py`, alembic | 🔴 HIGH |
| Camera CRUD API | `api/cameras.py` | 🔴 HIGH |
| อัพเดท WebSocket รับ `camera_id` param | `api/websocket.py` | 🔴 HIGH |
| `CameraManager` service | `services/camera_manager.py` | 🔴 HIGH |
| Pilot Console WebSocket endpoint | `api/console_ws.py` | 🔴 HIGH |

### Sprint 9 — RTSP Agent + Mobile

| Task | ไฟล์ | Priority |
|------|------|----------|
| `rtsp_agent.py` + Docker image | `agents/rtsp_agent.py` | 🔴 HIGH |
| Mobile Scan page (Vue) | `frontend/src/views/MobileScan.vue` | 🔴 HIGH |
| Pause/Resume control ฝั่ง camera | WebSocket protocol | 🟡 MED |
| Smartphone authorization | `api/cameras.py` + JWT claims | 🟡 MED |

### Sprint 10 — Pilot Console UI

| Task | ไฟล์ | Priority |
|------|------|----------|
| PilotConsole.vue — camera grid | `frontend/src/views/PilotConsole.vue` | 🔴 HIGH |
| Live event feed component | `frontend/src/components/EventFeed.vue` | 🔴 HIGH |
| Camera tile + controls | `frontend/src/components/CameraTile.vue` | 🔴 HIGH |
| Attendance stats sidebar | `frontend/src/components/AttendanceStats.vue` | 🟡 MED |
| Station map / tree view | `frontend/src/components/StationTree.vue` | 🟢 LOW |

---

## 12. Security Considerations

| ข้อกังวล | การป้องกัน |
|---------|-----------|
| Unauthorized camera access | JWT token ต้องมี `station_id` ใน claims สำหรับ OPERATOR |
| Smartphone camera spam | Rate limit frames ฝั่ง backend (max 5 FPS ต่อ connection) |
| RTSP credential leak | เก็บ rtsp_url encrypt ใน DB, ไม่ expose ทาง API |
| Pilot Console unauthorized | ADMIN role เท่านั้น, separate JWT scope |
| Camera replay attack | ตรวจ timestamp freshness (frame ไม่เก่ากว่า 5s) |

---

## 13. Scalability Notes

```
Current (MVP):
- 1 backend instance
- All cameras connect to same process
- Redis pub/sub ใน process เดียว

Future (Scale-out):
- Multiple backend instances (behind nginx)
- Redis pub/sub ข้าม instances
- Camera → any backend instance
- Pilot Console รับ events จาก Redis channel
- WebSocket sticky session (nginx ip_hash) หรือ Redis-backed session
```

---

*บันทึกโดย Sr. Software Engineer / System Architect — OmniSight Project*  
*ดูแผน implementation ใน `doc/project_management/SPRINT_LOG.md`*
