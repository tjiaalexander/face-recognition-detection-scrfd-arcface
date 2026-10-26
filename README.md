# Face Recognition Web System

Deteksi dan pengenalan wajah real-time lewat webcam. Backend FastAPI, deteksi SCRFD dan embedding ArcFace
(InsightFace `antelopev2`, dapat diganti `buffalo_l`) via ONNX Runtime, database SQLite, komunikasi WebSocket.

> **Status verifikasi:** modul database, enkripsi, kualitas wajah, pencocokan, smoothing, kalibrasi, auth, dan alur
> sesi recognition diuji dengan engine tiruan (48 tes lulus). **Belum teruji:** model InsightFace asli (akurasi, latensi),
> endpoint HTTP/WebSocket (`tests/test_api.py` sudah ditulis tetapi belum dijalankan), dan UI di browser.
> Jalankan `pytest` di mesin Anda dan lakukan kalibrasi sebelum memercayai hasilnya. Tidak ada angka akurasi yang dijanjikan.

## Menjalankan di Windows (PowerShell, Python 3.11)

Prasyarat: Python 3.11 dan **Microsoft C++ Build Tools** (workload "Desktop development with C++"; `insightface` sering gagal dipasang tanpanya).

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m scripts.hash_password        # tempel hasilnya ke ADMIN_PASSWORD_HASH di .env
python -m scripts.check_env            # cek paket dan provider CPU/GPU
python -m scripts.download_models      # unduh + verifikasi antelopev2 (ratusan MB)
uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

Buka http://127.0.0.1:8000 dan login. `localhost` dianggap konteks aman oleh browser sehingga kamera dapat dipakai
tanpa HTTPS. Untuk akses dari perangkat lain, **wajib** HTTPS (reverse proxy atau `--ssl-keyfile/--ssl-certfile` uvicorn).
`.\run.ps1` menjalankan semua langkah di atas.

Jika tidak mengatur password, aplikasi membuat password sementara dan mencetaknya di log saat start.

GPU NVIDIA: `pip uninstall onnxruntime`, `pip install onnxruntime-gpu`, pasang CUDA/cuDNN yang sesuai, set `ONNX_PROVIDERS=cuda`.
Ganti model: `MODEL_NAME=buffalo_l` lalu `python -m scripts.download_models --model buffalo_l`.
Template milik model lain tidak dipakai (embedding antar model tidak kompatibel); daftarkan ulang setelah mengganti model.

## Pengujian

```powershell
pip install -r requirements-dev.txt
pytest
```

## Struktur

```
app/main.py            inisialisasi FastAPI (factory), middleware keamanan
app/config.py          semua konfigurasi dari environment variable
app/api/               auth, users (registrasi/daftar/hapus), system (health/stats), ws (recognition)
app/services/          face_engine, recognition (+smoothing), quality_check, liveness, crypto, security,
                       calibration, session
app/database/          connection, models, repository (SQLite)
app/schemas/           validasi request/response (Pydantic)
frontend/              HTML + CSS + JavaScript (tanpa build step)
scripts/               download_models, check_env, calibrate_threshold, hash_password
tests/  docs/
```

## Alur recognition

Frame JPEG dikirim lewat WebSocket (maks ~10 fps; klien menunggu hasil sebelum mengirim frame berikutnya, server hanya
menyimpan 1 frame terbaru). Per frame: satu kali inference (SCRFD, alignment 5-landmark, ArcFace) di thread terpisah,
pemeriksaan kualitas, cosine similarity terhadap semua template, lalu smoothing per-track. Status:
`confirmed` (>= 3 dari 5 frame terakhir memilih orang yang sama), `tentative`, `unknown` (di bawah threshold), `low_quality`.

## Keputusan default dan alasannya

| Keputusan | Default | Alasan |
|---|---|---|
| Data tersimpan | Hanya embedding, terenkripsi Fernet | Meminimalkan data biometrik |
| Kunci enkripsi/JWT | Dibuat otomatis di `data/` bila tidak di env | Aman tanpa konfigurasi; **cadangkan** `data/embedding.key` terpisah dari database, jika hilang template tidak terbaca |
| Akses | Semua endpoint (termasuk WebSocket) butuh login admin, kecuali `/api/health` | Nama pengguna adalah data pribadi |
| Threshold | 0.45 (placeholder, UI menandai "belum dikalibrasi") | Tidak ada nilai universal; lihat `docs/CALIBRATION.md` |
| Liveness | Antarmuka saja; status `not_configured`, tidak pernah "lulus" | Tidak ada liveness palsu |
| Registrasi | Wajib centang persetujuan; minimal 3 sampel baik; sampel harus konsisten; ditolak bila mirip pengguna lain | Mencegah data campur dan duplikat |
| Frame | JPEG/PNG saja, maks 1 MB dan 1920 px, dimensi dicek sebelum decode | Batasi penyalahgunaan memori |

## Keterbatasan yang perlu Anda ketahui

- Deteksi oklusi hanya perkiraan kasar (skor deteksi rendah). Pemeriksaan kualitas memakai ambang awal yang perlu disetel.
- Pembatasan ukuran body memakai header `Content-Length`; untuk produksi tambahkan batas di reverse proxy.
- Token JWT disimpan di `sessionStorage` browser dan hilang saat tab ditutup.
- Lisensi: model pretrained InsightFace umumnya hanya untuk riset non-komersial. Periksa sebelum distribusi atau penggunaan komersial.
- Face matching bukan bukti identitas mutlak. Lihat `docs/PRIVACY.md`.
