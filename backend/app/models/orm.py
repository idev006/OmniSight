from sqlalchemy import (
    Column, String, Boolean, SmallInteger, Float,
    DateTime, ForeignKey, Time, BigInteger, UniqueConstraint,
    Text, text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.postgres import Base
import uuid


class Department(Base):
    __tablename__ = "departments"
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))
    employees = relationship("Employee", back_populates="department")


class Shift(Base):
    __tablename__ = "shifts"
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    employees = relationship("Employee", back_populates="shift")


class Employee(Base):
    __tablename__ = "employees"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    emp_code = Column(String(20), unique=True, nullable=False)
    full_name = Column(String(200), nullable=False)
    dept_id = Column(SmallInteger, ForeignKey("departments.id"), nullable=False)
    shift_id = Column(SmallInteger, ForeignKey("shifts.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))
    department = relationship("Department", back_populates="employees")
    shift = relationship("Shift", back_populates="employees")
    face_templates = relationship("FaceTemplate", back_populates="employee", cascade="all, delete-orphan")
    attendance_logs = relationship("AttendanceLog", back_populates="employee")


class Station(Base):
    __tablename__ = "stations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    location = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))
    station_departments = relationship("StationDepartment", back_populates="station", cascade="all, delete-orphan")
    attendance_logs = relationship("AttendanceLog", back_populates="station")


class StationDepartment(Base):
    __tablename__ = "station_departments"
    station_id = Column(UUID(as_uuid=True), ForeignKey("stations.id", ondelete="CASCADE"), primary_key=True)
    dept_id = Column(SmallInteger, ForeignKey("departments.id", ondelete="CASCADE"), primary_key=True)
    station = relationship("Station", back_populates="station_departments")
    department = relationship("Department")


class FaceTemplate(Base):
    __tablename__ = "face_templates"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    qdrant_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    sample_index = Column(SmallInteger, nullable=False)
    image_path = Column(String(500), nullable=False)
    quality_score = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))
    employee = relationship("Employee", back_populates="face_templates")
    __table_args__ = (UniqueConstraint("employee_id", "sample_index"),)


class AttendanceLog(Base):
    __tablename__ = "attendance_logs"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    station_id = Column(UUID(as_uuid=True), ForeignKey("stations.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    confidence_score = Column(Float, nullable=False)
    employee = relationship("Employee", back_populates="attendance_logs")
    station = relationship("Station", back_populates="attendance_logs")


# ─── User & RBAC ──────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    full_name = Column(String(200), nullable=True)
    role = Column(String(20), nullable=False, default="OPERATOR")  # ADMIN | HR | OPERATOR
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))
    user_stations = relationship("UserStation", back_populates="user", cascade="all, delete-orphan")


class UserStation(Base):
    """OPERATOR access control — กำหนดว่า user นี้ใช้ station ไหนได้บ้าง"""
    __tablename__ = "user_stations"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    station_id = Column(UUID(as_uuid=True), ForeignKey("stations.id", ondelete="CASCADE"), primary_key=True)
    user = relationship("User", back_populates="user_stations")
    station = relationship("Station")


# ─── Camera ───────────────────────────────────────────────────────────────────

class Camera(Base):
    __tablename__ = "cameras"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    station_id = Column(UUID(as_uuid=True), ForeignKey("stations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    camera_type = Column(String(20), nullable=False)   # WEBCAM | IP_CAMERA | CCTV | SMARTPHONE
    rtsp_url = Column(String(500), nullable=True)
    authorized_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))
    station = relationship("Station")
    authorized_user = relationship("User")


# ─── System Settings ──────────────────────────────────────────────────────────

class SystemSetting(Base):
    """Live config — เปลี่ยนได้ขณะระบบทำงาน ไม่ต้อง restart"""
    __tablename__ = "system_settings"
    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    value_type = Column(String(20), nullable=False, default="string")  # float|int|bool|string
    description = Column(Text, nullable=True)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=text("NOW()"), onupdate=text("NOW()"))
