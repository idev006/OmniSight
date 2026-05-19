# Chapter 4: AI & Hardware Optimization

## หลักการ: "Auto-detect ใช้ Hardware ดีที่สุดที่มี"

ระบบตรวจสอบ Hardware ตอน Startup แล้วเลือก Execution Provider ที่เหมาะสมโดยอัตโนมัติ ไม่ต้องแก้โค้ดเมื่อเปลี่ยน Environment

---

## AI Model: InsightFace buffalo_l

### ทำไมถึงเลือก buffalo_l

| เหตุผล | รายละเอียด |
|--------|----------|
| ความแม่นยำ | ~99.7% LFW benchmark — สำคัญมากสำหรับ 10,000 คน |
| Embedding Quality | 512 dimensions ให้ Feature ที่ครอบคลุมทุกมุมหน้า |
| CPU Friendly | ออกแบบมาให้รันบน ONNX Runtime ได้ดี |
| Battle-tested | ใช้ในระบบ Production จริงทั่วโลก |

### ทำไมไม่ใช้ buffalo_sc

- ความแม่นยำต่างกัน 1.2% ดูเล็กน้อย แต่กับพนักงาน 10,000 คน
- หน้าตาคล้ายกัน = โอกาส False Positive สูงขึ้น
- buffalo_l รันได้สบายบน Ryzen 16GB RAM

---

## ONNX Runtime: Auto-detect Provider

### Provider Priority (ลำดับความสำคัญ)

```
1. CUDAExecutionProvider      → NVIDIA GPU (Cloud / Local GPU)
2. DirectMLExecutionProvider  → Windows + AMD/Intel iGPU
3. ROCmExecutionProvider      → Linux + AMD GPU
4. CPUExecutionProvider       → Fallback (ปัจจุบัน)
```

### Auto-detect Logic

```python
import onnxruntime as ort
from multiprocessing import cpu_count

def get_best_provider() -> list:
    available = ort.get_available_providers()
    priority = [
        'CUDAExecutionProvider',
        'DirectMLExecutionProvider',
        'ROCmExecutionProvider',
        'CPUExecutionProvider',
    ]
    for provider in priority:
        if provider in available:
            return [provider]
    return ['CPUExecutionProvider']

def build_session(model_path: str) -> ort.InferenceSession:
    providers = get_best_provider()
    opts = ort.SessionOptions()

    if providers[0] == 'CPUExecutionProvider':
        opts.intra_op_num_threads = cpu_count()
        opts.inter_op_num_threads = 2
        opts.graph_optimization_level = (
            ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        )

    return ort.InferenceSession(model_path, opts, providers=providers)
```

### Performance เปรียบเทียบ

| Provider | Hardware | Inference (10 faces) | หมายเหตุ |
|---------|---------|---------------------|---------|
| CUDAExecutionProvider | NVIDIA T4 | ~30ms | Cloud standard |
| DirectMLExecutionProvider | Radeon iGPU | ~80ms | Windows bonus |
| CPUExecutionProvider | Ryzen 7xxx | ~200ms | ปัจจุบัน |

### Dependencies ตาม Provider

| Provider | Package เพิ่มเติม | OS |
|---------|----------------|-----|
| CUDA | `onnxruntime-gpu` + CUDA 11.8+ | Linux / Windows |
| DirectML | `onnxruntime-directml` | Windows 11+ เท่านั้น |
| ROCm | `onnxruntime-rocm` | Linux เท่านั้น |
| CPU | `onnxruntime` | ทุก OS |

```
# requirements.txt จัดการโดย environment variable
ONNXRUNTIME_PROVIDER=cpu   → pip install onnxruntime
ONNXRUNTIME_PROVIDER=cuda  → pip install onnxruntime-gpu
ONNXRUNTIME_PROVIDER=dml   → pip install onnxruntime-directml
```

---

## Hardware Optimization Strategy

### 0. GPU Path (เมื่อมี NVIDIA GPU)

เมื่อใช้ CUDAExecutionProvider ระบบจะเร็วขึ้นอัตโนมัติ:

```
CPU Path: Frame → CPU Inference (~200ms) → Qdrant → Result
GPU Path: Frame → GPU Inference (~30ms)  → Qdrant → Result
```

GPU ช่วยได้มากในส่วน **Inference** เท่านั้น Qdrant ยังรันบน CPU เหมือนเดิม

### 1. AVX-512 & VNNI (Ryzen Zen 4+ — CPU Path)

ONNX Runtime ดึงใช้ชุดคำสั่ง AVX-512 โดยอัตโนมัติเมื่อ CPU รองรับ

```
ปกติ: คูณเลข 1 ชุด / cycle
AVX-512: คูณเลข 16 ชุด / cycle → เร็วขึ้น 3-5x สำหรับ AI workload
```

ไม่ต้องเขียนโค้ดพิเศษ — ONNX Runtime จัดการให้อัตโนมัติ

### 2. Batch Inference (10 Faces พร้อมกัน)

```
❌ แบบผิด: Loop ส่งทีละหน้า 10 รอบ
   → 10 × 200ms = 2,000ms

✅ แบบถูก: ส่ง 10 หน้าเป็น Single Tensor Batch
   → 1 × 220ms = 220ms  (overhead เพิ่มนิดเดียว)
```

### 3. Int8 Quantization

```
Float32 Model → Int8 Quantized Model
RAM: ลดลง 4x  (~500MB → ~125MB)
Speed: เพิ่ม 2-3x
Accuracy: ลด < 0.5% (ยอมรับได้)
```

### 4. Core Affinity (แนะนำ)

```
AI Workers (Inference)  → Pin บน Performance Cores
API Workers (FastAPI)   → รันบน Cores ที่เหลือ
```

ป้องกัน Context Switching ระหว่าง AI กับ API

### 5. Model Preloading

```python
# โหลด Model ครั้งเดียวตอน Server Start
# ห้าม Load ซ้ำต่อ Request เด็ดขาด
@app.on_event("startup")
async def load_model():
    app.state.face_engine = FaceAnalysis(
        name='buffalo_l',
        providers=['CPUExecutionProvider']
    )
    app.state.face_engine.prepare(ctx_id=0, det_size=(640, 640))
```

---

## Inference Pipeline

```
รับภาพ Frame
    ↓
Resize → 640x640 (ลด CPU load)
    ↓
Detection: หาตำแหน่งใบหน้าทั้งหมดในเฟรม
    ↓
Crop: ตัดแต่ละใบหน้าออกมา
    ↓
Batch: รวมทุกใบหน้าเป็น Single Tensor
    ↓
Embedding: ONNX Runtime → 512d Vectors
    ↓
ส่งต่อไปยัง Qdrant Search
```

---

## Worker Architecture

```
FastAPI Process
├── API Workers (2-4 threads)
│   └── รับ HTTP request, WebSocket management
│
└── Inference Workers (N threads = CPU cores / 2)
    └── รับ face crops, คืน embeddings
        ├── Worker 1: ประมวลผล Batch A
        ├── Worker 2: ประมวลผล Batch B
        └── Worker N: ...
```

ใช้ `asyncio.run_in_executor` เพื่อป้องกัน Blocking event loop

---

## RAM Usage Estimation (16GB)

| Component | RAM ที่ใช้ |
|-----------|----------|
| OS + System | ~2 GB |
| FastAPI + Python | ~0.5 GB |
| buffalo_l Model (Int8) | ~0.5 GB |
| Qdrant HNSW Index (60k vectors) | ~0.5 GB |
| PostgreSQL | ~0.3 GB |
| Redis | ~0.1 GB |
| **รวม** | **~4 GB** |
| **เหลือ Buffer** | **~12 GB** |

RAM 16GB เพียงพอมาก ไม่มีปัญหา

---

## Performance Benchmark (เป้าหมาย)

| Scenario | Latency เป้าหมาย |
|---------|----------------|
| 1 face, full pipeline | < 200ms |
| 5 faces, batch | < 250ms |
| 10 faces, batch | < 300ms |
| Qdrant search (100 person scope) | < 5ms |
| Qdrant search (10,000 person scope) | < 15ms |
