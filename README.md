# 👁️ OmniSight — AI Face Recognition Attendance System

ระบบลงเวลางานและเช็คชื่ออัจฉริยะด้วยเทคโนโลยีตรวจจับใบหน้า (Face Recognition) พัฒนาขึ้นมาสำหรับตอบโจทย์ Enterprise HR, สถานศึกษา และงานอีเวนต์ขนาดใหญ่

---

## 🛠️ Tech Stack & Services

*   **Backend:** FastAPI (Python 3.12) + SQLAlchemy (Async) + Alembic
*   **AI Engine:** InsightFace `buffalo_l` (ONNX Runtime)
*   **Vector DB:** Qdrant (HNSW + SQ8)
*   **Cache / Event Bus:** Redis (Pub/Sub & Attendance Cooldown)
*   **Database:** PostgreSQL 16
*   **Frontend:** Vue 3 + Vite + Tailwind CSS + DaisyUI

---

## 📋 สิ่งที่ต้องเตรียม (Prerequisites)

ก่อนเริ่มเซ็ตอัพโปรเจกต์ กรุณาติดตั้งซอฟต์แวร์เหล่านี้ลงบนเครื่องคอมพิวเตอร์ของคุณ:

1.  **Git:** สำหรับดึงโค้ดและแชร์โค้ด
2.  **Python 3.12:** สภาพแวดล้อมภาษาสำหรับรัน Backend
3.  **Node.js (v18 ขึ้นไป):** สภาพแวดล้อมสำหรับฝั่ง Frontend
4.  **Docker Desktop:** สำหรับรันฐานข้อมูลและบริการเสริมต่าง ๆ (PostgreSQL, Redis, Qdrant)

---

## 🚀 ขั้นตอนการติดตั้งและรันโปรเจกต์แบบละเอียด (Setup Guide)

ให้ทำตามขั้นตอนต่อไปนี้ทีละขั้นตอนในเครื่องใหม่เพื่อเริ่มต้นใช้งาน:

### 1. ดึงโค้ดจากรีโพสิทอรี (Clone)
เปิด Terminal หรือ Command Prompt ในจุดที่ต้องการเก็บงาน แล้วรัน:
```bash
git clone https://github.com/idev006/OmniSight.git
cd OmniSight
```

---

### 2. เริ่มบริการระบบหลังบ้าน (Start Docker Services)
เปิด **Docker Desktop** ไว้ในเครื่อง จากนั้นกลับมาที่โฟลเดอร์โครงการ รันคำสั่งนี้เพื่อเริ่มสร้างฐานข้อมูลและระบบจับคู่ใบหน้าเวกเตอร์ในพื้นหลัง:
```bash
docker-compose up -d
```
> คำสั่งนี้จะทำการสร้างบริการ 3 อย่างโดยอัตโนมัติ:
> *   **PostgreSQL** (Port: `5432`)
> *   **Qdrant Vector DB** (Port: `6333` / Dashboard: `http://localhost:6333/dashboard`)
> *   **Redis** (Port: `6379`)

---

### 3. ตั้งค่าระบบหลังบ้าน (Backend Setup)

1.  **สร้างสภาพแวดล้อมจำลอง (Virtual Environment):**
    ```powershell
    python -m venv my_env
    ```
2.  **เปิดการใช้งานสภาพแวดล้อมจำลอง (Activate):**
    *   **Windows (PowerShell):**
        ```powershell
        .\my_env\Scripts\Activate.ps1
        ```
    *   **Windows (Command Prompt):**
        ```cmd
        .\my_env\Scripts\activate.bat
        ```
    *   **macOS / Linux:**
        ```bash
        source my_env/bin/activate
        ```
3.  **ติดตั้ง Libraries ทั้งหมดของ Python:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **สร้างไฟล์สำหรับตั้งค่าระบบความปลอดภัย (`.env`):**
    สร้างไฟล์ชื่อ `.env` ไว้ข้างในโฟลเดอร์ `backend/` แล้วใส่การเชื่อมต่อต่าง ๆ (อิงตามระบบของคุณ):
    ```env
    DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/omnisight
    REDIS_URL=redis://localhost:6379/0
    QDRANT_URL=http://localhost:6333
    JWT_SECRET=your_jwt_secret_key_here
    ACCESS_TOKEN_EXPIRE_HOURS=8
    ```
5.  **ทำการอัปเดตโครงสร้างฐานข้อมูล (Database Migration):**
    ในหน้าหลักของโปรเจกต์ (ยังเปิด virtual environment ค้างไว้) รันสคริปต์ย้ายข้อมูล:
    ```powershell
    .\migrate.bat upgrade
    ```

---

### 4. ตั้งค่าระบบหน้าบ้าน (Frontend Setup)

1.  ย้ายเข้าไปในโฟลเดอร์หน้าบ้าน:
    ```bash
    cd frontend
    ```
2.  ติดตั้งโมดูล Node.js ทั้งหมด:
    ```bash
    npm install
    ```

---

## 🏃 วิธีการรันแอปพลิเคชัน (How to Run)

ในหน้าโฟลเดอร์หลักของโปรเจกต์ (`OmniSight/`) เรามีสคริปต์ที่ทำเตรียมไว้ให้สามารถดับเบิลคลิกหรือรันเพื่อความสะดวกได้เลยครับ:

### **ฝั่งหลังบ้าน (Backend)**
เปิด Terminal รัน:
```powershell
.\start-backend.bat
```
*   หรือใช้งานแบบ Manual: `cd backend` และรัน `uvicorn main:app --reload`
*   Backend จะทำงานบน: **`http://localhost:8000`**
*   คุณสามารถเข้าไปทดสอบ API Docs ได้ที่: **`http://localhost:8000/docs`**

### **ฝั่งหน้าบ้าน (Frontend)**
เปิด Terminal อีกตัวขึ้นมาใหม่ รัน:
```powershell
.\start-frontend.bat
```
*   หรือใช้งานแบบ Manual: `cd frontend` และรัน `npm run dev`
*   Frontend จะทำงานบน: **`http://localhost:5173`**

### 🔑 บัญชีเข้าใช้งานระบบเริ่มต้น (Default Login)
*   **Username:** `admin`
*   **Password:** `admin`

---

## 🤝 ข้อปฏิบัติร่วมกันในการพัฒนาโปรเจกต์ (Git Workflow)

เพื่อป้องกันการเกิดปัญหาไฟล์ชนกันระหว่างเพื่อนร่วมงาน แนะนำให้มีข้อตกลงในการพัฒนาโค้ดร่วมกันดังนี้ครับ:

1.  **ดึงข้อมูลล่าสุดก่อนเริ่มทำงานทุกครั้ง:**
    ```bash
    git checkout master
    git pull origin master
    ```
2.  **แยกกิ่งเมื่อสร้างฟีเจอร์ใหม่เสมอ:** ห้ามแก้ไขโค้ดตรง ๆ บนกิ่ง `master`
    ```bash
    git checkout -b feature/ชื่อฟีเจอร์ของคุณ
    ```
3.  **ตั้งค่า Ignore ไฟล์ที่ไม่ต้องการบันทึก:** เรามีระบบ [.gitignore](.gitignore) คลุมไว้ให้เรียบร้อยแล้ว ห้ามลบโฟลเดอร์ `my_env/`, `node_modules/`, `storage/` หรือไฟล์ `.env` ไปขึ้นบนเซิร์ฟเวอร์ส่วนกลาง
4.  **ทำการ Push และสร้าง Pull Request:** เมื่อฟีเจอร์นั้นทำงานเสร็จสิ้นแล้ว ให้ Push กิ่งไปที่เซิร์ฟเวอร์ แล้วแจ้งเพื่อนให้ช่วยรีวิวโค้ดก่อนกดรวม (Merge)
    ```bash
    git push origin feature/ชื่อฟีเจอร์ของคุณ
    ```

---
*อัปเดตล่าสุด: 2026-05-17 (Sprint 8)*
