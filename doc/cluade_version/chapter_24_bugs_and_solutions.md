# Chapter 24 — Bugs & Solutions Log

> บันทึกปัญหาที่พบจริงระหว่าง development และวิธีแก้  
> ใช้เป็น reference สำหรับ session ถัดไปและการ deploy production

---

## BUG-005 — Docker Redis port 6379 blocked (Hyper-V port exclusion)

| | รายละเอียด |
|--|-----------|
| **Severity** | 🔴 Critical — ระบบ start ไม่ได้ |
| **Sprint** | Sprint 10 |
| **Symptom** | `Error response from daemon: ports are not available: exposing port TCP 0.0.0.0:6379` |
| **Root Cause** | Windows Hyper-V / WSL2 จอง dynamic port ranges ทับ port 6379 (Redis)<br>Excluded ranges: 6351–6450, 6451–6550, 6551–6650, 6651–6750 |

### วิธีวินิจฉัย

```powershell
netsh interface ipv4 show excludedportrange protocol=tcp
# ผลลัพธ์แสดง 6351-6450 ครอบคลุม port 6379
```

### วิธีแก้ ✅

```powershell
# เปิด PowerShell as Administrator
net stop winnat
net start winnat
# WinNAT release port reservations ทั้งหมด — start Docker ได้ทันที
```

### หมายเหตุ
- ปัญหานี้เกิดซ้ำได้หลัง Windows reboot บางครั้ง
- ถ้าไม่มี Admin สิทธิ์: เปลี่ยน host port ใน `docker-compose.yml` จาก `6379:6379` → `6300:6379` และ `REDIS_URL=redis://localhost:6300/0` ใน `.env`

---

## BUG-006 — Vite proxy ECONNREFUSED (Node.js IPv6 vs IPv4)

| | รายละเอียด |
|--|-----------|
| **Severity** | 🔴 Critical — API call ทั้งหมดล้มเหลว |
| **Sprint** | Sprint 10 |
| **Symptom** | `[vite] http proxy error: /api/v1/auth/login`<br>`AggregateError [ECONNREFUSED]` |
| **Root Cause** | Node.js 18+ resolve `localhost` เป็น `::1` (IPv6) ก่อน<br>แต่ uvicorn/FastAPI listen บน `0.0.0.0` (IPv4 เท่านั้น)<br>→ IPv6 connection ถูก refuse |

### วิธีวินิจฉัย

```powershell
netstat -ano | Select-String ":8000"
# แสดง 0.0.0.0:8000 LISTENING (IPv4 only, ไม่มี [::]:8000)
```

### วิธีแก้ ✅

```javascript
// vite.config.js — เปลี่ยน target จาก localhost เป็น explicit IPv4
proxy: {
  '/api': { target: 'http://127.0.0.1:8000' },  // ✅ explicit IPv4
  '/ws':  { target: 'ws://127.0.0.1:8000', ws: true },
}
// ❌ ไม่ใช้: 'http://localhost:8000'  ← Node 18+ → ::1 → ECONNREFUSED
```

---

## BUG-007 — Mobile login fail (axios baseURL hardcoded localhost)

| | รายละเอียด |
|--|-----------|
| **Severity** | 🔴 Critical — มือถือ login ไม่ได้ |
| **Sprint** | Sprint 10 |
| **Symptom** | หน้า login โหลดได้ แต่กด Login แล้วไม่มีอะไรเกิดขึ้น (network error) |
| **Root Cause** | `api/client.js` ใช้ `baseURL: 'http://localhost:8000'`<br>มือถือ resolve `localhost` = ตัวมือถือเอง ≠ PC<br>→ request ออกไปไม่ถึง backend เลย |

### วิธีแก้ ✅

```javascript
// frontend/src/api/client.js
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/',  // ✅ relative URL
  // Vite proxy (/api → 127.0.0.1:8000) จัดการเอง
  // ทำงานได้ทั้งจาก localhost และ IP address บนมือถือ
})
```

### หลักการ
Request path: `มือถือ → https://192.168.1.170:5173/api/...` → Vite proxy (server-side) → `127.0.0.1:8000`  
Proxy ทำงานบน PC ไม่ใช่บน client → relative URL จึงถูกต้องเสมอ

---

## BUG-008 — Mobile login 401 (keyboard autocapitalize)

| | รายละเอียด |
|--|-----------|
| **Severity** | 🟡 High — login ไม่ได้บน mobile |
| **Sprint** | Sprint 10 |
| **Symptom** | Backend log แสดง `POST /api/v1/auth/login 401 Unauthorized`<br>ทั้งที่ credentials ถูกต้อง (ทดสอบจาก PC ผ่าน) |
| **Root Cause** | iOS และ Android keyboard autocapitalize ตัวแรกของ `<input type="text">` เป็น capital<br>`operator1` → `Operator1` → password ไม่ตรง → 401 |

### วิธีแก้ ✅

```html
<!-- frontend/src/views/LoginView.vue -->
<input
  v-model="form.username"
  type="text"
  autocapitalize="off"   <!-- ✅ ปิด auto capitalize -->
  autocorrect="off"      <!-- ✅ ปิด autocorrect -->
  spellcheck="false"     <!-- ✅ ปิด spellcheck -->
/>
<input
  v-model="form.password"
  type="password"
  autocapitalize="off"
  autocorrect="off"
/>
```

### หมายเหตุ
ควรเพิ่ม attribute เหล่านี้กับ **ทุก input ที่เป็น credential** (username, password, token, PIN)

---

## BUG-009 — Camera not available on HTTP non-localhost

| | รายละเอียด |
|--|-----------|
| **Severity** | 🔴 Critical — กล้องเปิดไม่ได้บน mobile |
| **Sprint** | Sprint 10 |
| **Symptom** | กด Start → `TypeError: Cannot read properties of undefined (reading 'getUserMedia')` |
| **Root Cause** | Browser Security Policy: `navigator.mediaDevices` เป็น `undefined` บน HTTP ที่ไม่ใช่ localhost<br>เรียก `getUserMedia()` บน HTTP + non-localhost = blocked โดย browser |

### เงื่อนไข Secure Context

| URL | Camera API | หมายเหตุ |
|-----|-----------|---------|
| `http://localhost` | ✅ ใช้ได้ | localhost ยกเว้นพิเศษ |
| `http://192.168.x.x` | ❌ ไม่ได้ | non-localhost HTTP |
| `https://192.168.x.x` | ✅ ใช้ได้ | HTTPS เสมอได้ |
| `https://domain.com` | ✅ ใช้ได้ | production |

### วิธีแก้สำหรับ Development ✅

```bash
# ติดตั้ง Vite HTTPS plugin
npm install -D @vitejs/plugin-basic-ssl
```

```javascript
// vite.config.js
import basicSsl from '@vitejs/plugin-basic-ssl'

export default defineConfig({
  plugins: [vue(), basicSsl()],  // สร้าง self-signed cert อัตโนมัติ
  server: { host: true, ... }
})
```

มือถือเปิด `https://192.168.1.170:5173` → Chrome แจ้งเตือน cert → กด **Advanced → Proceed** → กล้องทำงาน ✅

### วิธีแก้สำหรับ Production

```nginx
# nginx.conf — ต้องมี SSL certificate จริง
server {
    listen 443 ssl;
    ssl_certificate     /etc/ssl/certs/omnisight.crt;
    ssl_certificate_key /etc/ssl/private/omnisight.key;
}
```

### Error Message ที่ปรับปรุงแล้ว

```javascript
// MobileScanView.vue — แสดง error ที่อ่านเข้าใจได้แทนการ crash
if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
  throw new Error(
    'Camera not available on HTTP.\n' +
    'Use: https://' + window.location.hostname + ':5173'
  )
}
```

---

## BUG-010 — WebSocket ใช้ ws:// เมื่อ frontend เป็น HTTPS

| | รายละเอียด |
|--|-----------|
| **Severity** | 🟡 High — scan ไม่ทำงานหลังแก้ BUG-009 |
| **Sprint** | Sprint 10 |
| **Symptom** | Mixed Content error: HTTPS page load ws:// (non-secure) WebSocket |
| **Root Cause** | WebSocket URL hardcoded เป็น `ws://` แต่เมื่อ frontend serve ด้วย HTTPS<br>browser บล็อก mixed content (HTTPS + ws:// ไม่ได้) |

### วิธีแก้ ✅

```javascript
// ทุกไฟล์ที่ใช้ WebSocket: MobileScanView.vue, ScanView.vue, PilotConsoleView.vue
const wsProto = window.location.protocol === 'https:' ? 'wss' : 'ws'
const url = `${wsProto}://${window.location.hostname}:8000/api/v1/ws/...`
//           ↑ wss:// สำหรับ HTTPS, ws:// สำหรับ HTTP
```

---

## สรุป Files ที่แก้ในแต่ละ Bug

| Bug | ไฟล์ที่แก้ |
|-----|-----------|
| BUG-005 | `docker-compose.yml` (workaround), แก้จริงด้วย WinNAT restart |
| BUG-006 | `frontend/vite.config.js` — localhost → 127.0.0.1 |
| BUG-007 | `frontend/src/api/client.js` — baseURL localhost → `/` |
| BUG-008 | `frontend/src/views/LoginView.vue` — autocapitalize/autocorrect |
| BUG-009 | `frontend/vite.config.js` + `@vitejs/plugin-basic-ssl` |
| BUG-010 | `MobileScanView.vue`, `ScanView.vue`, `PilotConsoleView.vue` — ws/wss dynamic |

---

## Checklist สำหรับ Mobile Development

```
✅ vite.config.js: host: true (เปิด network access)
✅ vite.config.js: proxy target ใช้ 127.0.0.1 (ไม่ใช่ localhost)
✅ vite.config.js: basicSsl() plugin (HTTPS สำหรับ camera API)
✅ api/client.js: baseURL = '/' (relative, ไม่ใช่ localhost)
✅ Login inputs: autocapitalize="off" autocorrect="off"
✅ WebSocket URL: wss:// เมื่อ page เป็น HTTPS
✅ Backend CORS: เพิ่ม https://<PC-IP>:5173
```

---

## Production Deployment Notes

เมื่อ deploy production สิ่งที่ต้องทำ:

1. **SSL Certificate** — ใช้ Let's Encrypt หรือ corporate cert
2. **nginx reverse proxy** — frontend + backend อยู่ domain เดียวกัน → ไม่มี cross-origin WS
3. **ลบ basicSsl()** ออกจาก vite.config.js (ใช้แค่ dev)
4. **CORS origins** — เปลี่ยนเป็น production domain แทน IP
5. **SECRET_KEY** — เปลี่ยนจาก default เป็น random 32+ chars

---

*บันทึก: 2026-05-18 | Sprint 10 | Mobile device testing session*
