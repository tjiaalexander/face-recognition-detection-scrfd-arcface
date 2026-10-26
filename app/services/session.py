"""Satu sesi recognition per koneksi WebSocket: decode -> deteksi -> kualitas -> match -> smoothing."""
from __future__ import annotations

import time

from app.config import Settings
from app.services.face_engine import BaseFaceEngine
from app.services.liveness import LivenessChecker
from app.services.quality_check import assess_face
from app.services.recognition import Detection, Recognizer, TemporalSmoother
from app.utils.images import decode_image


class RecognitionSession:
    def __init__(self, s: Settings, engine: BaseFaceEngine, recognizer: Recognizer, liveness: LivenessChecker):
        self.s, self.engine, self.recognizer, self.liveness = s, engine, recognizer, liveness
        self.smoother = TemporalSmoother(s)

    async def process(self, payload: bytes) -> dict:
        """payload = 4 byte frame_id (big-endian) + JPEG/PNG. Memunculkan FrameError jika frame tidak valid."""
        t0 = time.perf_counter()
        frame_id = int.from_bytes(payload[:4], "big")
        img = decode_image(payload[4:], self.s.max_frame_bytes, self.s.max_frame_side)
        faces = await self.engine.analyze_async(img)          # tepat satu inference per frame
        faces = sorted(faces, key=lambda f: f.area, reverse=True)[: self.s.max_faces]

        out: list[dict | None] = []
        dets: list[Detection] = []
        det_slots: list[int] = []
        for f in faces:
            box = [int(v) for v in f.bbox]
            q = assess_face(img, f, self.s)
            if not q.ok or f.embedding is None:
                reasons = q.reasons or ["low_confidence"]
                out.append({"track_id": None, "bbox": box, "status": "low_quality", "user_id": None,
                            "name": None, "score": None, "votes": 0,
                            "quality": {"ok": False, "reasons": reasons, "messages": q.messages or [reasons[0]]}})
                continue
            dets.append(Detection(f.bbox, self.recognizer.identify(f.embedding)))
            det_slots.append(len(out))
            out.append({"bbox": box, "quality": {"ok": True, "reasons": [], "messages": []}})
        for slot, tr in zip(det_slots, self.smoother.update(dets)):
            out[slot].update(track_id=tr.track_id, status=tr.status, user_id=tr.user_id, name=tr.name,
                             score=round(tr.score, 3), votes=tr.votes)
        return {"type": "result", "frame_id": frame_id, "width": int(img.shape[1]), "height": int(img.shape[0]),
                "faces": out, "liveness": "not_configured" if self.liveness.__class__.__name__ ==
                "NotConfiguredLiveness" else "configured",
                "latency_ms": round((time.perf_counter() - t0) * 1000, 1)}
