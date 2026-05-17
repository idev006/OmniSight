# OmniSight — Architecture Decisions Log (ADL)

> บันทึกการตัดสินใจเชิงสถาปัตยกรรมและเทคนิคที่สำคัญ  
> เพื่อให้ทีม (และ AI sessions ถัดไป) เข้าใจ "ทำไม" ไม่ใช่แค่ "ทำอะไร"

---

## ADR-001 — เลือก InsightFace buffalo_l

**วันที่:** 2026-05-16  
**สถานะ:** ✅ Accepted

**บริบท:**  
ต้องการ face detection + landmark + embedding ในระบบเดียว สำหรับ 10,000+ คน

**การตัดสินใจ:**  
ใช้ `insightface` package พร้อม model `buffalo_l`

**เหตุผล:**
- all-in-one pipeline: RetinaFace (detection) + 2d106det (landmark) + ArcFace R100 (512d embedding)
- Pretrained บน MS1MV3 (5.8M images) — accuracy สูงมาก
- ONNX-based — รองรับ CPU / CUDA / DirectML โดยไม่ต้องเปลี่ยนโค้ด
- Community active, documentation ดี

**ทางเลือกที่ปฏิเสธ:**
- `face_recognition` (dlib-based) — ช้ากว่า, 128d เท่านั้น
- DeepFace — หนักกว่า, accuracy ต่ำกว่าในหลาย benchmark

---

## ADR-002 — เลือก Qdrant เป็น Vector Database

**วันที่:** 2026-05-16  
**สถานะ:** ✅ Accepted

**บริบท:**  
ต้องการ vector search สำหรับ 512d embeddings, รองรับ 10,000+ คน × 6 templates = 60,000+ vectors

**การตัดสินใจ:**  
ใช้ Qdrant พร้อม HNSW index + SQ8 (Scalar Quantization 8-bit)

**เหตุผล:**
- HNSW: approximate nearest neighbor, O(log N) search
- SQ8: ลด memory จาก 512×4 bytes = 2KB → 512B ต่อ vector (ลด 75%)
- Payload filtering: filter ด้วย `dept_id` ก่อน search — ลด search space
- Rust-based, performance สูง
- Docker image เล็ก, setup ง่าย

**Config ที่ใช้:**
```python
VectorParams(size=512, distance=Distance.COSINE)
ScalarQuantizationConfig(type=ScalarType.INT8, always_ram=True)
HnswConfigDiff(m=16, ef_construct=100)
```

**ทางเลือกที่ปฏิเสธ:**
- pgvector — อยู่ใน Postgres แต่ performance ต่ำกว่าสำหรับ scale นี้
- FAISS — ไม่มี built-in server, ต้องจัดการ persistence เอง
- Pinecone / Weaviate — Cloud-only หรือ complexity สูง

---

## ADR-003 — Redis เก็บ Station Department Filter

**วันที่:** 2026-05-16  
**สถานะ:** ✅ Accepted

**บริบท:**  
WebSocket scan รับ frame ทุก 200ms — ถ้า query Postgres ทุกครั้งจะ overhead สูง

**การตัดสินใจ:**  
เก็บ `dept_ids` ของแต่ละ station ใน Redis key `station:{id}:depts`

**เหตุผล:**
- WebSocket handler ไม่ต้อง query Postgres ทุก frame
- Redis read latency < 1ms (local)
- เมื่อ admin เปลี่ยน dept ของ station → update Redis ทันที (PUT /stations/:id/departments)

**Flow:**
```
Admin เปลี่ยน dept → PUT API → UPDATE Postgres + SET Redis key
WebSocket frame → GET Redis key → build Qdrant filter → search
```

---

## ADR-004 — 6 Face Templates ต่อพนักงาน

**วันที่:** 2026-05-16  
**สถานะ:** ✅ Accepted

**บริบท:**  
จำนวน template ที่เหมาะสมระหว่าง accuracy vs. storage vs. enrollment UX

**การตัดสินใจ:**  
กำหนด `MIN_TEMPLATES_TO_ACTIVATE = 6` slots (index 0–5)

**เหตุผล:**
- ครอบคลุมมุมใบหน้า: หน้าตรง, หันซ้าย/ขวา, เงย/ก้ม, แสงต่างกัน
- 6 vectors × 512B (SQ8) = 3KB ต่อคน → 10,000 คน = 30MB เท่านั้น
- UX: 6 slots เห็นได้ชัดในหน้า enrollment, ไม่มากเกินไป

---

## ADR-005 — WebSocket Binary JPEG (ไม่ใช่ Base64)

**วันที่:** 2026-05-16  
**สถานะ:** ✅ Accepted

**บริบท:**  
ส่ง video frame จาก browser ไป backend ทุก 200ms

**การตัดสินใจ:**  
ส่งเป็น binary `ArrayBuffer` (JPEG bytes) ผ่าน `ws.send(blob)`

**เหตุผล:**
- Base64 เพิ่มขนาด ~33% (3 bytes → 4 chars)
- Binary: 640×480 JPEG 70% ≈ 15-30KB
- Base64: ≈ 20-40KB
- ลด bandwidth และ decode time ฝั่ง backend

**Frontend code:**
```js
canvas.toBlob(blob => ws.send(blob), 'image/jpeg', 0.7)
```

**Backend code:**
```python
raw = await websocket.receive_bytes()
arr = np.frombuffer(raw, np.uint8)
frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
```

---

## ADR-006 — Virtual Environment บน F: Drive (ไม่ใช่ C:)

**วันที่:** 2026-05-16  
**สถานะ:** ✅ Accepted

**บริบท:**  
C: drive มีพื้นที่จำกัด, MSVC Build Tools และ Python packages มีขนาดใหญ่

**การตัดสินใจ:**  
- venv: `F:\programming\python\OmniSight\my_env`
- Build Tools: `F:\BuildTools`

**ผลที่ตามมา:**  
ต้องใช้ `DISTUTILS_USE_SDK=1` + `MSSdk=1` เมื่อ build C extension  
→ ดูรายละเอียดใน `doc/claude_version/other/lesson_learned_insightface_msvc_non_c_drive.md`

---

## ADR-007 — Hardcoded admin/admin สำหรับ MVP

**วันที่:** 2026-05-16  
**สถานะ:** ⚠️ Temporary — ต้องแก้ใน Phase 3

**บริบท:**  
MVP ต้องการ auth แต่ user management ยังไม่ได้ทำ

**การตัดสินใจ:**  
Hardcode `username=admin, password=admin` ใน auth.py

**เงื่อนไข:**
- ใช้ได้เฉพาะ dev/testing
- **ต้องเปลี่ยนก่อน production** เป็น DB-backed user management

---

## ADR-008 — Match Threshold 0.72 (Cosine Similarity)

**วันที่:** 2026-05-16  
**สถานะ:** ✅ Accepted (อาจ tune ได้)

**บริบท:**  
Cosine similarity ระหว่าง query embedding และ stored embedding

**การตัดสินใจ:**  
`MATCH_THRESHOLD = 0.72`

**เหตุผล:**
- buffalo_l ArcFace: cosine ≥ 0.72 = same person (empirical)
- ต่ำเกินไป (< 0.65) → false positive มาก
- สูงเกินไป (> 0.80) → false negative มาก (reject คนจริง)
- 0.72 เป็น baseline ที่ InsightFace แนะนำสำหรับ controlled environment

**ผลการทดสอบ:**  
confidence = 0.9957 สำหรับรูปเดียวกัน (expected: สูงมากเพราะรูปซ้ำ)  
ในการใช้งานจริง: คาดว่า 0.75–0.90 สำหรับภาพจากกล้อง
