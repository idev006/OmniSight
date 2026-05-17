# Chapter 22 — Authentication & Authorization

> เขียน: 2026-05-17 | Sprint 8

---

## ภาพรวม

OmniSight ใช้ **JWT Bearer Token** สำหรับ Authentication และ **Role-Based Access Control (RBAC)** สำหรับ Authorization โดยมีหลักการ:

- **SSOT (Single Source of Truth)**: `auth.js` store เป็นศูนย์กลาง — ทุก component อ่าน auth state จากที่เดียว
- **Double-check**: Frontend guard + Backend dependency ทั้งคู่ต้องผ่าน
- **Defense-in-depth**: Token expiry เช็คทั้งฝั่ง client (computed) และ server (JWT decode)

---

## Roles

| Role | ย่อว่า | สิทธิ์ |
|------|--------|--------|
| `ADMIN` | ผู้ดูแลระบบ | ทุกอย่าง |
| `HR` | HR Manager | อ่าน/แก้ข้อมูล HR, ดู Attendance |
| `OPERATOR` | เจ้าหน้าที่สแกน | Scan เฉพาะ station ที่ได้รับมอบหมาย |

---

## Sequence Diagrams

### 1. Login Flow

```mermaid
sequenceDiagram
    actor User
    participant LoginView
    participant AuthStore
    participant API as FastAPI /auth/login
    participant DB as PostgreSQL

    User->>LoginView: กรอก username + password
    LoginView->>AuthStore: auth.login(username, password)
    AuthStore->>API: POST /api/v1/auth/login
    API->>DB: SELECT user WHERE username=? AND is_active=TRUE
    DB-->>API: User record
    API->>API: verify_password(plain, hashed)
    
    alt ✅ Credentials valid
        API->>DB: SELECT access_token_expire_hours FROM system_settings
        DB-->>API: expire_hours (e.g. 8)
        API->>API: create_access_token(sub, role, user_id, station_ids, expire_hours)
        API-->>AuthStore: { access_token: "eyJ..." }
        AuthStore->>AuthStore: validate token (not expired, has sub+role)
        AuthStore->>AuthStore: localStorage.setItem('omnisight-token', token)
        AuthStore->>API: GET /api/v1/auth/me (verify + get full_name)
        API->>DB: SELECT user WHERE id=? AND is_active=TRUE
        DB-->>API: { full_name, role, station_ids }
        API-->>AuthStore: UserInfo
        AuthStore-->>LoginView: login() resolved
        LoginView->>Router: router.replace('/scan')
    else ❌ Invalid credentials
        API-->>AuthStore: 401 Unauthorized
        AuthStore-->>LoginView: throw Error
        LoginView->>LoginView: error.value = 'Invalid username or password'
    end
```

---

### 2. Protected API Call Flow

```mermaid
sequenceDiagram
    actor User
    participant Component
    participant APIClient as axios client
    participant Backend as FastAPI endpoint
    participant Security as security.py

    User->>Component: ทำ action (e.g. โหลดรายการ employees)
    Component->>APIClient: api.get('/api/v1/employees')
    
    APIClient->>APIClient: request interceptor:<br/>ดึง token จาก localStorage('omnisight-token')
    APIClient->>Backend: GET /api/v1/employees<br/>Authorization: Bearer eyJ...
    
    Backend->>Security: Depends(require_hr)
    Security->>Security: decode_token(token)
    
    alt ✅ Token valid + role = ADMIN or HR
        Security-->>Backend: CurrentUser object
        Backend->>DB: SELECT employees...
        DB-->>Backend: data
        Backend-->>APIClient: 200 OK + data
        APIClient-->>Component: response.data
        Component->>Component: แสดงผลข้อมูล
    else ❌ Token expired or invalid
        Security-->>Backend: 401 Unauthorized
        Backend-->>APIClient: 401 response
        APIClient->>APIClient: response interceptor:<br/>localStorage.removeItem('omnisight-token')
        APIClient->>Browser: window.location.replace('/login?reason=expired')
        Browser->>LoginView: แสดง "Your session has expired"
    else ❌ Wrong role (e.g. OPERATOR calling HR endpoint)
        Security-->>Backend: 403 Forbidden
        Backend-->>APIClient: 403 response
        APIClient-->>Component: throw error
        Component->>Component: toast.error(...)
    end
```

---

### 3. App Load / Session Restore Flow

```mermaid
sequenceDiagram
    participant Browser
    participant App as App.vue (onMounted)
    participant AuthStore
    participant Router
    participant API as /auth/me

    Browser->>App: โหลดหน้าใหม่ (F5 / URL เข้าตรง)
    App->>AuthStore: useAuthStore() initializes
    AuthStore->>AuthStore: token = localStorage.getItem('omnisight-token')
    
    alt ✅ token พบ
        App->>AuthStore: auth.verifySession()
        AuthStore->>AuthStore: isTokenExpired(token)?
        
        alt token expired (client-side check)
            AuthStore->>AuthStore: _clearState() → ลบ localStorage
            AuthStore-->>App: return false
        else token not expired
            AuthStore->>API: GET /api/v1/auth/me
            
            alt ✅ User ยังอยู่ใน DB + is_active
                API-->>AuthStore: { full_name, role, ... }
                AuthStore->>AuthStore: _fullName = full_name
                AuthStore-->>App: return true
            else ❌ User ถูก deactivate
                API-->>AuthStore: 401 Deactivated
                AuthStore->>AuthStore: _clearState()
                AuthStore-->>App: return false
                App->>Browser: redirect /login?reason=deactivated
            end
        end
    else ❌ ไม่มี token
        App->>App: ไม่ทำอะไร (Router guard จัดการ)
    end
    
    App->>Router: Navigation begins
    Router->>AuthStore: router.beforeEach → auth.isLoggedIn?
    
    alt Not logged in + accessing protected route
        Router->>Browser: redirect /login (+ ?reason=expired ถ้ามี token เก่า)
    else Logged in + wrong role
        Router->>Browser: redirect /scan
    else ✅ OK
        Router->>Browser: render component
    end
```

---

### 4. Logout Flow

```mermaid
sequenceDiagram
    actor User
    participant AppLayout
    participant ConfirmModal
    participant AuthStore
    participant Browser

    User->>AppLayout: คลิก "Sign Out"
    AppLayout->>ConfirmModal: await confirm("Sign out of OmniSight?")
    ConfirmModal-->>User: แสดง modal
    
    alt ✅ User กด "Sign Out"
        ConfirmModal-->>AppLayout: true
        AppLayout->>AuthStore: auth.logout()
        AuthStore->>AuthStore: token.value = ''
        AuthStore->>AuthStore: _fullName.value = ''
        AuthStore->>AuthStore: localStorage.removeItem('omnisight-token')
        AuthStore->>Browser: window.location.replace('/login')
        Browser->>LoginView: หน้า login (clean state)
    else ❌ User กด "Cancel"
        ConfirmModal-->>AppLayout: false
        AppLayout->>AppLayout: ไม่ทำอะไร
    end
```

---

## API Authorization Matrix

### ✅ = Protected | 🔴 = Unprotected (ก่อนแก้)

| Module | Endpoint | Method | Required Role | After Fix |
|--------|----------|--------|---------------|-----------|
| **auth** | /auth/login | POST | none (public) | ✅ by design |
| **auth** | /auth/me | GET | any auth user | ✅ |
| **users** | /users | GET | ADMIN | ✅ |
| **users** | /users | POST | ADMIN | ✅ |
| **users** | /users/{id} | GET/PUT/DELETE | ADMIN | ✅ |
| **users** | /users/{id}/stations | PUT | ADMIN | ✅ |
| **departments** | /departments | GET | HR + ADMIN | ✅ fixed |
| **departments** | /departments | POST | ADMIN | ✅ fixed |
| **departments** | /departments/{id} | PUT/DELETE | ADMIN | ✅ fixed |
| **employees** | /employees | GET | HR + ADMIN | ✅ fixed |
| **employees** | /employees | POST | HR + ADMIN | ✅ fixed |
| **employees** | /employees/{id} | GET/PATCH | HR + ADMIN | ✅ fixed |
| **enrollment** | /employees/{id}/enrollment | GET | HR + ADMIN | ✅ fixed |
| **enrollment** | /employees/{id}/enroll | POST | HR + ADMIN | ✅ fixed |
| **enrollment** | /employees/{id}/enroll/{idx} | DELETE | HR + ADMIN | ✅ fixed |
| **stations** | /stations | GET | any auth user | ✅ fixed |
| **stations** | /stations | POST | ADMIN | ✅ fixed |
| **stations** | /stations/{id} | GET | any auth user | ✅ fixed |
| **stations** | /stations/{id}/departments | PUT | ADMIN | ✅ fixed |
| **attendance** | /attendance | GET | HR + ADMIN | ✅ fixed |
| **cameras** | /cameras | GET | HR + ADMIN | ✅ |
| **cameras** | /cameras | POST | ADMIN | ✅ |
| **cameras** | /cameras/{id} | GET | HR + ADMIN | ✅ |
| **cameras** | /cameras/{id} | PUT/DELETE | ADMIN | ✅ |
| **cameras** | /cameras/{id}/pause,resume | POST | ADMIN | ✅ |
| **shifts** | /shifts | GET | HR + ADMIN | ✅ fixed |
| **shifts** | /shifts | POST | ADMIN | ✅ fixed |
| **shifts** | /shifts/{id} | DELETE | ADMIN | ✅ fixed |
| **settings** | /settings | GET/PUT | ADMIN | ✅ |
| **websocket** | /ws/scan/{station_id} | WS | any auth + station check | ✅ |

---

## Frontend Route Guard Matrix

| Route | Allowed Roles | Guard |
|-------|---------------|-------|
| /scan | All (ADMIN, HR, OPERATOR) | auth only |
| /attendance | ADMIN, HR | `roles: ['ADMIN','HR']` |
| /employees | ADMIN, HR | `roles: ['ADMIN','HR']` |
| /employees/:id/enroll | ADMIN, HR | `roles: ['ADMIN','HR']` |
| /departments | ADMIN, HR | `roles: ['ADMIN','HR']` |
| /stations | ADMIN | `roles: ['ADMIN']` |
| /cameras | ADMIN | `roles: ['ADMIN']` |
| /users | ADMIN | `roles: ['ADMIN']` |
| /settings | ADMIN | `roles: ['ADMIN']` |
| /login | public | redirect to /scan if logged in |

---

## Auth Store SSOT Design

```
┌─────────────────────────────────────────────────────────┐
│                    auth.js (Pinia Store)                 │
│                                                         │
│  token (ref)  ──────────────────────────────────────┐  │
│     │                                               │  │
│     ▼                                               ▼  │
│  user (computed)                          localStorage  │
│     ├── checks isTokenExpired()          'omnisight-    │
│     ├── checks p.sub && p.role           token'         │
│     └── returns null if any fail                        │
│                                                         │
│  isLoggedIn = !!user (covers expiry)                    │
│  isAdmin    = role === 'ADMIN'                          │
│  isHR       = role in ['ADMIN','HR']                    │
│  expiresIn  = p.exp - now (seconds)                     │
│                                                         │
│  login()         → stores token + calls verifySession() │
│  logout()        → clears all + redirect /login         │
│  forceLogout()   → called by 401 interceptor            │
│  verifySession() → calls /me on app load                │
└─────────────────────────────────────────────────────────┘
```

---

## Security Dependencies (backend)

```python
# security.py — ใช้เป็น Depends() ใน endpoint

get_current_user    # ✅ any valid JWT → decode only
require_hr          # ✅ role must be ADMIN or HR
require_admin       # ✅ role must be ADMIN
get_current_user_ws # ✅ WebSocket version (token via query param)
```

---

## Known Limitations (ยังไม่ได้แก้)

| Issue | Severity | หมายเหตุ |
|-------|----------|---------|
| Token stored in localStorage (XSS risk) | 🟡 MEDIUM | httpOnly cookie จะปลอดภัยกว่า แต่ต้องเปลี่ยน architecture มาก |
| No token revocation (blacklist) | 🟡 MEDIUM | logout ลบแค่ client-side, token ยังใช้ได้บน server จนหมดอายุ |
| No CSRF protection | 🟡 MEDIUM | ป้องกันด้วย CORS policy (allow_origins ระบุชัด) |
| WebSocket token ไม่ revoke เมื่อ logout | 🟡 LOW | Long-lived WS ยังทำงานได้หลัง logout |

---

## Files ที่เกี่ยวข้อง

| ไฟล์ | บทบาท |
|------|-------|
| `frontend/src/stores/auth.js` | SSOT — token + user state ทั้งหมด |
| `frontend/src/api/client.js` | Axios — attach token + 401 handler |
| `frontend/src/router/index.js` | Route guards + roles array |
| `frontend/src/views/LoginView.vue` | Login form + session expired banner |
| `frontend/src/layouts/AppLayout.vue` | Sign out confirm |
| `backend/app/core/security.py` | JWT decode + FastAPI dependencies |
| `backend/app/api/auth.py` | /login + /me endpoints |

---

*อัพเดทล่าสุด: 2026-05-17 (Sprint 8)*
