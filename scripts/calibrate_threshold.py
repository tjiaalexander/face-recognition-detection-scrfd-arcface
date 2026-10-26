"""Kalibrasi threshold dan evaluasi dari dataset berlabel.

Struktur dataset (data Anda sendiri, diperoleh sah dengan persetujuan):
    dataset/<nama_orang>/*.jpg
Butuh minimal ~10 orang dengan >=10 foto per orang agar FAR kecil dapat diukur.

  python -m scripts.calibrate_threshold --dataset dataset --far-target 0.001 [--apply]

--apply menulis data/threshold.json (dipakai otomatis oleh aplikasi untuk model yang sama)."""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

from app.config import Settings
from app.services.calibration import build_trials, choose_threshold, evaluate, split_dataset
from app.services.face_engine import InsightFaceEngine

EXT = {".jpg", ".jpeg", ".png", ".bmp"}


def embed(engine, path: Path, latencies: list[float]):
    img = cv2.imread(str(path))
    if img is None:
        return None
    t = time.perf_counter()
    faces = engine.analyze(img)
    latencies.append((time.perf_counter() - t) * 1000)
    faces = [f for f in faces if f.embedding is not None]
    if len(faces) != 1:      # abaikan foto tanpa wajah / banyak wajah agar label tidak ambigu
        return None
    return faces[0].embedding


def embed_group(engine, groups: dict[str, list[Path]], lat) -> dict[str, np.ndarray]:
    out = {}
    for person, paths in groups.items():
        embs = [e for e in (embed(engine, p, lat) for p in paths) if e is not None]
        if embs:
            out[person] = np.vstack(embs)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, type=Path)
    ap.add_argument("--far-target", type=float, default=0.001)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    s = Settings.from_env()
    per_person = {d.name: sorted(p for p in d.iterdir() if p.suffix.lower() in EXT)
                  for d in sorted(args.dataset.iterdir()) if d.is_dir()}
    if len(per_person) < 6:
        print(f"[PERINGATAN] Hanya {len(per_person)} orang; hasil kalibrasi tidak andal (disarankan >= 10).")
    split = split_dataset(per_person, seed=args.seed)
    if not split.enroll or not (split.calib_impostors or split.eval_impostors):
        print("Data tidak cukup untuk memisahkan gallery/impostor. Tambah orang dan foto.")
        return 1

    engine = InsightFaceEngine(s)
    engine.load()
    lat: list[float] = []
    gallery = embed_group(engine, split.enroll, lat)
    calib_known = embed_group(engine, split.calib_known, lat)
    eval_known = embed_group(engine, split.eval_known, lat)
    calib_imp = [e for m in embed_group(engine, split.calib_impostors, lat).values() for e in m]
    eval_imp = [e for m in embed_group(engine, split.eval_impostors, lat).values() for e in m]
    gallery = {k: v for k, v in gallery.items() if k in calib_known and k in eval_known}

    t_calib = build_trials(gallery, {k: calib_known[k] for k in gallery}, calib_imp)
    threshold, warn = choose_threshold(t_calib.impostor_scores, args.far_target)
    t_eval = build_trials(gallery, {k: eval_known[k] for k in gallery}, eval_imp)
    report = {
        "model": s.model_name, "far_target": args.far_target, "seed": args.seed,
        "calibration": evaluate(t_calib, threshold), "evaluation": evaluate(t_eval, threshold),
        "people": {"gallery": len(gallery), "impostor_calib": len(split.calib_impostors),
                   "impostor_eval": len(split.eval_impostors), "skipped": split.skipped},
        "latency_ms_detect_embed": {"p50": float(np.percentile(lat, 50)), "p95": float(np.percentile(lat, 95)),
                                    "n": len(lat), "providers": engine.providers},
        "warning": warn, "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    Path(s.data_dir).mkdir(parents=True, exist_ok=True)
    (Path(s.data_dir) / "calibration_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    if args.apply:
        s.threshold_file.write_text(json.dumps({"model": s.model_name, "threshold": threshold,
                                                "far_target": args.far_target,
                                                "calibrated_at": report["created_at"]}, indent=2))
        print(f"\nThreshold {threshold:.4f} ditulis ke {s.threshold_file}. Restart aplikasi.")
    else:
        print("\nTambahkan --apply untuk menyimpan threshold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
