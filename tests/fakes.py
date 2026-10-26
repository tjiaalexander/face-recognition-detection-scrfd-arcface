"""Engine tiruan untuk tes (TIDAK memakai model nyata). Wajah dirender sebagai kotak bertekstur
dengan penanda: blok kecil berwarna di pojok kiri-atas (lebar blok = ukuran_wajah/5, kanal biru = identitas)."""
from __future__ import annotations

import cv2
import numpy as np

from app.services.face_engine import BaseFaceEngine, DetectedFace, FaceEngineError, ModelNotAvailableError

DIM = 64


def identity_embedding(identity: int, jitter_seed: int = 0) -> np.ndarray:
    base = np.random.default_rng(1000 + identity).normal(size=DIM)
    noise = np.random.default_rng(jitter_seed).normal(size=DIM) * 0.05
    v = base + noise
    return (v / np.linalg.norm(v)).astype(np.float32)


def render_scene(faces: list[tuple[int, int, int, int]], w: int = 640, h: int = 480, gain: float = 1.0) -> np.ndarray:
    """faces: (identitas 0..9, x, y, ukuran). Ukuran harus kelipatan 5."""
    img = np.zeros((h, w, 3), np.uint8)
    for ident, x, y, size in faces:
        rng = np.random.default_rng(ident * 7 + x)
        tex = rng.integers(90, 200, (size, size, 3)).astype(np.float32)
        img[y:y + size, x:x + size] = np.clip(tex * gain, 0, 255).astype(np.uint8)
        m = size // 5
        img[y:y + m, x:x + m] = (10 + 25 * ident, 255, 255)
    return img


class FakeEngine(BaseFaceEngine):
    model_name = "fake"
    providers = ["CPUExecutionProvider"]

    def __init__(self, fail_load: bool = False):
        super().__init__()
        self.fail_load = fail_load
        self.calls = 0

    def load(self) -> None:
        if self.fail_load:
            raise ModelNotAvailableError("model palsu gagal dimuat")
        self.loaded = True

    def analyze(self, image: np.ndarray) -> list[DetectedFace]:
        self.calls += 1
        mask = ((image[:, :, 1] == 255) & (image[:, :, 2] == 255)).astype(np.uint8)
        n, _, stats, _ = cv2.connectedComponentsWithStats(mask)
        faces = []
        for i in range(1, n):
            x, y, mw, mh, area = stats[i]
            if area < 16:
                continue
            size = int(mw) * 5
            ident = int(round((int(image[y + mh // 2, x + mw // 2, 0]) - 10) / 25))
            kps = np.array([[x + .3 * size, y + .38 * size], [x + .7 * size, y + .38 * size],
                            [x + .5 * size, y + .6 * size], [x + .35 * size, y + .8 * size],
                            [x + .65 * size, y + .8 * size]], np.float32)
            faces.append(DetectedFace((float(x), float(y), float(x + size), float(y + size)), kps, 0.99,
                                      identity_embedding(ident, jitter_seed=int(x) + int(y))))
        return faces


def png(img: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return buf.tobytes()
