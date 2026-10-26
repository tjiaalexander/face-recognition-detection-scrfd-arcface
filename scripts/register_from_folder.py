from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

import requests


def iter_images(folder: Path):
    exts = {".jpg", ".jpeg", ".png"}
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path.suffix.lower() in exts:
            yield path


def encode_image(path: Path) -> str:
    with path.open("rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def login(base_url: str, username: str, password: str):
    resp = requests.post(
        f"{base_url}/api/auth/login",
        json={"username": username, "password": password},
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Login gagal: {resp.status_code} {resp.text}")
    return resp.json()["access_token"]


def register_user(base_url: str, token: str, user_id: str, name: str, image_dir: Path):
    images = list(iter_images(image_dir))
    if not images:
        raise RuntimeError(f"Folder '{image_dir}' tidak berisi gambar JPG/PNG.")

    frames = [encode_image(p) for p in images[:10]]
    payload = {
        "user_id": user_id,
        "name": name,
        "consent": True,
        "frames": frames,
    }

    resp = requests.post(
        f"{base_url}/api/users/register",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=60,
    )
    try:
        body = resp.json()
    except ValueError:
        body = {"raw": resp.text}

    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Registrasi gagal: {resp.status_code} {json.dumps(body, ensure_ascii=False)}")

    print(json.dumps(body, ensure_ascii=False, indent=2))
    print(f"\nBerhasil mendaftarkan {len(frames)} gambar untuk {name} ({user_id}).")


def main():
    parser = argparse.ArgumentParser(description="Register wajah dari folder gambar ke server face recognition")
    parser.add_argument("folder", type=str, help="Folder berisi gambar wajah")
    parser.add_argument("--user-id", required=True, help="ID unik pengguna, contoh: ANDI-001")
    parser.add_argument("--name", required=True, help="Nama lengkap")
    parser.add_argument("--username", default="admin", help="Username admin")
    parser.add_argument("--password", default=None, help="Password admin. Jika tidak diisi, pakai ADMIN_PASSWORD dari env.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL server")
    args = parser.parse_args()

    password = args.password or __import__("os").environ.get("ADMIN_PASSWORD")
    if not password:
        raise RuntimeError("Password admin belum di-set. Gunakan --password atau set env ADMIN_PASSWORD.")

    token = login(args.base_url, args.username, password)
    register_user(args.base_url, token, args.user_id, args.name, Path(args.folder).resolve())


if __name__ == "__main__":
    main()
