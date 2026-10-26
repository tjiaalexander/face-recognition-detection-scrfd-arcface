# Jalankan dari folder proyek:  .\run.ps1
$ErrorActionPreference = "Stop"
if (-not (Test-Path .venv)) { py -3.11 -m venv .venv }
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "File .env dibuat. Atur ADMIN_PASSWORD_HASH atau ADMIN_PASSWORD." }
python -m scripts.check_env
python -m scripts.download_models
uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
