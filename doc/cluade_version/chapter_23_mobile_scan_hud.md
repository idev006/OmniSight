# Chapter 23 — Mobile Scan: HUD Design & Smartphone Camera Agent

> **สถานะ:** ✅ Implemented (Sprint 10–11, 2026-05-18)  
> **ไฟล์หลัก:** `frontend/src/views/MobileScanView.vue`  
> **Route:** `/mobile-scan` (standalone, no AppLayout sidebar)

---

## 1. บริบท (Context)

### ปัญหาที่ต้องการแก้

OmniSight ต้องการ camera node ที่ยืดหยุ่น — ไม่ใช่ทุก gate จะมี PC ตั้งอยู่  
OPERATOR (รปภ. / เจ้าหน้าที่หน้าประตู) ต้องการ device ที่:
- พกพาได้
- ราคาถูก / มีอยู่แล้ว
- ติดตั้งง่าย ไม่ต้อง configure

**คำตอบ:** สมาร์ทโฟน + browser = ready-to-use camera agent ทันที

---

## 2. ปรัชญาและแนวคิด

### "Smartphone as a Camera Agent"

```
ทุกคนมีสมาร์ทโฟน → ไม่ต้องลงทุน hardware
เปิด URL ได้เลย   → ไม่ต้อง install app
กล้องหลัง HD      → ความละเอียดดีกว่า webcam ราคาเดียวกัน
4G/WiFi portable  → ย้าย gate ได้ง่าย
```

### "Heads-Up Display (HUD)"

OPERATOR ต้องทำงานหลายอย่างพร้อมกัน:
- พูดคุยกับคนที่เดินผ่าน
- เปิด/ปิดประตู  
- ตรวจสอบสิ่งของ

**ข้อสรุป:** UI ต้องสื่อสารผลลัพธ์ *โดยไม่ต้องให้ operator จ้องหน้าจอ*

---

## 3. User Persona Analysis

| มิติ | รายละเอียด |
|------|-----------|
| **ตำแหน่ง** | OPERATOR — รปภ., เจ้าหน้าที่ gate, พนักงาน HR |
| **Tech skill** | ต่ำ — ใช้มือถือพื้นฐานได้ |
| **สภาพแวดล้อม** | กลางแจ้ง / โรงงาน / ล็อบบี้ — แสงแปรปรวน |
| **ท่าทาง** | มือเดียวถือมือถือ อีกมือทำงานอื่น |
| **สายตา** | ไม่ได้จ้องหน้าจอตลอด |
| **Session** | 2–8 ชั่วโมงต่อวัน (ตลอดกะ) |
| **ความคาดหวัง** | "มันทำงานเอง ฉันแค่ถือ" |

### Jobs-to-be-Done

> "เมื่อฉันยืนอยู่ที่ประตู ฉันต้องการ **รู้ทันทีโดยไม่ต้องมองหน้าจอ** ว่าคนที่เดินผ่านคือใคร  
> และได้รับ **สัญญาณเตือนทันที** เมื่อมีคนไม่รู้จัก"

---

## 4. Pain Points ของ Version เดิม

| ปัญหา | ผลกระทบ | Severity |
|-------|---------|----------|
| หน้าจอดับใน 30 วินาที | ต้องแตะหน้าจอตลอด = ใช้งานจริงไม่ได้ | 🔴 Critical |
| ไม่มีเสียง | ต้องจ้องหน้าจอ = ทำงานอื่นไม่ได้ | 🔴 Critical |
| Result card เล็ก | กลางแดดอ่านไม่เห็น | 🟡 High |
| Unknown face เงียบ | รปภ.ไม่รู้ว่ามีคนแปลกหน้า | 🟡 High |
| Beep spam | เสียง beep ซ้ำๆ ทุก frame ของคนเดิม | 🟡 High |

---

## 5. System / Architecture Design

### Data Flow

```
สมาร์ทโฟน (camera)
        │
        │  binary JPEG @ 2fps  (WebSocket)
        ▼
Backend → Face Engine (ONNX) → Qdrant search
        │
        │  JSON {faces: [{tracking_id, status, full_name, ...}]}
        ▼
MobileScanView.vue
        │
        ├─ Wake Lock API      (screen stays on)
        ├─ Web Audio API      (beep tones)
        ├─ SpeechSynthesis    (TTS ชื่อพนักงาน)
        ├─ Navigator.vibrate  (tactile alert)
        └─ HUD Overlay        (large result card)
```

### Browser APIs ที่ใช้ (ทั้งหมด native, ไม่มี dependency เพิ่ม)

| API | Browser Support | ใช้ทำ |
|-----|----------------|-------|
| `Screen Wake Lock API` | Chrome 84+, iOS 16.4+ | กันหน้าจอดับ |
| `Web Audio API` | ทุก browser | beep tones |
| `SpeechSynthesis API` | Chrome, iOS Safari | พูดชื่อพนักงาน TH |
| `Navigator.vibrate()` | Android Chrome | สั่นเมื่อ unknown |
| `MediaDevices.getUserMedia` | ทุก browser (HTTPS/localhost) | เปิดกล้อง |

### Recognition Result State Machine

```
receive {faces} from WebSocket
        │
        ├─ faces = []
        │       └─ clear unknown overlay (match auto-dismisses)
        │
        ├─ face.status = 'match'
        │       ├─ attendance_logged = true
        │       │       ├─ beep 880Hz 0.12s
        │       │       ├─ TTS: "{full_name}"
        │       │       └─ Green HUD card (auto-dismiss 2.5s)
        │       └─ attendance_logged = false  (cooldown — already logged today)
        │               ├─ soft beep 660Hz 0.08s (acknowledge only)
        │               └─ Green HUD card (auto-dismiss 2.5s)
        │
        └─ face.status = 'unknown'
                ├─ double beep 220Hz 0.35s × 2
                ├─ vibrate [200, 100, 200]
                └─ Red HUD card (stays until faces = [])
```

### Audio Cooldown per Tracking ID

```
_audioCooldown: Map<tracking_id, timestamp_ms>
TTL: 3000ms

ก่อน play audio → ตรวจ cooldown
  if (now - lastPlayed < 3000ms) → skip
  else → play + update timestamp

เหตุผล: backend ส่ง result ทุก 0.5s (2fps)
         ถ้าคนหยุดอยู่หน้ากล้อง 5 วินาที = 10 results
         โดยไม่มี cooldown = beep 10 ครั้งสำหรับคนคนเดียว
```

### Wake Lock Strategy

```javascript
// Acquire: เมื่อกด Start
wakeLock = await navigator.wakeLock.request('screen')

// Re-acquire: เมื่อ tab กลับมา visible (OS อาจ release ระหว่าง background)
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible' && streaming) acquireWakeLock()
})

// Release: เมื่อกด Stop หรือ component unmount
await wakeLock.release()
```

---

## 6. UI/UX Design

### Layout: Heads-Up Display

```
┌─────────────────────────────────┐
│  ● Live    [Station Name]  ☀️   │  ← top HUD bar (semi-transparent)
│                                 │
│         [ VIDEO FEED ]          │
│                                 │
│   ╔═════════════════════════╗   │
│   ║  ✅  สมชาย ใจดี          ║   │  ← Result overlay (center, large)
│   ║      Engineering        ║   │     match = green, unknown = red
│   ║  EMP-0042    99.1%      ║   │
│   ║       ✓ Logged          ║   │
│   ╚═════════════════════════╝   │
│                                 │
├─────────────────────────────────┤
│  [🔄] [      ■ STOP      ] [🔊] │  ← control bar
│  0 frames        Last: สมชาย   │
└─────────────────────────────────┘
```

### Result Overlay — 2 States

**MATCH (สีเขียว)** — auto-dismiss หลัง 2.5 วินาที
- Background: `rgba(22,163,74,0.92)` + `backdrop-filter: blur(8px)`
- ชื่อ: `clamp(22px, 6vw, 32px) font-black` — อ่านได้กลางแดด
- แสดง: ✅ icon, ชื่อ, แผนก, รหัสพนักงาน, confidence, สถานะ logged

**UNKNOWN (สีแดง)** — ค้างจนใบหน้าออกจากกล้อง
- Background: `rgba(220,38,38,0.92)` + blur
- แสดง: ⚠️ animate-pulse, "ใบหน้าไม่รู้จัก", "กรุณาตรวจสอบ"

### Typography — Outdoor Readable

| Element | Size | เหตุผล |
|---------|------|--------|
| ชื่อพนักงาน | `clamp(22px, 6vw, 32px)` | อ่านได้จาก 50cm กลางแสง |
| แผนก | `clamp(14px, 4vw, 18px)` | secondary info |
| confidence | `14px monospace` | admin reference only |

### Audio Design

| เหตุการณ์ | เสียง | Freq | Duration | เหตุผล |
|-----------|-------|------|----------|--------|
| Match (new) | Beep + TTS ชื่อ | 880 Hz | 0.12s | บอกว่า "ผ่านได้" + ใคร |
| Match (cooldown) | Soft beep | 660 Hz | 0.08s | acknowledge เงียบๆ |
| Unknown | Double low beep | 220 Hz | 0.35s × 2 | เตือน "หยุดตรวจ" |
| (ทั้งหมด) | Vibrate | — | [200,100,200] | tactile สำหรับ unknown |

### Controls

| Element | หน้าที่ |
|---------|--------|
| 🔄 Flip button | สลับ front/rear camera (disabled ระหว่าง stream) |
| ▶ Start / ■ Stop | เริ่ม/หยุด stream + wake lock |
| 🔊 Audio toggle | เปิด/ปิดเสียง (สำหรับ environment ที่ต้องการเงียบ) |
| ☀️ badge | แสดงว่า Wake Lock active |

---

## 7. Edge Cases

| กรณี | การจัดการ |
|------|----------|
| Browser block autoplay audio | `AudioContext` init หลัง user กด Start (user gesture required) |
| iOS Wake Lock < 16.4 | graceful fallback — ไม่ crash, ไม่ show ☀️ |
| TTS ภาษาไทยไม่มีใน device | fallback เป็น beep อย่างเดียว (ไม่ error) |
| หลายใบหน้าในเฟรมเดียว | overlay แสดงหน้าแรก, beep ทุกหน้า |
| Network drop | reconnect อัตโนมัติ (3s) — wake lock ยังทำงาน |
| Tab switch / phone lock | visibilitychange → re-acquire wake lock เมื่อ visible |
| กด Stop ระหว่าง reconnect | `_destroyed` flag ป้องกัน reconnect loop |

---

## 8. Architecture Integration

### เปรียบเทียบกับ Camera Types อื่น

| | `/scan` (Webcam) | `/mobile-scan` (Smartphone) | `rtsp_agent.py` (IP Cam) |
|--|-----------------|---------------------------|--------------------------|
| Hardware | PC webcam | สมาร์ทโฟน | IP Camera / CCTV |
| Protocol | WS binary JPEG | WS binary JPEG | WS binary JPEG |
| UI | Sidebar layout | Fullscreen HUD | CLI (no UI) |
| Audio | ❌ | ✅ TTS + beep | ❌ |
| Wake Lock | ❌ (PC ไม่ดับ) | ✅ | ❌ (server process) |
| Portable | ❌ | ✅ | ❌ (fixed mount) |
| Control | pause/resume | pause/resume/set_fps | pause/resume/set_fps |

*ทุกประเภทใช้ protocol เดียวกัน — "One Protocol, Many Cameras" (ADR-009)*

### Route Architecture

```
/mobile-scan → standalone route (ไม่ nested ใต้ AppLayout)
               เหตุผล: ใช้ fixed inset-0 = fullscreen
                        sidebar จะบดบัง video feed
               Access: ทุก authenticated role (OPERATOR, HR, ADMIN)
```

### Network Access (Local)

```
PC (dev server):  http://192.168.1.170:5173/mobile-scan
WS Backend:       ws://192.168.1.170:8000/api/v1/ws/scan/{stationId}

vite.config.js: server.host = true   (bind 0.0.0.0)
main.py CORS:   เพิ่ม http://192.168.1.170:5173

WebSocket URL: ws://${window.location.hostname}:8000/...
               ← dynamic ตาม hostname ที่เปิด (ทำงานได้ทั้ง localhost และ IP)
```

---

## 9. ผลลัพธ์ (Before → After)

| | ก่อน | หลัง |
|--|------|------|
| หน้าจอ | ❌ ดับใน 30s | ✅ Wake Lock ตลอด session |
| การแจ้งเตือน | ❌ visual เท่านั้น | ✅ TTS + beep + vibrate |
| อ่านผลลัพธ์ | ❌ card เล็ก กลางแดดมองไม่เห็น | ✅ HUD ขนาดใหญ่ clamp font |
| Unknown alert | ❌ เงียบ | ✅ double beep + สั่น |
| Beep spam | ❌ beep ทุก frame | ✅ cooldown 3s per face |
| Operator experience | ❌ ต้องจ้องหน้าจอตลอด | ✅ ได้ยินเสียง ไม่ต้องมอง |

---

## 10. Known Limitations

| รายการ | หมายเหตุ |
|--------|---------|
| TTS ภาษาไทย | ขึ้นกับ voice ใน device — บาง Android ไม่มี th-TH voice |
| Wake Lock iOS | ต้องการ iOS 16.4+ และ HTTPS (localhost ยกเว้น) |
| HTTPS requirement | Production deploy ต้องใช้ HTTPS เพื่อ Wake Lock + getUserMedia |
| Single overlay | แสดงผลหน้าแรกในเฟรมเท่านั้น (กรณีหลายคนพร้อมกัน) |
| Audio latency | TTS อาจมี delay 0.1–0.3s ขึ้นกับ device |

---

*บันทึก: 2026-05-18 | Sprint 10–11 | Analyst → Design → Implement → Report*
