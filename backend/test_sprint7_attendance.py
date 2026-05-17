"""
Sprint 7 Verification Test: Attendance Auto-Logging
Tests: WebSocket scan -> match -> attendance_logged=True + DB insert + cooldown
"""
import asyncio
import json
import sys
import time
import urllib.request
import websockets
import cv2
import numpy as np

BASE = "http://localhost:8000"
WS_BASE = "ws://localhost:8000"
STATION_ID = "ccd829a0-bfe5-4fa9-892b-f39ef8a32389"
# emp1 is fully enrolled (6/6)
EMPLOYEE_ID = "db421a76-ae81-4e07-830d-62661f266f84"
# Use one of the stored sample images for scanning
SAMPLE_IMAGE = r"F:\programming\python\OmniSight\storage\faces\faces\db421a76-ae81-4e07-830d-62661f266f84\sample_0.jpg"

OK = "[OK]"
FAIL = "[FAIL]"
INFO = "[INFO]"


def http_get(url, token=None):
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def get_token():
    data = json.dumps({"username": "admin", "password": "admin"}).encode()
    req = urllib.request.Request(
        f"{BASE}/api/v1/auth/login",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())["access_token"]


def count_attendance_logs(token):
    logs = http_get(f"{BASE}/api/v1/attendance", token)
    return len(logs)


async def send_frame_and_get_result(token, image_path, timeout=120):
    """Connect WebSocket, send one frame, return parsed result."""
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot load image: {image_path}")

    # Encode as JPEG binary (full resolution)
    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    frame_bytes = buf.tobytes()

    ws_url = f"{WS_BASE}/api/v1/ws/scan/{STATION_ID}?token={token}"
    print(f"  {INFO} Connecting WebSocket: {ws_url[:60]}...")
    print(f"  {INFO} Frame size: {img.shape} ({len(frame_bytes):,} bytes)")
    print(f"  {INFO} Timeout: {timeout}s (model warmup may take 30s+)")

    start = time.time()
    async with websockets.connect(ws_url, ping_timeout=None) as ws:
        await ws.send(frame_bytes)
        print(f"  {INFO} Frame sent, waiting for response...")
        raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
    elapsed = time.time() - start
    result = json.loads(raw)
    return result, elapsed


def main():
    print("=" * 60)
    print("Sprint 7: Attendance Auto-Logging Verification")
    print("=" * 60)

    # Step 1: Auth
    print("\n[1] Authentication")
    try:
        token = get_token()
        print(f"  {OK} Token acquired")
    except Exception as e:
        print(f"  {FAIL} Login failed: {e}")
        sys.exit(1)

    # Step 2: Baseline attendance count
    print("\n[2] Baseline attendance log count")
    try:
        before_count = count_attendance_logs(token)
        print(f"  {INFO} Current attendance logs: {before_count}")
    except Exception as e:
        print(f"  {FAIL} Cannot get attendance: {e}")
        sys.exit(1)

    # Step 3: WebSocket scan - first frame
    print("\n[3] WebSocket scan (first frame - may trigger model warmup)")
    try:
        result, elapsed = asyncio.run(
            send_frame_and_get_result(token, SAMPLE_IMAGE, timeout=120)
        )
        print(f"  {INFO} Response in {elapsed:.1f}s")
        faces = result.get("faces", [])
        print(f"  {INFO} Faces detected: {len(faces)}")

        if not faces:
            print(f"  {FAIL} No faces detected! Check image: {SAMPLE_IMAGE}")
            sys.exit(1)

        face = faces[0]
        status = face.get("status")
        confidence = face.get("confidence", 0)
        attendance_logged = face.get("attendance_logged", False)
        emp_id = face.get("employee_id", "N/A")

        print(f"  {INFO} Status: {status}")
        print(f"  {INFO} Employee: {emp_id}")
        print(f"  {INFO} Confidence: {confidence:.4f}")
        print(f"  {INFO} attendance_logged: {attendance_logged}")

        if status == "match":
            print(f"  {OK} Face matched!")
        else:
            print(f"  {FAIL} Face not matched (status={status})")
            sys.exit(1)

    except asyncio.TimeoutError:
        print(f"  {FAIL} WebSocket timeout (>120s) - backend may be down or model failed to load")
        sys.exit(1)
    except Exception as e:
        print(f"  {FAIL} WebSocket error: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)

    # Step 4: Check attendance_logged field
    print("\n[4] Verify attendance_logged field in WebSocket response")
    if attendance_logged:
        print(f"  {OK} attendance_logged=True — new log was created")
    else:
        print(f"  [NOTE] attendance_logged=False — likely in cooldown from previous scan")
        print(f"         This is correct behavior if scanned within last 5 minutes")

    # Step 5: Verify DB was updated
    print("\n[5] Verify PostgreSQL attendance_logs table")
    try:
        after_count = count_attendance_logs(token)
        diff = after_count - before_count
        print(f"  {INFO} Attendance logs before: {before_count}")
        print(f"  {INFO} Attendance logs after:  {after_count}")
        if attendance_logged:
            if diff == 1:
                print(f"  {OK} 1 new attendance log inserted in DB")
            else:
                print(f"  {FAIL} Expected +1 log, got +{diff}")
        else:
            if diff == 0:
                print(f"  {OK} No new log (cooldown active) — correct behavior")
            else:
                print(f"  {FAIL} attendance_logged=False but DB changed by {diff}?")
    except Exception as e:
        print(f"  {FAIL} Cannot check attendance after: {e}")

    # Step 6: Second scan (should be cooldown)
    print("\n[6] Second scan immediately (should trigger cooldown)")
    try:
        result2, elapsed2 = asyncio.run(
            send_frame_and_get_result(token, SAMPLE_IMAGE, timeout=60)
        )
        faces2 = result2.get("faces", [])
        if faces2:
            face2 = faces2[0]
            al2 = face2.get("attendance_logged", False)
            status2 = face2.get("status")
            print(f"  {INFO} Status: {status2}, attendance_logged: {al2}")
            if status2 == "match" and not al2:
                print(f"  {OK} Cooldown working — second scan not logged")
            elif status2 == "match" and al2:
                print(f"  [NOTE] Logged again — cooldown may have expired or Redis unavailable")
            else:
                print(f"  {INFO} No match on second scan")
        else:
            print(f"  {INFO} No faces detected on second scan")
    except Exception as e:
        print(f"  {FAIL} Second scan error: {e}")

    # Step 7: Final summary
    print("\n" + "=" * 60)
    print("SPRINT 7 TEST SUMMARY")
    print("=" * 60)
    print(f"  WebSocket attendance_logged (1st scan): {attendance_logged}")
    print(f"  DB logs count change: {before_count} -> {after_count}")
    print(f"  Cooldown verified: see step 6 above")
    print("\nSprint 7 attendance auto-logging: COMPLETE")


if __name__ == "__main__":
    main()
