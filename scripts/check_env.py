"""Periksa kompatibilitas lingkungan: python -m scripts.check_env"""
from __future__ import annotations

import platform
import sys


def main() -> int:
    print(f"Python      : {platform.python_version()} ({platform.system()})")
    if sys.version_info[:2] != (3, 11):
        print("  [PERINGATAN] Proyek ini ditargetkan untuk Python 3.11.")
    problems = 0
    for mod in ("numpy", "cv2", "onnxruntime", "insightface", "fastapi", "uvicorn", "cryptography", "jwt"):
        try:
            m = __import__(mod)
            print(f"{mod:<12}: {getattr(m, '__version__', 'ok')}")
        except ImportError as exc:
            problems += 1
            print(f"{mod:<12}: TIDAK ADA ({exc})")
    try:
        import onnxruntime as ort
        prov = ort.get_available_providers()
        print(f"ONNX providers: {prov}")
        print("  -> GPU NVIDIA siap" if "CUDAExecutionProvider" in prov else
              "  -> hanya CPU (normal; untuk GPU pasang onnxruntime-gpu + CUDA/cuDNN yang cocok)")
        if "onnxruntime-gpu" not in "".join(sys.modules) and len(prov) > 1:
            pass
    except ImportError:
        pass
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
