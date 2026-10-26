# Kalibrasi threshold dan evaluasi

Threshold bawaan (`RECOGNITION_THRESHOLD=0.45`) hanya placeholder. Skor cosine bergantung pada model, kamera,
pencahayaan, dan populasi pengguna, sehingga threshold harus dikalibrasi dengan data Anda sendiri.

## Data
Kumpulkan foto secara sah dan dengan persetujuan:

```
dataset/
  orang_a/*.jpg
  orang_b/*.jpg
  ...
```
Disarankan >= 10 orang dan >= 10 foto per orang, dengan variasi pose, cahaya, dan hari pengambilan. Foto tanpa wajah
atau dengan banyak wajah dilewati otomatis. Dengan data sedikit, FAR kecil (mis. 0.001) tidak dapat diukur; skrip memberi peringatan.

## Pemisahan data (mencegah kebocoran)
- **Orang** dibagi: gallery (terdaftar) dan impostor (tidak terdaftar). Impostor dibagi lagi menjadi impostor-kalibrasi dan
  impostor-evaluasi yang **orangnya berbeda**.
- **Foto** orang gallery dibagi tiga bagian lepas: enroll (40%), kalibrasi (30%), evaluasi (30%).
- Threshold dipilih **hanya** dari data kalibrasi. Angka FAR/FRR/precision/recall dilaporkan dari data evaluasi.
- Pembagian deterministik (`--seed`).

## Menjalankan
```powershell
python -m scripts.calibrate_threshold --dataset dataset --far-target 0.001
python -m scripts.calibrate_threshold --dataset dataset --far-target 0.001 --apply   # simpan data/threshold.json
```
Laporan lengkap ada di `data/calibration_report.json`: FAR, FRR, misidentification rate, precision, recall, serta latensi
deteksi+embedding (p50/p95) dengan provider yang dipakai. Aplikasi memakai `data/threshold.json` otomatis jika modelnya sama
dan `RECOGNITION_THRESHOLD` tidak diatur di environment.

## Definisi metrik
- **FAR**: proporsi probe orang tak terdaftar yang diterima (skor terbaik >= threshold).
- **FRR**: proporsi probe orang terdaftar yang ditolak (skor < threshold).
- **Misidentification**: orang terdaftar diterima tetapi sebagai orang lain.
- **Precision** = TP / (TP + FP), FP mencakup impostor yang diterima dan salah identifikasi. **Recall** = TP / semua probe terdaftar.

Ulangi kalibrasi saat mengganti kamera, model, atau kondisi pencahayaan. Pengaturan `DUPLICATE_THRESHOLD` (cegah registrasi ganda) sebaiknya
lebih tinggi dari threshold pengenalan; periksa dengan pasangan foto orang yang sama dan berbeda.
