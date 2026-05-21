from pydantic import BaseModel, UUID4
from typing import Optional, Literal
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

class EmployeePage(BaseModel):
    items: list[EmployeeOut]
    total: int
    page: int
    page_size: int


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
    image_url: Optional[str] = None   # populated at runtime — not stored in DB
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
    status: str                          # "match" | "unknown" | "spoof"
    employee_id: Optional[UUID4] = None
    full_name: Optional[str] = None
    dept_name: Optional[str] = None
    emp_code: Optional[str] = None
    confidence: float = 0.0
    bbox: BBox
    attendance_logged: bool = False      # True = บันทึกเวลาแล้ว, False = cooldown หรือ unknown

# --- Auth ---
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- User ---
class UserCreate(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    role: Literal["ADMIN", "HR", "OPERATOR"] = "OPERATOR"

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[Literal["ADMIN", "HR", "OPERATOR"]] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

class UserOut(BaseModel):
    id: UUID4
    username: str
    full_name: Optional[str]
    role: str
    is_active: bool
    station_ids: list[str] = []
    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_user(cls, user) -> "UserOut":
        obj = cls.model_validate(user)
        if hasattr(user, "user_stations") and user.user_stations is not None:
            obj.station_ids = [str(us.station_id) for us in user.user_stations]
        return obj

class UserStationUpdate(BaseModel):
    station_ids: list[str]


# --- Camera ---
class CameraCreate(BaseModel):
    station_id: UUID4
    name: str
    camera_type: Literal["WEBCAM", "IP_CAMERA", "CCTV", "SMARTPHONE"]
    rtsp_url: Optional[str] = None
    authorized_user_id: Optional[UUID4] = None
    description: Optional[str] = None

class CameraUpdate(BaseModel):
    name: Optional[str] = None
    camera_type: Optional[Literal["WEBCAM", "IP_CAMERA", "CCTV", "SMARTPHONE"]] = None
    rtsp_url: Optional[str] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None

class CameraOut(BaseModel):
    id: UUID4
    station_id: UUID4
    name: str
    camera_type: str
    rtsp_url: Optional[str] = None
    is_active: bool
    description: Optional[str] = None
    live_status: str = "offline"    # active | paused | offline  (runtime, not DB)
    live_fps: float = 0.0           # runtime
    model_config = {"from_attributes": True}


# --- System Setting ---
class SystemSettingOut(BaseModel):
    key: str
    value: str
    value_type: str
    description: Optional[str]
    liveness: str = "live"          # live | graceful | restart  (runtime)
    model_config = {"from_attributes": True}

class SystemSettingUpdate(BaseModel):
    value: str


# --- ScanResult (updated) ---
class ScanResult(BaseModel):
    timestamp: datetime
    camera_id: str = ""
    faces: list["FaceResult"]
