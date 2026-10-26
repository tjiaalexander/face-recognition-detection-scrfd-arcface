"""Inisialisasi FastAPI. Jalankan: uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import auth, system, users, ws
from app.config import BASE_DIR, Settings, get_settings, persisted_secret, random_token
from app.database.connection import Database
from app.database.repository import SQLiteRepository
from app.services.crypto import EmbeddingCipher
from app.services.face_engine import BaseFaceEngine, FaceEngineError, InsightFaceEngine
from app.services.liveness import build_liveness
from app.services.recognition import Recognizer
from app.services.security import AuthService, SlidingWindowLimiter

log = logging.getLogger("app")

CSP = ("default-src 'self'; img-src 'self' data: blob:; style-src 'self'; script-src 'self'; "
       "connect-src 'self' ws: wss:; media-src 'self' blob:; frame-ancestors 'none'; base-uri 'none'")


def create_app(settings: Settings | None = None, engine: BaseFaceEngine | None = None) -> FastAPI:
    s = settings or get_settings()
    s.validate()
    logging.basicConfig(level=s.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    embedding_key = s.embedding_key or persisted_secret(s.data_dir / "embedding.key", EmbeddingCipher.generate_key)
    jwt_secret = s.jwt_secret or persisted_secret(s.data_dir / "jwt.secret", random_token)

    db = Database(s.database_file)
    repo = SQLiteRepository(db, EmbeddingCipher(embedding_key), s.model_name)
    engine = engine or InsightFaceEngine(s)
    recognizer = Recognizer(repo, s)
    liveness = build_liveness(s.liveness_mode)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.engine_error = None
        try:
            await asyncio.to_thread(engine.load)
        except FaceEngineError as exc:
            app.state.engine_error = str(exc)
            log.error("Model gagal dimuat: %s", exc)
        n = await asyncio.to_thread(recognizer.reload)
        log.info("%d template dimuat. Threshold=%.3f (%s)", n, s.recognition_threshold,
                 "dikalibrasi" if s.threshold_calibrated else "BELUM dikalibrasi")
        task = asyncio.create_task(_retention_loop(repo, recognizer, s)) if s.retention_days > 0 else None
        yield
        if task:
            task.cancel()
        engine.close()
        db.close()

    app = FastAPI(title=s.app_name, lifespan=lifespan,
                  docs_url="/docs" if s.enable_docs else None,
                  redoc_url=None, openapi_url="/openapi.json" if s.enable_docs else None)
    app.state.settings, app.state.repo, app.state.engine = s, repo, engine
    app.state.db = db
    app.state.embedding_key = embedding_key
    app.state.recognizer, app.state.liveness = recognizer, liveness
    app.state.liveness_status = "not_configured" if s.liveness_mode == "none" else s.liveness_mode
    app.state.engine_error = None
    app.state.auth = AuthService(s, jwt_secret)
    app.state.login_limiter = SlidingWindowLimiter(s.login_max_attempts, s.login_window_seconds)
    app.state.register_limiter = SlidingWindowLimiter(s.register_max_per_minute, 60)

    max_body = int(s.max_frame_bytes * s.register_max_samples * 4 / 3) + 16_384

    @app.middleware("http")
    async def guard(request: Request, call_next):
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > max_body:
            return JSONResponse({"detail": {"code": "payload_too_large", "message": "Permintaan terlalu besar."}}, 413)
        if request.method in {"POST", "PUT", "PATCH"} and request.url.path.startswith("/api/users/register"):
            try:
                body = await request.body()
            except Exception:
                body = b""
            if len(body) > max_body:
                return JSONResponse({"detail": {"code": "payload_too_large", "message": "Permintaan terlalu besar."}}, 413)
            request._body = body
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = CSP
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(self), microphone=()"
        if request.url.path.startswith(("/api", "/js", "/css")):
            response.headers["Cache-Control"] = "no-store"
        return response

    app.include_router(auth.router)
    app.include_router(system.router)
    app.include_router(users.router)
    app.include_router(ws.router)
    frontend = BASE_DIR / "frontend"
    if frontend.is_dir():
        app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    return app


async def _retention_loop(repo, recognizer, s: Settings) -> None:
    while True:
        try:
            n = await asyncio.to_thread(repo.purge_older_than, s.retention_days)
            if n:
                log.info("Retensi: %d pengguna dihapus (> %d hari).", n, s.retention_days)
                await asyncio.to_thread(recognizer.reload)
        except Exception:  # noqa: BLE001
            log.exception("Purge retensi gagal")
        await asyncio.sleep(86_400)

