"""Deteksi (SCRFD), alignment (norm_crop 112x112 dari 5 landmark), dan embedding (ArcFace)
memakai InsightFace + ONNX Runtime. Inference dijalankan di thread terpisah agar event loop
FastAPI tidak terblokir. Satu frame = satu kali inference."""
from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import numpy as np

from app.config import MODEL_FILES, Settings

log = logging.getLogger(__name__)


class FaceEngineError(RuntimeError):
    pass


class ModelNotAvailableError(FaceEngineError):
    pass


@dataclass
class DetectedFace:
    bbox: tuple[float, float, float, float]   # x1,y1,x2,y2 (piksel frame asli)
    kps: np.ndarray | None                    # (5,2): mata kiri, mata kanan, hidung, mulut kiri, mulut kanan
    det_score: float
    embedding: np.ndarray | None = None       # float32, L2-normalized

    @property
    def area(self) -> float:
        return max(0.0, self.bbox[2] - self.bbox[0]) * max(0.0, self.bbox[3] - self.bbox[1])


class BaseFaceEngine(ABC):
    model_name: str = "base"
    providers: list[str] = []

    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="face-engine")
        self.loaded = False

    @abstractmethod
    def load(self) -> None: ...

    @abstractmethod
    def analyze(self, image: np.ndarray) -> list[DetectedFace]:
        """Deteksi + alignment + embedding untuk semua wajah pada satu gambar BGR."""

    async def analyze_async(self, image: np.ndarray) -> list[DetectedFace]:
        if not self.loaded:
            raise FaceEngineError("Model belum dimuat.")
        return await asyncio.get_running_loop().run_in_executor(self._executor, self.analyze, image)

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)


def select_providers(preference: str) -> list[str]:
    try:
        import onnxruntime as ort
    except ImportError as exc:
        raise ModelNotAvailableError("onnxruntime belum terpasang (pip install onnxruntime).") from exc
    available = ort.get_available_providers()
    pref = preference.lower()
    if pref == "cpu":
        return ["CPUExecutionProvider"]
    if pref in ("cuda", "auto") and "CUDAExecutionProvider" in available:
        return ["CUDAExecutionProvider", "CPUExecutionProvider"]
    if pref == "cuda":
        raise ModelNotAvailableError(
            "ONNX_PROVIDERS=cuda tetapi CUDAExecutionProvider tidak tersedia. "
            "Pasang onnxruntime-gpu + CUDA/cuDNN yang sesuai, atau gunakan 'cpu'. "
            f"Provider tersedia: {available}")
    return ["CPUExecutionProvider"]


def check_model_files(settings: Settings) -> None:
    folder = settings.models_root / "models" / settings.model_name
    missing = [f for f in MODEL_FILES[settings.model_name] if not (folder / f).is_file()]
    if missing:
        raise ModelNotAvailableError(
            f"Berkas model {missing} tidak ditemukan di {folder}. "
            f"Jalankan: python -m scripts.download_models --model {settings.model_name}")


class InsightFaceEngine(BaseFaceEngine):
    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.model_name = settings.model_name
        self._det = None
        self._rec = None

    def load(self) -> None:
        s = self.settings
        check_model_files(s)  # cek lebih dulu agar insightface tidak mencoba mengunduh sendiri
        self.providers = select_providers(s.onnx_providers)
        try:
            from insightface.app import FaceAnalysis
        except ImportError as exc:
            raise ModelNotAvailableError("insightface belum terpasang (pip install insightface).") from exc
        try:
            app = FaceAnalysis(name=s.model_name, root=str(s.models_root),
                               allowed_modules=["detection", "recognition"], providers=self.providers)
            app.prepare(ctx_id=0 if "CUDAExecutionProvider" in self.providers else -1,
                        det_size=(s.det_size, s.det_size), det_thresh=s.det_thresh)
            self._det, self._rec = app.models["detection"], app.models["recognition"]
        except Exception as exc:  # noqa: BLE001 - library memunculkan berbagai tipe error
            raise ModelNotAvailableError(f"Gagal memuat model {s.model_name}: {exc}") from exc
        self.loaded = True
        log.info("Model %s dimuat (providers=%s)", s.model_name, self.providers)

    def analyze(self, image: np.ndarray) -> list[DetectedFace]:
        from insightface.utils import face_align

        bboxes, kpss = self._det.detect(image, max_num=self.settings.max_faces, metric="default")
        if bboxes is None or len(bboxes) == 0:
            return []
        faces: list[DetectedFace] = []
        for i, box in enumerate(bboxes):
            kps = None if kpss is None else np.asarray(kpss[i], dtype=np.float32)
            emb = None
            if kps is not None:
                aligned = face_align.norm_crop(image, kps, image_size=112)
                feat = np.asarray(self._rec.get_feat(aligned), dtype=np.float32).reshape(-1)
                norm = float(np.linalg.norm(feat))
                emb = feat / norm if norm > 0 else None
            faces.append(DetectedFace(tuple(float(v) for v in box[:4]), kps, float(box[4]), emb))
        return faces
