"""Konfigurasi aplikasi. Semua nilai dapat diubah lewat environment variable
(nama variabel = nama field dalam huruf besar, mis. RECOGNITION_THRESHOLD)."""
from __future__ import annotations

import json
import logging
import os
import secrets
from dataclasses import dataclass, fields, replace
from functools import lru_cache
from pathlib import Path
from typing import Callable

log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent

# Berkas ONNX minimal yang dibutuhkan (deteksi SCRFD + pengenalan ArcFace).
MODEL_FILES: dict[str, tuple[str, str]] = {
    "antelopev2": ("scrfd_10g_bnkps.onnx", "glintr100.onnx"),
    "buffalo_l": ("det_10g.onnx", "w600k_r50.onnx"),
    "buffalo_s": ("det_10g.onnx", "w200k_r50.onnx"),
}


def load_dotenv(path: Path | None = None) -> None:
    path = path or BASE_DIR / ".env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _cast(raw: str, default: object) -> object:
    if isinstance(default, bool):
        return raw.lower() in {"1", "true", "yes", "on"}
    if isinstance(default, int):
        return int(raw)
    if isinstance(default, float):
        return float(raw)
    if isinstance(default, Path):
        return Path(raw)
    return raw


def persisted_secret(path: Path, generator: Callable[[], str]) -> str:
    """Baca rahasia dari berkas; buat baru jika belum ada."""
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    value = generator()
    path.write_text(value, encoding="utf-8")
    try:
        os.chmod(path, 0o600)  # di Windows efeknya terbatas
    except OSError:
        pass
    log.warning("Rahasia baru dibuat di %s. Cadangkan berkas ini dan jangan di-commit.", path)
    return value


def random_token() -> str:
    return secrets.token_urlsafe(32)


@dataclass(frozen=True)
class Settings:
    app_name: str = "Face Recognition System"
    log_level: str = "INFO"
    enable_docs: bool = False

    data_dir: Path = BASE_DIR / "data"
    database_path: str = ""          # kosong -> data/faces.db ; ":memory:" untuk tes
    model_name: str = "antelopev2"   # atau "buffalo_l"
    model_root: str = ""             # kosong -> data/insightface
    onnx_providers: str = "auto"     # auto | cpu | cuda
    det_size: int = 640
    det_thresh: float = 0.5
    max_faces: int = 10

    # PERINGATAN: nilai default ini BELUM dikalibrasi. Jalankan scripts/calibrate_threshold.py.
    # Untuk kasus wajah kembar, default yang lebih konservatif mencegah false duplicate pada orang yang berbeda.
    recognition_threshold: float = 0.45
    threshold_calibrated: bool = False

    # Kualitas wajah (nilai awal; sesuaikan dengan kamera Anda)
    min_face_px: int = 80
    min_det_score: float = 0.6
    min_blur: float = 40.0
    min_brightness: float = 50.0
    max_brightness: float = 215.0
    max_yaw_ratio: float = 0.35
    max_roll_deg: float = 30.0

    register_min_samples: int = 3
    register_max_samples: int = 10
    register_consistency_min: float = 0.45

    max_frame_bytes: int = 5_000_000
    max_frame_side: int = 4096
    ws_max_fps: float = 8.0
    smoothing_window: int = 5
    smoothing_min_votes: int = 3
    track_iou: float = 0.3
    track_ttl_frames: int = 10

    admin_username: str = "admin"
    admin_password: str = ""
    admin_password_hash: str = ""
    jwt_secret: str = ""
    jwt_expire_minutes: int = 60
    login_max_attempts: int = 5
    login_window_seconds: int = 60
    register_max_per_minute: int = 20
    embedding_key: str = ""
    retention_days: int = 0          # 0 = nonaktif
    liveness_mode: str = "none"

    # ---- turunan ----
    @property
    def database_file(self) -> str:
        return self.database_path or str(Path(self.data_dir) / "faces.db")

    @property
    def models_root(self) -> Path:
        return Path(self.model_root) if self.model_root else Path(self.data_dir) / "insightface"

    @property
    def threshold_file(self) -> Path:
        return Path(self.data_dir) / "threshold.json"

    def validate(self) -> None:
        errs: list[str] = []
        if self.model_name not in MODEL_FILES:
            errs.append(f"MODEL_NAME harus salah satu dari {sorted(MODEL_FILES)}")
        if not -1.0 < self.recognition_threshold < 1.0:
            errs.append("RECOGNITION_THRESHOLD harus di antara -1 dan 1")
        if self.smoothing_min_votes > self.smoothing_window:
            errs.append("SMOOTHING_MIN_VOTES tidak boleh melebihi SMOOTHING_WINDOW")
        if self.register_min_samples > self.register_max_samples:
            errs.append("REGISTER_MIN_SAMPLES tidak boleh melebihi REGISTER_MAX_SAMPLES")
        if self.ws_max_fps <= 0:
            errs.append("WS_MAX_FPS harus > 0")
        if errs:
            raise ValueError("Konfigurasi tidak valid: " + "; ".join(errs))

    def with_calibrated_threshold(self, explicit: bool = False) -> "Settings":
        """Pakai threshold hasil kalibrasi (data/threshold.json) jika ada dan modelnya sama."""
        if explicit or not self.threshold_file.is_file():
            return self
        try:
            data = json.loads(self.threshold_file.read_text(encoding="utf-8"))
            if data.get("model") == self.model_name:
                return replace(self, recognition_threshold=float(data["threshold"]),
                               threshold_calibrated=True)
            log.warning("threshold.json dibuat untuk model %s, bukan %s; diabaikan.",
                        data.get("model"), self.model_name)
        except (OSError, ValueError, KeyError) as exc:
            log.warning("threshold.json tidak dapat dibaca: %s", exc)
        return self

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        kwargs: dict[str, object] = {}
        for f in fields(cls):
            raw = os.environ.get(f.name.upper())
            if raw is None or not raw.strip():
                continue
            kwargs[f.name] = _cast(raw.strip(), f.default)
        settings = cls(**kwargs)  # type: ignore[arg-type]
        settings = settings.with_calibrated_threshold(explicit="recognition_threshold" in kwargs)
        settings.validate()
        return settings


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
