# Migrasi ke PostgreSQL + pgvector

Seluruh akses data lewat `SQLiteRepository` (`app/database/repository.py`). Untuk PostgreSQL, buat kelas dengan
metode yang sama (`create_user`, `delete_user`, `get_user`, `list_users`, `count_*`, `load_index`, `purge_older_than`) lalu
ganti pembuatannya di `app/main.py`.

Skema yang disarankan:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE users (user_id text PRIMARY KEY, name text NOT NULL, consent_at timestamptz NOT NULL, created_at timestamptz NOT NULL);
CREATE TABLE templates (id bigserial PRIMARY KEY, user_id text NOT NULL REFERENCES users ON DELETE CASCADE,
  model text NOT NULL, embedding vector(512) NOT NULL, quality real, created_at timestamptz NOT NULL);
CREATE INDEX ON templates USING hnsw (embedding vector_cosine_ops);
```
Catatan: pencarian di database memerlukan embedding **tidak terenkripsi** di kolom `vector`, sehingga perlindungan harus
berpindah ke enkripsi disk/tablespace, kontrol akses, dan jaringan. Pertimbangkan hal ini sebelum bermigrasi; untuk beberapa
ribu template, pencocokan di memori seperti sekarang sudah cukup cepat. Gunakan operator `<=>` (jarak cosine; skor = 1 - jarak).
