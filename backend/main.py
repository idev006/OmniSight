from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.db.qdrant import init_collection
from app.core.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_collection()
    print(f"OmniSight started — ONNX Provider: {settings.onnxruntime_provider}")
    yield


app = FastAPI(
    title="OmniSight API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


from app.api import auth, departments, shifts, employees, stations, enrollment, attendance, websocket

app.include_router(auth.router,        prefix="/api/v1/auth",        tags=["auth"])
app.include_router(departments.router, prefix="/api/v1/departments",  tags=["departments"])
app.include_router(shifts.router,      prefix="/api/v1/shifts",       tags=["shifts"])
app.include_router(employees.router,   prefix="/api/v1/employees",    tags=["employees"])
app.include_router(stations.router,    prefix="/api/v1/stations",     tags=["stations"])
app.include_router(enrollment.router,  prefix="/api/v1/employees",    tags=["enrollment"])
app.include_router(attendance.router,  prefix="/api/v1/attendance",   tags=["attendance"])
app.include_router(websocket.router,   prefix="/api/v1/ws",           tags=["websocket"])
