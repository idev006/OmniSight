"""
load_test.py -- Simulate N cameras sending JPEG frames simultaneously.
Measures: round-trip latency (p50/p95/p99), throughput, error rate,
          backend memory and CPU usage.

Requirements: backend running at localhost:8000, Docker services up,
              at least 1 station in DB, employee data seeded.

Usage (from project root):
    my_env/Scripts/python.exe backend/scripts/load_test.py
    my_env/Scripts/python.exe backend/scripts/load_test.py --cameras 10 --fps 2 --duration 30
    my_env/Scripts/python.exe backend/scripts/load_test.py --cameras 20 --fps 5 --duration 60
"""
import asyncio
import argparse
import json
import time
import statistics
import uuid
import sys
from pathlib import Path

import httpx
import websockets
import numpy as np
import cv2
import psutil

BASE_HTTP = "http://localhost:8000"
BASE_WS   = "ws://localhost:8000"

# ── Synthetic frame ────────────────────────────────────────────────────────
_FRAME_CACHE: list[bytes] = []

def _build_frame_cache(n: int = 30, width: int = 320, height: int = 240):
    """Pre-generate N varied JPEG frames so workers don't stall on encode."""
    for _ in range(n):
        img = np.random.randint(40, 220, (height, width, 3), dtype=np.uint8)
        # Rough skin-tone rectangle (no real face — tests empty-detection path)
        cx, cy = width // 2 + np.random.randint(-20, 20), height // 2 + np.random.randint(-20, 20)
        cv2.rectangle(img, (cx - 35, cy - 45), (cx + 35, cy + 45), (180, 155, 130), -1)
        _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 70])
        _FRAME_CACHE.append(buf.tobytes())

_frame_idx = 0

def next_frame() -> bytes:
    global _frame_idx
    f = _FRAME_CACHE[_frame_idx % len(_FRAME_CACHE)]
    _frame_idx += 1
    return f


# ── Auth & station discovery ───────────────────────────────────────────────
async def get_token(username: str = "admin", password: str = "admin") -> str:
    async with httpx.AsyncClient(base_url=BASE_HTTP, timeout=10) as c:
        r = await c.post("/api/v1/auth/login",
                         json={"username": username, "password": password})
        r.raise_for_status()
        return r.json()["access_token"]


async def get_station_id(token: str) -> str:
    async with httpx.AsyncClient(base_url=BASE_HTTP, timeout=10) as c:
        r = await c.get("/api/v1/stations",
                        headers={"Authorization": f"Bearer {token}"})
        r.raise_for_status()
        stations = r.json()
        if not stations:
            raise RuntimeError("No stations found in DB. Create at least one station first.")
        return stations[0]["id"]


# ── Backend process monitor ────────────────────────────────────────────────
def _find_backend_proc() -> psutil.Process | None:
    """Find the uvicorn/python process listening on port 8000."""
    try:
        for conn in psutil.net_connections(kind="tcp"):
            if conn.laddr.port == 8000 and conn.status == "LISTEN" and conn.pid:
                return psutil.Process(conn.pid)
    except (psutil.AccessDenied, OSError):
        pass
    return None


async def monitor_backend(duration: float, interval: float = 1.0) -> dict:
    """Sample backend CPU% and RSS memory every `interval` seconds."""
    proc = _find_backend_proc()
    if proc is None:
        return {"error": "backend process not found on port 8000"}

    cpu_samples: list[float] = []
    mem_mb_samples: list[float] = []
    proc.cpu_percent()  # first call initialises the counter

    t0 = time.monotonic()
    while time.monotonic() - t0 < duration:
        await asyncio.sleep(interval)
        try:
            cpu_samples.append(proc.cpu_percent())
            mem_mb_samples.append(proc.memory_info().rss / 1024 / 1024)
        except psutil.NoSuchProcess:
            break

    return {
        "pid": proc.pid,
        "cpu_pct": cpu_samples,
        "mem_mb": mem_mb_samples,
    }


# ── Single camera worker ───────────────────────────────────────────────────
async def camera_worker(
    idx: int,
    station_id: str,
    token: str,
    fps: float,
    duration: float,
    out: dict,
):
    camera_id = f"lt{idx:03d}-{uuid.uuid4().hex[:6]}"
    url = f"{BASE_WS}/api/v1/ws/scan/{station_id}?token={token}&camera_id={camera_id}"
    interval = 1.0 / fps

    latencies_ms: list[float] = []
    frames_sent = 0
    frames_ok = 0
    errors = 0

    try:
        async with websockets.connect(
            url,
            ping_interval=None,
            max_size=4 * 1024 * 1024,
            open_timeout=10,
        ) as ws:
            deadline = time.monotonic() + duration
            while time.monotonic() < deadline:
                t0 = time.monotonic()

                await ws.send(next_frame())
                frames_sent += 1

                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=8.0)
                    rtt = (time.monotonic() - t0) * 1000
                    latencies_ms.append(rtt)
                    frames_ok += 1
                    # Optionally parse to verify response is valid JSON
                    # json.loads(raw)
                except asyncio.TimeoutError:
                    errors += 1

                # Pace to target FPS
                elapsed = time.monotonic() - t0
                sleep = max(0.0, interval - elapsed)
                if sleep > 0:
                    await asyncio.sleep(sleep)

    except Exception as e:
        errors += 1
        print(f"  [camera {idx:03d}] connection error: {e}")

    out[idx] = {
        "latencies_ms": latencies_ms,
        "frames_sent": frames_sent,
        "frames_ok": frames_ok,
        "errors": errors,
    }


# ── Report ─────────────────────────────────────────────────────────────────
def _pct(data: list[float], p: float) -> float:
    if not data:
        return 0.0
    return float(np.percentile(data, p))


def print_report(
    n_cameras: int,
    fps: float,
    duration: float,
    results: dict,
    monitor: dict,
):
    all_lat: list[float] = []
    total_sent = total_ok = total_err = 0

    for r in results.values():
        all_lat.extend(r["latencies_ms"])
        total_sent += r["frames_sent"]
        total_ok   += r["frames_ok"]
        total_err  += r["errors"]

    throughput = total_ok / duration

    print()
    print("=" * 60)
    print("  LOAD TEST RESULTS")
    print("=" * 60)
    print(f"  Cameras       : {n_cameras}")
    print(f"  Target FPS    : {fps} fps/camera  ({fps * n_cameras:.1f} fps total)")
    print(f"  Duration      : {duration:.0f}s")
    print("-" * 60)
    print(f"  Frames sent   : {total_sent:,}")
    print(f"  Frames OK     : {total_ok:,}")
    print(f"  Errors        : {total_err}")
    print(f"  Error rate    : {total_err/max(total_sent,1)*100:.2f}%")
    print(f"  Throughput    : {throughput:.1f} frames/s (actual processed)")
    print("-" * 60)

    if all_lat:
        print(f"  Latency (ms)  : min={min(all_lat):.1f}  "
              f"p50={_pct(all_lat,50):.1f}  "
              f"p95={_pct(all_lat,95):.1f}  "
              f"p99={_pct(all_lat,99):.1f}  "
              f"max={max(all_lat):.1f}")
    else:
        print("  Latency       : no data")

    print("-" * 60)

    if "error" in monitor:
        print(f"  Backend proc  : {monitor['error']}")
    else:
        cpu = monitor.get("cpu_pct", [])
        mem = monitor.get("mem_mb", [])
        pid = monitor.get("pid", "?")
        cpu_str = f"avg={statistics.mean(cpu):.1f}%  max={max(cpu):.1f}%" if cpu else "n/a"
        mem_str = f"avg={statistics.mean(mem):.0f}MB  max={max(mem):.0f}MB" if mem else "n/a"
        print(f"  Backend PID   : {pid}")
        print(f"  Backend CPU   : {cpu_str}")
        print(f"  Backend RAM   : {mem_str}")

    print("=" * 60)

    # Per-camera detail
    print("\n  Per-camera summary:")
    print(f"  {'cam':>4}  {'sent':>6}  {'ok':>6}  {'err':>4}  {'p50ms':>7}  {'p95ms':>7}")
    print("  " + "-" * 46)
    for idx in sorted(results):
        r = results[idx]
        lat = r["latencies_ms"]
        p50 = f"{_pct(lat,50):.1f}" if lat else "-"
        p95 = f"{_pct(lat,95):.1f}" if lat else "-"
        print(f"  {idx:>4}  {r['frames_sent']:>6}  {r['frames_ok']:>6}  "
              f"{r['errors']:>4}  {p50:>7}  {p95:>7}")
    print()


# ── Entry point ────────────────────────────────────────────────────────────
async def run(cameras: int, fps: float, duration: float, username: str, password: str):
    print(f"\n{'='*60}")
    print(f"  OmniSight Load Test")
    print(f"  {cameras} cameras  x  {fps} fps  x  {duration:.0f}s")
    print(f"{'='*60}")

    print("\n-> Authenticating ...")
    token = await get_token(username, password)
    print(f"   Token: {token[:24]}...")

    print("-> Looking up station ...")
    station_id = await get_station_id(token)
    print(f"   Station ID: {station_id}")

    print(f"-> Pre-generating synthetic frames ...")
    _build_frame_cache(n=60)
    print(f"   {len(_FRAME_CACHE)} frames cached")

    print(f"\n-> Starting {cameras} camera workers for {duration:.0f}s ...\n")

    results: dict = {}
    monitor_task = asyncio.create_task(monitor_backend(duration + 2))

    workers = [
        asyncio.create_task(
            camera_worker(i, station_id, token, fps, duration, results)
        )
        for i in range(cameras)
    ]

    await asyncio.gather(*workers)
    monitor_data = await monitor_task

    print_report(cameras, fps, duration, results, monitor_data)


def main():
    ap = argparse.ArgumentParser(description="OmniSight WebSocket load test")
    ap.add_argument("--cameras",  type=int,   default=10,    help="Number of concurrent camera connections (default: 10)")
    ap.add_argument("--fps",      type=float, default=2.0,   help="Frames per second per camera (default: 2.0)")
    ap.add_argument("--duration", type=float, default=30.0,  help="Test duration in seconds (default: 30)")
    ap.add_argument("--username", type=str,   default="admin")
    ap.add_argument("--password", type=str,   default="admin")
    args = ap.parse_args()
    asyncio.run(run(args.cameras, args.fps, args.duration, args.username, args.password))


if __name__ == "__main__":
    main()
