"""WebSocket /ws/recognize.

Protokol:
  1. Klien mengirim JSON {"type":"auth","token":"<jwt>"} (maks 10 detik).
  2. Server membalas {"type":"ready",...}.
  3. Klien mengirim frame biner: 4 byte frame_id (big-endian) + JPEG/PNG.
  4. Server membalas {"type":"result",...} atau {"type":"error",...}.
Backpressure: hanya SATU frame terbaru yang menunggu; frame lama dibuang. Laju proses dibatasi WS_MAX_FPS."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from urllib.parse import urlparse

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.session import RecognitionSession
from app.utils.images import FrameError

log = logging.getLogger(__name__)
router = APIRouter()


async def _safe_close(ws: WebSocket, code: int) -> None:
    try:
        await ws.close(code=code)
    except Exception:  # noqa: BLE001
        pass


@router.websocket("/ws/recognize")
async def recognize(ws: WebSocket):
    state = ws.app.state
    s = state.settings
    origin = ws.headers.get("origin")
    if origin and urlparse(origin).netloc != ws.headers.get("host"):
        await ws.close(code=4403)
        return
    await ws.accept()
    try:
        msg = await asyncio.wait_for(ws.receive_json(), timeout=10)
        user = state.auth.verify_token(str(msg.get("token", ""))) if msg.get("type") == "auth" else None
    except (asyncio.TimeoutError, ValueError, AttributeError, WebSocketDisconnect, RuntimeError):
        user = None
    if user is None:
        await _safe_close(ws, 4401)
        return
    engine = state.engine
    if not engine.loaded:
        await ws.send_json({"type": "error", "code": "model_unavailable",
                            "message": state.engine_error or "Model belum dimuat."})
        await _safe_close(ws, 1011)
        return

    session = RecognitionSession(s, engine, state.recognizer, state.liveness)
    await ws.send_json({"type": "ready", "threshold": s.recognition_threshold,
                        "threshold_calibrated": s.threshold_calibrated, "max_fps": s.ws_max_fps})

    slot: bytes | None = None
    event = asyncio.Event()
    send_lock = asyncio.Lock()
    dropped = 0

    async def send(obj: dict) -> None:
        async with send_lock:
            await ws.send_json(obj)

    async def reader() -> None:
        nonlocal slot, dropped
        while True:
            m = await ws.receive()
            if m["type"] == "websocket.disconnect":
                return
            data = m.get("bytes")
            if data is not None:
                if len(data) > s.max_frame_bytes + 4 or len(data) <= 4:
                    await send({"type": "error", "code": "invalid_frame",
                                "message": "Ukuran frame tidak valid."})
                    continue
                if slot is not None:
                    dropped += 1          # frame lama dibuang
                slot = data
                event.set()
            elif m.get("text"):
                try:
                    if json.loads(m["text"]).get("type") == "ping":
                        await send({"type": "pong"})
                except (ValueError, AttributeError):
                    pass

    async def worker() -> None:
        nonlocal slot
        min_interval, last = 1.0 / s.ws_max_fps, 0.0
        while True:
            await event.wait()
            event.clear()
            wait = min_interval - (time.monotonic() - last)
            if wait > 0:
                await asyncio.sleep(wait)
            data, slot = slot, None
            if data is None:
                continue
            last = time.monotonic()
            frame_id = int.from_bytes(data[:4], "big")
            try:
                result = await session.process(data)
                result["dropped"] = dropped
            except FrameError as exc:
                result = {"type": "error", "code": exc.code, "message": exc.message, "frame_id": frame_id}
            except Exception:  # noqa: BLE001
                log.exception("Inference gagal")
                result = {"type": "error", "code": "inference_failed",
                          "message": "Pemrosesan frame gagal.", "frame_id": frame_id}
            await send(result)

    tasks = [asyncio.create_task(reader()), asyncio.create_task(worker())]
    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for t in tasks:
            t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await _safe_close(ws, 1000)
