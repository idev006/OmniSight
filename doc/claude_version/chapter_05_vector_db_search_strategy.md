# Chapter 5: Vector DB & Search Strategy

## ทำไมต้องใช้ Vector Database

พนักงาน 10,000 คน × 6 รูป = **60,000 Embeddings (512 dimensions)**

```
Linear Search: เทียบทีละเวกเตอร์ 60,000 ครั้ง
→ CPU ต้องคำนวณ distance 60,000 ครั้ง/คน
→ 10 คนพร้อมกัน = 600,000 การคำนวณ
→ ช้าแน่นอน

HNSW Index (Vector DB):
→ ค้นหาแบบ "กระโดด" ผ่านโครงสร้าง Graph
→ O(log N) แทน O(N)
→ 60,000 vectors → ผลในเวลา < 10ms
```

---

## Qdrant: เหตุผลที่เลือก

| เหตุผล | รายละเอียด |
|--------|----------|
| Payload Filtering | กรองด้วย dept_id ก่อน Search ได้ทันที |
| Batch Search API | ส่ง 10 vectors พร้อมกันในคำสั่งเดียว |
| Scalar Quantization | บีบอัด vector ลด RAM 4x |
| Docker Native | Deploy ง่าย |
| gRPC Support | เชื่อมต่อ persistent connection เร็วมาก |

---

## Collection Design: `face_registry`

```
Collection: face_registry

Vector Config:
  size: 512
  distance: Cosine

Payload Fields:
  employee_id : UUID    (link กลับ PostgreSQL)
  dept_id     : Integer (ใช้ Pre-filter ← สำคัญที่สุด)
  sample_index: Integer (1-6)

Payload Index:
  dept_id → Indexed (ต้อง Index เพื่อให้ Filter เร็ว)
```

---

## HNSW Index Configuration

```
hnsw_config:
  m: 16              # จำนวน edges ต่อ node (accuracy vs speed)
  ef_construct: 100  # ความแม่นยำตอนสร้าง index
  on_disk: false     # เก็บใน RAM เพื่อความเร็ว
```

**ef_search: 50** ใช้ตอน query (ยิ่งสูง ยิ่งแม่น แต่ช้ากว่า)

---

## Scalar Quantization (SQ8)

```
Float32 Vector (512d):
  ขนาด: 512 × 4 bytes = 2,048 bytes/vector
  60,000 vectors = ~120 MB

SQ8 Quantized Vector (512d):
  ขนาด: 512 × 1 byte = 512 bytes/vector
  60,000 vectors = ~30 MB

ประหยัด RAM: 4x
ลดความแม่นยำ: < 0.5%
```

---

## Search Strategy: Pre-filtered Batch Search

### Flow เมื่อมี 10 คนในเฟรม

```
รับ 10 Embeddings จาก ONNX
    ↓
ดึง dept_ids ของ Station นี้จาก Redis
→ [101, 102] (แผนกสืบสวน, แผนกป้องกัน)
    ↓
Qdrant Batch Search:
  queries: [embedding_1, ..., embedding_10]
  filter: { dept_id: { "any": [101, 102] } }
  limit: 1 (Top-1 Match per face)
  score_threshold: 0.6
    ↓
รับผลลัพธ์: [{employee_id, score}, ...] × 10
    ↓
ดึง Metadata จาก PostgreSQL ด้วย employee_ids
```

### ผลของ Pre-filtering

```
ไม่มี Filter: ค้นหาจาก 60,000 vectors
มี Filter (dept 101, 102):
  พนักงาน 2 แผนก × 6 vectors × 300 คน/แผนก
  = ค้นหาจาก ~3,600 vectors เท่านั้น
  
ความเร็ว: เร็วขึ้น ~17x
Accuracy: ดีขึ้น (search space เล็กลง = false positive น้อยลง)
```

---

## Score Threshold

| Score | ความหมาย | Action |
|-------|---------|--------|
| > 0.85 | Match ชัดเจน | ✅ ระบุตัวตน + บันทึก Log |
| 0.65 - 0.85 | Match ไม่แน่ใจ | ⚠️ ระบุตัวตน แต่ confidence ต่ำ |
| < 0.65 | ไม่ Match | ❌ Unknown |

**Recommended threshold: 0.72** (ปรับได้ผ่าน Admin)

---

## Multi-Vector Strategy (6 รูปต่อคน)

พนักงาน 1 คน มี 6 Points ใน Qdrant (sample_index 1-6)

```
ผลการค้นหาอาจได้:
  Employee A, score 0.91 (sample_index 2)
  Employee A, score 0.88 (sample_index 1)
  Employee A, score 0.79 (sample_index 5)

→ ใช้ Best Match (score สูงสุด) = Employee A, 0.91
```

**ข้อดี:** พนักงานเดินผ่านมุมใดก็ Match ได้ ไม่ต้องหันหน้าตรงเสมอ

---

## Enrollment: บันทึก Vector ใหม่

```
ถ่ายรูปใหม่ → ONNX Inference → Embedding
    ↓
ถ้าเป็น sample_index ใหม่ → Insert Point
ถ้าแก้ไขรูปเดิม → Delete old Point → Insert new Point
    ↓
อัปเดต face_templates ใน PostgreSQL
  (บันทึก qdrant_id ใหม่)
```

---

## Qdrant Collection Operations

| Operation | เมื่อไหร่ |
|-----------|---------|
| `upsert_points` | ลงทะเบียนหรืออัปเดตใบหน้า |
| `delete_points` | ลบ Vector เมื่อแก้ไขรูป หรือพนักงานลาออก |
| `search_batch` | สแกนหน้า (Batch ทุกครั้ง) |
| `set_payload_index` | ตอน Setup (Index dept_id) |
| `create_collection` | ตอน Initialize ระบบครั้งแรก |
