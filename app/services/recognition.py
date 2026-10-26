"""Pencocokan identitas (cosine similarity pada embedding ternormalisasi) dan smoothing multi-frame."""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from itertools import count

import numpy as np

from app.config import Settings
from app.database.models import TemplateIndex


@dataclass(frozen=True)
class Identification:
    user_id: str | None   # None jika di bawah threshold
    name: str | None
    score: float          # skor terbaik (juga diisi saat Unknown, untuk transparansi)
    matched: bool


class Recognizer:
    def __init__(self, repo, settings: Settings):
        self._repo, self._s = repo, settings
        self._index = TemplateIndex()
        self._lock = threading.Lock()

    def reload(self) -> int:
        index = self._repo.load_index()
        with self._lock:
            self._index = index
        return index.size

    @property
    def index(self) -> TemplateIndex:
        return self._index

    def best_match(self, embedding: np.ndarray) -> tuple[str | None, float]:
        idx = self._index
        if idx.size == 0:
            return None, 0.0
        sims = idx.matrix @ np.asarray(embedding, dtype=np.float32)
        i = int(np.argmax(sims))
        return idx.user_ids[i], float(sims[i])

    def identify(self, embedding: np.ndarray) -> Identification:
        user_id, score = self.best_match(embedding)
        if user_id is not None and score >= self._s.recognition_threshold:
            return Identification(user_id, self._index.names.get(user_id), score, True)
        return Identification(None, None, score, False)


# ---------- smoothing multi-frame ----------
def iou(a, b) -> float:
    ix1, iy1, ix2, iy2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


@dataclass
class Detection:
    bbox: tuple[float, float, float, float]
    ident: Identification


@dataclass
class TrackResult:
    track_id: int
    status: str            # confirmed | tentative | unknown
    user_id: str | None
    name: str | None
    score: float
    votes: int


@dataclass
class _Track:
    id: int
    bbox: tuple
    history: deque
    missed: int = 0


class TemporalSmoother:
    """Identitas dinyatakan 'confirmed' hanya jika >= min_votes dari `window` frame terakhir
    pada track yang sama memilih pengguna yang sama. Satu frame tidak pernah cukup."""

    def __init__(self, s: Settings):
        self.s = s
        self._tracks: list[_Track] = []
        self._ids = count(1)

    def update(self, detections: list[Detection]) -> list[TrackResult]:
        used: set[int] = set()
        assigned: list[_Track | None] = []
        for det in detections:
            best, best_iou = None, self.s.track_iou
            for t in self._tracks:
                if t.id in used:
                    continue
                v = iou(t.bbox, det.bbox)
                if v >= best_iou:
                    best, best_iou = t, v
            if best is None:
                best = _Track(next(self._ids), det.bbox, deque(maxlen=self.s.smoothing_window))
                self._tracks.append(best)
            used.add(best.id)
            best.bbox, best.missed = det.bbox, 0
            best.history.append((det.ident.user_id, det.ident.score, det.ident.name))
            assigned.append(best)
        for t in self._tracks:
            if t.id not in used:
                t.missed += 1
        self._tracks = [t for t in self._tracks if t.missed <= self.s.track_ttl_frames]
        return [self._result(t, d) for t, d in zip(assigned, detections)]

    def _result(self, t: _Track, det: Detection) -> TrackResult:
        votes: dict[str, list[float]] = {}
        names: dict[str, str | None] = {}
        for uid, score, name in t.history:
            if uid is not None:
                votes.setdefault(uid, []).append(score)
                names[uid] = name
        if votes:
            top = max(votes, key=lambda u: len(votes[u]))
            if len(votes[top]) >= self.s.smoothing_min_votes:
                return TrackResult(t.id, "confirmed", top, names[top], float(np.mean(votes[top])), len(votes[top]))
        ident = det.ident
        if ident.matched:
            return TrackResult(t.id, "tentative", ident.user_id, ident.name, ident.score,
                               len(votes.get(ident.user_id, [])))
        return TrackResult(t.id, "unknown", None, None, ident.score, 0)
