"""Unduh dan verifikasi model InsightFace.

  python -m scripts.download_models --model antelopev2
  python -m scripts.download_models --model antelopev2 --verify-only

Verifikasi: (1) berkas wajib ada, (2) dapat dibuka ONNX Runtime, (3) SHA256 dicatat ke
data/insightface/models/<model>/MANIFEST.json pada unduhan pertama dan dibandingkan pada
verifikasi berikutnya. Catat/bandingkan juga SHA256 dengan sumber tepercaya Anda sendiri.
LISENSI: model pretrained InsightFace umumnya hanya untuk riset non-komersial. Periksa lisensi
sebelum distribusi atau penggunaan komersial."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from app.config import MODEL_FILES, Settings

URL = "https://github.com/deepinsight/insightface/releases/download/v0.7/{name}.zip"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(folder: Path, model: str) -> bool:
    ok = True
    manifest_path = folder / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
    for fname in MODEL_FILES[model]:
        p = folder / fname
        if not p.is_file() or p.stat().st_size == 0:
            print(f"[GAGAL] {fname}: tidak ada atau kosong"); ok = False; continue
        digest = sha256(p)
        known = manifest.get(fname)
        if known and known != digest:
            print(f"[GAGAL] {fname}: SHA256 berbeda dari manifest (berkas rusak/diubah)"); ok = False; continue
        try:
            import onnxruntime as ort
            ort.InferenceSession(str(p), providers=["CPUExecutionProvider"])
        except ImportError:
            print("[PERINGATAN] onnxruntime belum terpasang; uji pemuatan ONNX dilewati")
        except Exception as exc:  # noqa: BLE001
            print(f"[GAGAL] {fname}: ONNX Runtime tidak dapat membukanya: {exc}"); ok = False; continue
        manifest.setdefault(fname, digest)
        print(f"[OK]    {fname}  sha256={digest}")
    if ok:
        manifest_path.write_text(json.dumps(manifest, indent=2))
    return ok


def download(model: str, folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    url = URL.format(name=model)
    print(f"Mengunduh {url} (ratusan MB, harap tunggu)...")
    with tempfile.TemporaryDirectory() as tmp:
        zpath = Path(tmp) / "model.zip"
        urllib.request.urlretrieve(url, zpath)
        with zipfile.ZipFile(zpath) as z:
            for member in z.infolist():
                name = Path(member.filename).name   # ratakan folder bersarang & cegah path traversal
                if member.is_dir() or not name.endswith(".onnx"):
                    continue
                with z.open(member) as src, (folder / name).open("wb") as dst:
                    shutil.copyfileobj(src, dst)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None, choices=sorted(MODEL_FILES))
    ap.add_argument("--verify-only", action="store_true")
    args = ap.parse_args()
    s = Settings.from_env()
    model = args.model or s.model_name
    folder = s.models_root / "models" / model
    if not args.verify_only:
        if all((folder / f).is_file() for f in MODEL_FILES[model]):
            print(f"Berkas model sudah ada di {folder}; unduhan dilewati (hapus folder untuk mengunduh ulang).")
        else:
            try:
                download(model, folder)
            except Exception as exc:  # noqa: BLE001
                print(f"Pengunduhan gagal: {exc}\nUnduh manual {URL.format(name=model)} lalu ekstrak berkas .onnx ke {folder}")
                return 1
    return 0 if verify(folder, model) else 1


if __name__ == "__main__":
    sys.exit(main())
