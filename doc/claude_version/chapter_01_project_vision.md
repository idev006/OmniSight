# Chapter 1: Project Vision & Overview

## ชื่อระบบ: OmniSight

> "ความซับซ้อนต้องอยู่ที่วิศวกร ความเรียบง่ายและลื่นไหลต้องอยู่ที่ผู้ใช้"

---

## วิสัยทัศน์ (Vision)

สร้างระบบเช็คชื่อด้วยใบหน้าที่ **พนักงานเดินผ่านแล้วชื่อเด้งขึ้นมาทันที** โดยที่ไม่ต้องหยุด ไม่ต้องกด ไม่ต้องรู้สึกว่ากำลังถูกสแกน ระบบเบื้องหลังทำงานอย่างเงียบเชียบและแม่นยำ

---

## เป้าหมายหลัก (Core Goals)

| Goal | รายละเอียด |
|------|-----------|
| Zero-Lag | วิดีโอและ Overlay ต้องลื่นไหลตลอดเวลา ไม่กระตุก |
| Smart Overlay | ข้อมูลพนักงานลอยตามใบหน้า ไม่สั่น ไม่ทับกัน |
| Scale | รองรับพนักงาน 10,000 คน (60,000 Face Embeddings) |
| CPU-Only | ทำงานได้ดีบน Ryzen โดยไม่ต้องพึ่ง GPU |
| Multi-Face | รองรับ 1-10 ใบหน้าในเฟรมเดียวกัน |

---

## ข้อจำกัดของ Hardware (Constraints)

| ทรัพยากร | ข้อจำกัด | วิธีรับมือ |
|---------|---------|----------|
| ไม่มี GPU | ประมวลผลบน CPU เท่านั้น | ONNX Runtime + AVX-512 + Batch Inference |
| RAM 16 GB | ต้องบริหารจัดการอย่างระมัดระวัง | Scalar Quantization ใน Qdrant |
| CPU Ryzen (ใหม่) | Multi-core สูง, มี AVX-512/VNNI | Pin AI workers บน Performance Cores |

---

## สถาปัตยกรรมระดับสูง (High-Level Architecture)

```
[กล้อง N ตัว]
      ↓ WebSocket (Binary)
[Backend: FastAPI]
      ↓                    ↓
[ONNX Inference]    [Redis: Active Filter]
      ↓
[Qdrant: Vector Search (dept filtered)]
      ↓
[PostgreSQL: Employee Metadata + Log]
      ↓ WebSocket (JSON)
[Frontend: Vue 3 + Canvas Overlay]
```

---

## ผู้ใช้งานระบบ (Users)

| ผู้ใช้ | บทบาท |
|-------|-------|
| พนักงาน | เดินผ่านจุดสแกน — ไม่ต้องทำอะไรเพิ่ม |
| HR / Admin | ลงทะเบียนพนักงาน, จัดการ Station, ดู Report |
| System (AI) | ตรวจจับ, ระบุตัวตน, บันทึก log อัตโนมัติ |

---

## ความคาดหวังด้าน Performance

| Metric | เป้าหมาย |
|--------|---------|
| Face Detection + Recognition | < 300ms end-to-end |
| Vector Search (filtered) | < 10ms |
| UI Overlay Frame Rate | 30 FPS ขึ้นไป |
| ระบบพร้อมใช้งาน | 99.9% uptime (24/7) |
| False Positive Rate | < 0.1% |

---

## ขอบเขตของระบบ (Scope)

### อยู่ในขอบเขต ✅
- ลงทะเบียนใบหน้าพนักงาน (HR ดำเนินการ)
- สแกนเช็คชื่อแบบ Real-time (Multi-face 1-10 คน)
- แสดง Overlay ข้อมูลพนักงานบนเฟรมวิดีโอ
- จัดการ Station (กล้อง) หลายตัว
- กรองการค้นหาตามแผนก (Strict Mode)
- บันทึก Attendance Log พร้อม Timestamp
- รายงานสรุปการเข้างาน (HR ใช้)
- จัดการข้อมูลพนักงาน, แผนก, กะ

### ไม่อยู่ในขอบเขต ❌
- การตัดสินว่าพนักงานสายหรือไม่ (HR Report ทำเอง)
- ระบบเงินเดือน (Payroll Integration — Phase ถัดไป)
- Mobile Application
- การรู้จำเสียง (Voice Recognition)
