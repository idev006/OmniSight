# Chapter 0: Technology Stack

## Overview

OmniSight ออกแบบให้รันได้บนทุก Environment โดยไม่ต้องแก้โค้ด ระบบตรวจจับ Hardware อัตโนมัติและเลือกใช้ Execution Provider ที่ดีที่สุดที่มีอยู่

| Environment | OS | Hardware | Provider |
|-------------|-----|---------|---------|
| Local (ปัจจุบัน) | Windows 11 | Ryzen CPU | CPUExecutionProvider |
| Local (upgrade) | Windows 11 | NVIDIA GPU | CUDAExecutionProvider |
| Local (AMD iGPU) | Windows 11 | Radeon iGPU | DirectMLExecutionProvider |
| On-Premise | Linux | NVIDIA GPU | CUDAExecutionProvider |
| Cloud (AWS/GCP/Azure) | Linux | NVIDIA GPU | CUDAExecutionProvider |

---

## Frontend

| Component | Technology | เหตุผล |
|-----------|-----------|--------|
| Build Tool | Vite (Latest) | Fast HMR, optimized bundle |
| Framework | Vue.js 3 (Latest) | Reactive state, Composition API |
| UI Library | DaisyUI (Latest) | Native components, ไม่ต้องเขียน CSS เอง |
| CSS Framework | Tailwind CSS (Latest) | Utility-first, เบาและเร็ว |
| Router | Vue Router | SPA routing |
| State Management | Pinia | ง่ายกว่า Vuex, รองรับ TypeScript |
| Face Overlay | Canvas API + Vue 3 | วาด Bounding Box + แสดง Identity Card |

> **หมายเหตุ:** ไม่ใช้ MediaPipe WASM บน Frontend — Backend จัดการ Detection + Recognition ทั้งหมด Frontend ทำหน้าที่แค่ **รับผลลัพธ์แล้ววาด Overlay**

---

## Backend

| Component | Technology | เหตุผล |
|-----------|-----------|--------|
| Runtime | Python 3.12 | Performance improvements, better typing |
| API Framework | FastAPI | Async, OpenAPI built-in, WebSocket support |
| Data Validation | Pydantic v2 | เร็วกว่า v1 มาก, strict typing |
| ORM | SQLAlchemy | Mature, รองรับ async |
| DB Migration | Alembic | คู่กับ SQLAlchemy, จัดการ Schema changes |
| Inference Engine | ONNX Runtime | Auto-detect: CUDA → DirectML → CPU |
| Face Model | InsightFace buffalo_l | ความแม่นยำสูงสุด (~99.7%) |

---

## Infrastructure

| Component | Technology | เหตุผล |
|-----------|-----------|--------|
| Vector DB | Qdrant (Docker) | HNSW indexing, Payload filtering, Batch search |
| Relational DB | PostgreSQL (Docker) | Reliable, รองรับ UUID, timezone-aware datetime |
| Cache | Redis (Docker) | เก็บ Active Filter state ของ Admin |
| Container | Docker + Docker Compose | ง่ายต่อการ deploy และ restart |

---

## Communication Protocol

| เส้นทาง | Protocol | รูปแบบข้อมูล | เหตุผล |
|--------|---------|-------------|--------|
| Frontend ↔ Backend (สแกน) | WebSocket | Binary | ลด CPU overhead จาก Base64 encoding |
| Frontend ↔ Backend (API) | HTTP/REST | JSON | CRUD operations ทั่วไป |
| Backend ↔ Qdrant | gRPC (Persistent) | Protocol Buffers | เร็ว, ลด handshake overhead |
| Backend ↔ PostgreSQL | TCP (Connection Pool) | SQL | SQLAlchemy managed |
| Backend ↔ Redis | TCP | Binary | Active filter state |

---

## AI Model: InsightFace buffalo_l

| Spec | ค่า |
|------|-----|
| Embedding Size | 512 dimensions |
| Accuracy | ~99.7% (LFW benchmark) |
| Model Size | ~500 MB |
| RAM Usage | ~1.5 GB |
| Inference Time (CPU) | ~150-200ms / batch |
| Distance Metric | Cosine Similarity |

---

## OS Support

| OS | รองรับ | หมายเหตุ |
|----|--------|---------|
| Windows 11+ | ✅ | DirectML + CUDA (ถ้ามี NVIDIA) |
| Linux (Ubuntu 22.04+) | ✅ | CUDA + ROCm + CPU |
| macOS | ⚠️ | CPUExecutionProvider เท่านั้น (ไม่ได้ทดสอบ) |

---

## Hardware Requirements

### CPU-Only (ปัจจุบัน)

| Resource | Minimum | แนะนำ |
|----------|---------|-------|
| CPU | Ryzen 5000+ (Zen 3) | Ryzen 7000+ (Zen 4, AVX-512) |
| RAM | 16 GB | 32 GB |
| Storage | 50 GB | 100 GB |
| GPU | ไม่จำเป็น | ไม่จำเป็น |

### GPU (อนาคต / Cloud)

| Resource | Minimum | แนะนำ |
|----------|---------|-------|
| GPU | NVIDIA GTX 1060 6GB | NVIDIA RTX 3060+ |
| VRAM | 6 GB | 8 GB+ |
| CUDA | 11.8+ | 12.x |
| RAM | 16 GB | 32 GB |

### Cloud Instances แนะนำ

| Provider | Instance | GPU | ใช้เมื่อ |
|---------|---------|-----|--------|
| AWS | g4dn.xlarge | T4 16GB | Production scale |
| GCP | n1 + T4 | T4 16GB | Production scale |
| Azure | NC4as T4 v3 | T4 16GB | Production scale |

---

## ข้อมูลที่ไม่ใช้ (Rejected Options)

| Technology | เหตุผลที่ไม่เลือก |
|-----------|----------------|
| MediaPipe WASM | ทำงานซ้ำกับ Backend, เพิ่มความซับซ้อน Frontend โดยไม่จำเป็น |
| InsightFace buffalo_sc | ความแม่นยำต่ำกว่า 1.2% มีผลกับฐานพนักงาน 10,000 คน |
| Milvus | ซับซ้อนกว่า Qdrant สำหรับ use case นี้ |
| MongoDB | ไม่เหมาะกับ relational data ของระบบนี้ |
