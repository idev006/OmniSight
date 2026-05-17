"""
OmniSight RTSP Camera Agent
─────────────────────────────────────────────────────────────────────────────
Bridges IP cameras / CCTV (RTSP streams) to the OmniSight backend WebSocket.

Usage:
    python rtsp_agent.py

Environment variables (set in .env or shell):
    OMNISIGHT_WS      WebSocket base URL  (default: ws://localhost:8000)
    STATION_ID        Station UUID        (required)
    CAMERA_ID         Camera UUID from DB (required — register in Cameras UI first)
    OMNISIGHT_TOKEN   JWT access token    (OPERATOR or ADMIN role)
    RTSP_URL          rtsp://user:pass@192.168.1.x:554/stream1
    TARGET_FPS        Frames to SEND per second (default: 2)
                      Backend will also gate this, but sending less saves bandwidth
    JPEG_QUALITY      JPEG compression 1-100 (default: 70)
    RESIZE_WIDTH      Resize frame before sending (default: 640, 0 = no resize)

Plug-and-play design:
  • Auto-reconnect on both RTSP loss and WebSocket disconnect
  • Respects pause/resume/set_fps commands from Pilot Console
  • camera_id from DB = no conflicts (admin registers camera first, gets UUID)
  • Works with any RTSP source: Hikvision, Dahua, Axis, generic ONVIF, VLC test stream
"""
import asyncio
import cv2
import json
import logging
import os
import sys
import time

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("rtsp-agent")


# ── Config ────────────────────────────────────────────────────────────────────
BACKEND_WS    = os.getenv("OMNISIGHT_WS",       "ws://localhost:8000")
STATION_ID    = os.getenv("STATION_ID",         "")
CAMERA_ID     = os.getenv("CAMERA_ID",          "")
TOKEN         = os.getenv("OMNISIGHT_TOKEN",    "")
RTSP_URL      = os.getenv("RTSP_URL",           "")
TARGET_FPS    = float(os.getenv("TARGET_FPS",   "2"))
JPEG_QUALITY  = int(os.getenv("JPEG_QUALITY",   "70"))
RESIZE_WIDTH  = int(os.getenv("RESIZE_WIDTH",   "640"))


def _validate_config():
    missing = [k for k, v in {
        "STATION_ID": STATION_ID,
        "CAMERA_ID":  CAMERA_ID,
        "TOKEN":      TOKEN,
        "RTSP_URL":   RTSP_URL,
    }.items() if not v]
    if missing:
        logger.error(f"Missing required env vars: {', '.join(missing)}")
        sys.exit(1)


def _encode_frame(frame: np.ndarray) -> bytes:
    """Resize (optional) + JPEG encode → bytes"""
    if RESIZE_WIDTH > 0:
        h, w = frame.shape[:2]
        if w != RESIZE_WIDTH:
            scale  = RESIZE_WIDTH / w
            new_h  = int(h * scale)
            frame  = cv2.resize(frame, (RESIZE_WIDTH, new_h), interpolation=cv2.INTER_LINEAR)
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    return buf.tobytes()


async def run():
    """Main loop with reconnect logic for both RTSP and WebSocket."""
    try:
        import websockets
    except ImportError:
        logger.error("websockets package not installed. Run: pip install websockets")
        sys.exit(1)

    _validate_config()

    ws_url = (
        f"{BACKEND_WS}/api/v1/ws/scan/{STATION_ID}"
        f"?token={TOKEN}&camera_id={CAMERA_ID}"
    )
    frame_interval = 1.0 / TARGET_FPS

    logger.info(f"RTSP Agent starting")
    logger.info(f"  RTSP   : {RTSP_URL}")
    logger.info(f"  Backend: {ws_url[:60]}…")
    logger.info(f"  FPS    : {TARGET_FPS}  JPEG quality: {JPEG_QUALITY}")

    while True:
        # ── Open RTSP stream ──────────────────────────────────────────────
        logger.info("Opening RTSP stream…")
        cap = cv2.VideoCapture(RTSP_URL)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)     # minimize latency (1-frame buffer)

        if not cap.isOpened():
            logger.warning("Cannot open RTSP stream. Retry in 5s…")
            cap.release()
            await asyncio.sleep(5)
            continue

        logger.info("RTSP stream opened ✓")

        # ── Connect WebSocket ─────────────────────────────────────────────
        try:
            async with websockets.connect(
                ws_url,
                ping_interval=20,
                ping_timeout=30,
                close_timeout=5,
            ) as ws:
                logger.info("WebSocket connected ✓")
                paused      = False
                current_fps = TARGET_FPS
                min_interval = 1.0 / current_fps

                # Background task: listen for control messages from server
                # (pause / resume / set_fps / disconnect)
                async def _listen():
                    nonlocal paused, current_fps, min_interval
                    try:
                        async for msg in ws:
                            if not isinstance(msg, str):
                                continue
                            try:
                                cmd = json.loads(msg)
                            except json.JSONDecodeError:
                                continue

                            action = cmd.get("action", "")

                            if action == "pause":
                                paused = True
                                logger.info("Paused by Pilot Console")

                            elif action == "resume":
                                paused = False
                                logger.info("Resumed by Pilot Console")

                            elif action == "set_fps":
                                new_fps = float(cmd.get("fps", current_fps))
                                new_fps = max(0.1, min(30.0, new_fps))
                                current_fps  = new_fps
                                min_interval = 1.0 / new_fps
                                logger.info(f"FPS changed to {new_fps:.1f}")

                            elif action == "disconnect":
                                reason = cmd.get("reason", "Server disconnected")
                                logger.info(f"Disconnect requested: {reason}")
                                await ws.close()
                                return

                    except Exception as e:
                        logger.debug(f"Listen loop ended: {e}")

                listen_task = asyncio.create_task(_listen())

                # ── Frame send loop ───────────────────────────────────────
                try:
                    while ws.open:
                        t0 = time.monotonic()

                        ret, frame = cap.read()
                        if not ret:
                            logger.warning("RTSP frame read failed — stream ended?")
                            break

                        if paused:
                            await asyncio.sleep(0.1)
                            continue

                        # Encode and send
                        try:
                            payload = await asyncio.get_event_loop().run_in_executor(
                                None, _encode_frame, frame
                            )
                            await ws.send(payload)
                        except Exception as e:
                            logger.warning(f"Send error: {e}")
                            break

                        # Sleep to hit target FPS (time already spent in read/encode)
                        elapsed = time.monotonic() - t0
                        sleep   = max(0.0, min_interval - elapsed)
                        if sleep > 0:
                            await asyncio.sleep(sleep)

                finally:
                    listen_task.cancel()

        except Exception as e:
            logger.warning(f"WebSocket error: {e}")
        finally:
            cap.release()
            logger.info("RTSP stream released. Reconnect in 3s…")
            await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(run())
