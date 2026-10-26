# Privasi, keamanan, dan retensi

- **Persetujuan:** registrasi mewajibkan pernyataan persetujuan; waktunya disimpan. Dapatkan persetujuan tertulis sesuai hukum setempat.
- **Minimisasi:** hanya embedding yang disimpan (terenkripsi di database). Foto mentah tidak disimpan. Embedding tidak pernah dikirim ke klien.
- **Enkripsi:** saat disimpan, Fernet dengan `EMBEDDING_KEY` (default: `data/embedding.key`). Simpan kunci terpisah dari database
  dan cadangkan. Saat dikirim: gunakan HTTPS/WSS untuk akses selain localhost.
- **Akses:** login admin (JWT, kedaluwarsa), pembatasan percobaan login, batas ukuran frame, batas laju proses WebSocket,
  pemeriksaan Origin pada WebSocket, header keamanan (CSP, nosniff).
- **Retensi:** `RETENTION_DAYS=N` menghapus pengguna (beserta semua templatenya) yang terdaftar lebih dari N hari, dicek tiap 24 jam.
  Penghapusan manual lewat menu Database Pengguna menghapus semua template pengguna tersebut.
- **Pencadangan:** cadangan database juga berisi data biometrik terenkripsi; terapkan retensi yang sama.
- **Liveness:** belum ada. `app/services/liveness.py` hanya mendefinisikan antarmuka; status selalu `not_configured`. Sebelum hasil
  dipakai untuk tindakan sensitif (akses, pembayaran), implementasikan `LivenessChecker` nyata (model anti-spoofing atau challenge-response)
  dan gunakan `allowed_for_sensitive_action()` yang menolak jika liveness tidak lulus.
- **Bukan bukti mutlak:** kecocokan wajah bersifat probabilistik, dapat keliru, dan akurasinya dapat berbeda antar kelompok demografis.
  Jangan jadikan satu-satunya dasar keputusan yang berdampak pada seseorang.
- **Lisensi model:** periksa lisensi bobot pretrained InsightFace sebelum distribusi atau penggunaan komersial.
