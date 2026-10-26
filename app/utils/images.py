"""Decode frame dengan batas ukuran. Hanya JPEG dan PNG yang diterima; dimensi dibaca dari
header SEBELUM decode agar gambar kecil-berdimensi-raksasa tidak menghabiskan memori."""
from __future__ import annotations

import base64
import binascii
import struct

import cv2
import numpy as np


class FrameError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


_SOF = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}


def peek_dimensions(data: bytes) -> tuple[int, int] | None:
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        w, h = struct.unpack(">II", data[16:24])
        return w, h
    if data[:3] == b"\xff\xd8\xff":
        i, n = 2, len(data)
        while i + 9 < n:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker == 0xFF:
                i += 1
                continue
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            if marker in _SOF:
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    return None


def _resize_to_limit(img: np.ndarray, max_side: int) -> np.ndarray:
    h, w = img.shape[:2]
    if h <= max_side and w <= max_side:
        return img
    scale = min(max_side / float(h), max_side / float(w))
    if scale >= 1.0:
        return img
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)


def _encode_jpeg(img: np.ndarray, quality: int) -> tuple[bool, np.ndarray]:
    result = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if isinstance(result, tuple) and len(result) == 2:
        a, b = result
        if isinstance(a, np.ndarray) and not isinstance(b, np.ndarray):
            return bool(b), a
        if isinstance(b, np.ndarray) and not isinstance(a, np.ndarray):
            return bool(a), b
        return bool(a), b if isinstance(b, np.ndarray) else np.asarray(b)
    if isinstance(result, np.ndarray):
        return True, result
    return False, np.empty((0,), dtype=np.uint8)


def decode_image(data: bytes, max_bytes: int, max_side: int) -> np.ndarray:
    if not data:
        raise FrameError("invalid_frame", "Frame kosong.")
    dims = peek_dimensions(data)
    if dims is None:
        raise FrameError("invalid_frame", "Format frame harus JPEG atau PNG yang valid.")
    if min(dims) < 16:
        raise FrameError("frame_dimensions", f"Dimensi frame tidak diizinkan ({dims[0]}x{dims[1]}).")

    img = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise FrameError("invalid_frame", "Frame tidak dapat didecode.")

    # Normalisasi otomatis untuk foto ponsel beresolusi tinggi agar tetap bisa dipakai sebagai sampel.
    img = _resize_to_limit(img, max_side)

    for quality in (85, 75, 60, 45):
        ok, encoded = _encode_jpeg(img, quality)
        if ok and encoded.size <= max_bytes:
            return cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        if ok and max(img.shape[:2]) > max_side // 2:
            img = _resize_to_limit(img, max_side // 2)

    return img


def decode_b64_image(b64: str, max_bytes: int, max_side: int) -> np.ndarray:
    if "," in b64[:64]:  # buang prefix data:image/...;base64,
        b64 = b64.split(",", 1)[1]
    try:
        data = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise FrameError("invalid_frame", "Base64 tidak valid.") from exc
    return decode_image(data, max_bytes, max_side)
