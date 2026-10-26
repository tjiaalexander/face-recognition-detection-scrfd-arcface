"""Pemeriksaan kualitas wajah. Nilai ambang adalah titik awal dan harus disesuaikan dengan kamera Anda.
Oklusi tidak dideteksi langsung; det_score rendah dipakai sebagai indikator kasar."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import cv2
import numpy as np

from app.config import Settings

REASON_MESSAGES = {
    "no_face": "Tidak ada wajah terdeteksi.",
    "multiple_faces": "Terdeteksi lebih dari satu wajah.",
    "face_too_small": "Wajah terlalu kecil. Dekatkan wajah ke kamera.",
    "low_confidence": "Wajah kurang jelas atau tertutup sebagian.",
    "face_cut_off": "Wajah terpotong di tepi frame.",
    "blurry": "Gambar buram. Tahan posisi dan bersihkan lensa.",
    "too_dark": "Pencahayaan terlalu gelap.",
    "too_bright": "Pencahayaan terlalu terang.",
    "face_turned": "Wajah terlalu menoleh. Hadap lurus ke kamera.",
    "face_tilted": "Kepala terlalu miring.",
}


def enhance_face_image(image: np.ndarray) -> np.ndarray:
    """Perbaiki citra yang terlalu gelap atau kontras rendah agar wajah lebih terbaca.

    Fitur ini bersifat konservatif: hanya diterapkan saat kondisi gambar memang membutuhkan
    peningkatan kualitas, sehingga gambar normal tidak berubah dan validasi kualitas tetap akurat.
    """
    if image is None or image.size == 0:
        return image.copy() if isinstance(image, np.ndarray) else np.array([], dtype=np.uint8)

    img = image.copy()
    if img.ndim == 2:
        gray = img.astype(np.uint8)
        mean_brightness = float(gray.mean())
        contrast = float(gray.std())
        if mean_brightness >= 80 and contrast >= 35:
            return img
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        gray = cv2.equalizeHist(gray)
        gray = cv2.convertScaleAbs(gray, alpha=1.08, beta=8)
        gray = cv2.medianBlur(gray, 3)
        return cv2.cvtColor(np.clip(gray, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)

    if img.ndim == 3 and img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    value = hsv[:, :, 2]
    mean_brightness = float(value.mean())
    contrast = float(value.std())
    if mean_brightness >= 80 and contrast >= 35:
        return img

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    value = clahe.apply(value)
    value = cv2.equalizeHist(value)
    value = cv2.convertScaleAbs(value, alpha=1.08, beta=8)
    value = cv2.medianBlur(value, 3)
    hsv[:, :, 2] = value
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


@dataclass
class QualityResult:
    ok: bool
    reasons: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)

    @property
    def messages(self) -> list[str]:
        return [REASON_MESSAGES.get(r, r) for r in self.reasons]


def assess_face(image: np.ndarray, face, s: Settings) -> QualityResult:
    h, w = image.shape[:2]
    x1, y1, x2, y2 = face.bbox
    fw, fh = x2 - x1, y2 - y1
    reasons: list[str] = []
    metrics: dict[str, float] = {"face_px": float(min(fw, fh)), "det_score": float(face.det_score)}

    if min(fw, fh) < s.min_face_px:
        reasons.append("face_too_small")
    if face.det_score < s.min_det_score:
        reasons.append("low_confidence")
    tol = max(2.0, 0.05 * max(fw, fh))
    if x1 < -tol or y1 < -tol or x2 > w + tol or y2 > h + tol:
        reasons.append("face_cut_off")

    cx1, cy1, cx2, cy2 = max(0, int(x1)), max(0, int(y1)), min(w, int(x2)), min(h, int(y2))
    if cx2 - cx1 >= 8 and cy2 - cy1 >= 8:
        gray = cv2.cvtColor(image[cy1:cy2, cx1:cx2], cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (112, 112), interpolation=cv2.INTER_AREA)  # normalisasi skala
        blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        bright = float(gray.mean())
        metrics.update(blur=blur, brightness=bright)
        if blur < s.min_blur:
            reasons.append("blurry")
        if bright < s.min_brightness:
            reasons.append("too_dark")
        elif bright > s.max_brightness:
            reasons.append("too_bright")
    else:
        reasons.append("face_cut_off")

    kps = getattr(face, "kps", None)
    if kps is not None and len(kps) >= 3:
        le, re_, nose = kps[0], kps[1], kps[2]
        eye_dist = float(np.hypot(*(re_ - le)))
        if eye_dist > 1e-6:
            yaw = float((nose[0] - (le[0] + re_[0]) / 2) / eye_dist)
            roll = math.degrees(math.atan2(float(re_[1] - le[1]), float(re_[0] - le[0])))
            metrics.update(yaw_ratio=yaw, roll_deg=roll)
            if abs(yaw) > s.max_yaw_ratio:
                reasons.append("face_turned")
            if abs(roll) > s.max_roll_deg:
                reasons.append("face_tilted")

    return QualityResult(ok=not reasons, reasons=reasons, metrics=metrics)
