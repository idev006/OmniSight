# Chapter 6: Data Schema & Class Design

## Dual-Database Strategy

| Database | ใช้เก็บ | เหตุผล |
|---------|--------|--------|
| PostgreSQL | Metadata, Relations, Logs | Structured data, Business logic |
| Qdrant | Face Embeddings (512d) | Vector similarity search |
| Redis | Active Filter State | Fast in-memory cache |
| Disk (/storage/faces/) | Original face images | ไม่เก็บรูปใน DB |

---

## PostgreSQL Schema

### Table: `departments`

```sql
CREATE TABLE departments (
    id         SMALLSERIAL PRIMARY KEY,
    name       VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ  DEFAULT NOW()
);
```

### Table: `shifts`

```sql
CREATE TABLE shifts (
    id         SMALLSERIAL PRIMARY KEY,
    name       VARCHAR(100) NOT NULL,  -- "กะเช้า"
    start_time TIME         NOT NULL,  -- 08:30
    end_time   TIME         NOT NULL   -- 17:30
);
```

> **หมายเหตุ:** Shift ใช้เพื่อ HR Report เท่านั้น ไม่ยุ่งกับ Logic การสแกน

### Table: `employees`

```sql
CREATE TABLE employees (
    id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    emp_code   VARCHAR(20)  UNIQUE NOT NULL,   -- รหัสพนักงาน
    full_name  VARCHAR(200) NOT NULL,
    dept_id    SMALLINT     NOT NULL REFERENCES departments(id),
    shift_id   SMALLINT     REFERENCES shifts(id),
    is_active  BOOLEAN      DEFAULT TRUE,
    created_at TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX idx_employees_dept ON employees(dept_id);
CREATE INDEX idx_employees_active ON employees(is_active);
```

### Table: `stations`

```sql
CREATE TABLE stations (
    id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    name       VARCHAR(200) NOT NULL,   -- "ประตูหน้า อาคาร A"
    location   VARCHAR(200),
    is_active  BOOLEAN      DEFAULT TRUE,
    created_at TIMESTAMPTZ  DEFAULT NOW()
);
```

### Table: `station_departments`

```sql
-- กล้อง 1 ตัว ดูแลได้ N แผนก
CREATE TABLE station_departments (
    station_id UUID     NOT NULL REFERENCES stations(id) ON DELETE CASCADE,
    dept_id    SMALLINT NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
    PRIMARY KEY (station_id, dept_id)
);

CREATE INDEX idx_sd_station ON station_departments(station_id);
```

### Table: `face_templates`

```sql
CREATE TABLE face_templates (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id   UUID         NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    qdrant_id     UUID         NOT NULL UNIQUE,  -- Point ID ใน Qdrant
    sample_index  SMALLINT     NOT NULL CHECK (sample_index BETWEEN 1 AND 6),
    image_path    VARCHAR(500) NOT NULL,          -- "{employee_id}/1.jpg"
    quality_score FLOAT        NOT NULL,
    created_at    TIMESTAMPTZ  DEFAULT NOW(),

    UNIQUE (employee_id, sample_index)            -- 1 คน ต่อ 1 ช่อง
);

CREATE INDEX idx_ft_employee ON face_templates(employee_id);
```

### Table: `attendance_logs`

```sql
CREATE TABLE attendance_logs (
    id               BIGSERIAL    PRIMARY KEY,
    employee_id      UUID         NOT NULL REFERENCES employees(id),
    station_id       UUID         NOT NULL REFERENCES stations(id),
    timestamp        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    confidence_score FLOAT        NOT NULL
);

CREATE INDEX idx_log_employee   ON attendance_logs(employee_id);
CREATE INDEX idx_log_station    ON attendance_logs(station_id);
CREATE INDEX idx_log_timestamp  ON attendance_logs(timestamp);
```

---

## Qdrant Collection: `face_registry`

```
Collection: face_registry

Vectors:
  size    : 512
  distance: Cosine

Payload per Point:
  employee_id  : string (UUID)
  dept_id      : integer        ← Indexed, ใช้ Pre-filter
  sample_index : integer (1-6)

Quantization:
  type  : scalar
  type  : int8
  always_ram: true

HNSW Config:
  m           : 16
  ef_construct: 100
  on_disk     : false
```

---

## File Storage Structure

```
/storage/faces/
└── {employee_id}/          ← UUID ของพนักงาน
    ├── 1.jpg               ← sample_index 1
    ├── 2.jpg
    ├── 3.jpg
    ├── 4.jpg
    ├── 5.jpg
    └── 6.jpg

ขนาดโดยประมาณ:
  6 รูป × 10,000 คน × 50 KB = ~3 GB
```

---

## Redis: Active Filter State

```
Key   : "station:{station_id}:filter"
Value : [dept_id_1, dept_id_2, ...]  (JSON Array)
TTL   : ไม่มี (คงอยู่จนกว่า Admin จะเปลี่ยน)
```

---

## Enrollment Rules

| กฎ | รายละเอียด |
|----|----------|
| รูปขั้นต่ำ | ต้องครบ **6 รูป** จึงจะ Active |
| แก้ไขรูป | เลือกแก้ทีละ sample_index ได้ |
| ลบพนักงาน | Cascade ลบ face_templates + Qdrant points + /storage/faces/{id}/ |
| ห้ามเก็บรูปใน DB | เก็บเฉพาะ image_path ใน face_templates |

---

## Entity Relationship (ภาพรวม)

```
departments ──< employees >── shifts
                   │
                   └──< face_templates (1-6 per employee)
                   │
                   └──< attendance_logs >── stations
                                                │
                                    station_departments >── departments
```

---

## Class Design (Python / Pydantic)

```python
class Department(BaseModel):
    id: int
    name: str

class Shift(BaseModel):
    id: int
    name: str
    start_time: time
    end_time: time

class Employee(BaseModel):
    id: UUID
    emp_code: str
    full_name: str
    dept_id: int
    shift_id: Optional[int]
    is_active: bool

class Station(BaseModel):
    id: UUID
    name: str
    location: Optional[str]
    is_active: bool
    dept_ids: List[int]    # จาก station_departments

class FaceTemplate(BaseModel):
    id: UUID
    employee_id: UUID
    qdrant_id: UUID
    sample_index: int      # 1-6
    image_path: str
    quality_score: float

class AttendanceLog(BaseModel):
    id: int
    employee_id: UUID
    station_id: UUID
    timestamp: datetime
    confidence_score: float
```
