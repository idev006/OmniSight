from pydantic import BaseModel, UUID4
from typing import Optional
from datetime import time, datetime


# --- Department ---
class DepartmentCreate(BaseModel):
    name: str

class DepartmentOut(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


# --- Shift ---
class ShiftCreate(BaseModel):
    name: str
    start_time: time
    end_time: time

class ShiftOut(BaseModel):
    id: int
    name: str
    start_time: time
    end_time: time
    model_config = {"from_attributes": True}


# --- Employee ---
class EmployeeCreate(BaseModel):
    emp_code: str
    full_name: str
    dept_id: int
    shift_id: Optional[int] = None

class EmployeeOut(BaseModel):
    id: UUID4
    emp_code: str
    full_name: str
    dept_id: int
    shift_id: Optional[int]
    is_active: bool
    enrollment_count: int = 0
    is_enrollment_complete: bool = False
    model_config = {"from_attributes": True}


# --- Station ---
class StationCreate(BaseModel):
    name: str
    location: Optional[str] = None

class StationOut(BaseModel):
    id: UUID4
    name: str
    location: Optional[str]
    is_active: bool
    dept_ids: list[int] = []
    model_config = {"from_attributes": True}

class StationDeptUpdate(BaseModel):
    dept_ids: list[int]


# --- Face Template ---
class FaceTemplateOut(BaseModel):
    sample_index: int
    quality_score: float
    created_at: Optional[datetime]
    model_config = {"from_attributes": True}

class EnrollmentStatus(BaseModel):
    employee_id: UUID4
    slots: list[Optional[FaceTemplateOut]]
    completed: int
    is_ready: bool


# --- Attendance Log ---
class AttendanceLogOut(BaseModel):
    id: int
    employee_id: UUID4
    station_id: UUID4
    timestamp: datetime
    confidence_score: float
    model_config = {"from_attributes": True}


# --- WebSocket Scan Result ---
class BBox(BaseModel):
    x: int
    y: int
    w: int
    h: int

class FaceResult(BaseModel):
    tracking_id: int
    status: str                          # "match" | "unknown"
    employee_id: Optional[UUID4] = None
    full_name: Optional[str] = None
    dept_name: Optional[str] = None
    emp_code: Optional[str] = None
    confidence: float = 0.0
    bbox: BBox
    attendance_logged: bool = False      # True = บันทึกเวลาแล้ว, False = cooldown หรือ unknown

class ScanResult(BaseModel):
    timestamp: datetime
    faces: list[FaceResult]


# --- Auth ---
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
