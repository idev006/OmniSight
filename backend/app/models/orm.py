from sqlalchemy import (
    Column, String, Boolean, SmallInteger, Float,
    DateTime, ForeignKey, Time, BigInteger, UniqueConstraint,
    text,
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
