from dataclasses import replace

from fastapi import APIRouter, Depends, HTTPException, Request

from app.config import MODEL_FILES
from app.dependencies import get_engine, get_repository, get_settings, require_admin
from app.schemas.system import HealthOut, ModelListOut, ModelSwitchIn, StatsOut

router = APIRouter(prefix="/api", tags=["system"])


def _ready_models(settings) -> list[str]:
    ready: list[str] = []
    base = settings.models_root / "models"
    for name in MODEL_FILES:
        folder = base / name
        if folder.is_dir() and all((folder / filename).is_file() for filename in MODEL_FILES[name]):
            ready.append(name)
    return ready


@router.get("/health", response_model=HealthOut)
def health(engine=Depends(get_engine)):
    """Publik dan minimal: tidak memuat data biometrik atau detail konfigurasi."""
    return HealthOut(status="ok", model_loaded=engine.loaded)


@router.get("/system/models", response_model=ModelListOut, dependencies=[Depends(require_admin)])
def list_models(request: Request):
    settings = request.app.state.settings
    ready = _ready_models(settings)
    if not ready:
        ready = [settings.model_name]
    current = settings.model_name if settings.model_name in ready else ready[0]
    return ModelListOut(current=current, model=current, models=ready)


@router.post("/system/model", response_model=ModelListOut, dependencies=[Depends(require_admin)])
def switch_model(payload: ModelSwitchIn, request: Request):
    model_name = payload.model
    if model_name not in MODEL_FILES:
        raise HTTPException(400, {"code": "invalid_model", "message": f"Model tidak dikenal: {model_name}"})

    ready = _ready_models(request.app.state.settings)
    if model_name not in ready:
        raise HTTPException(400, {
            "code": "model_unavailable",
            "message": f"Model '{model_name}' belum terpasang. Jalankan: python -m scripts.download_models --model {model_name}"
        })

    s = request.app.state.settings
    if s.model_name == model_name:
        return ModelListOut(current=s.model_name, model=s.model_name, models=ready)

    try:
        old_engine = request.app.state.engine
        if old_engine is not None:
            old_engine.close()

        new_settings = replace(s, model_name=model_name)
        request.app.state.settings = new_settings

        from app.database.connection import Database
        from app.database.repository import SQLiteRepository
        from app.services.crypto import EmbeddingCipher
        from app.services.face_engine import InsightFaceEngine
        from app.services.recognition import Recognizer

        db = getattr(request.app.state, "db", None)
        if db is None:
            db = Database(new_settings.database_file)
            request.app.state.db = db
        repo = SQLiteRepository(db, EmbeddingCipher(request.app.state.embedding_key), model_name)
        engine = InsightFaceEngine(new_settings)
        engine.load()
        recognizer = Recognizer(repo, new_settings)
        recognizer.reload()
        request.app.state.repo = repo
        request.app.state.engine = engine
        request.app.state.recognizer = recognizer
        request.app.state.engine_error = None
        request.app.state.liveness_status = "not_configured" if new_settings.liveness_mode == "none" else new_settings.liveness_mode
    except Exception as exc:  # pragma: no cover - runtime failure path
        raise HTTPException(500, {"code": "model_switch_failed", "message": str(exc)}) from exc

    return ModelListOut(current=model_name, model=model_name, models=list(MODEL_FILES))


@router.get("/stats", response_model=StatsOut, dependencies=[Depends(require_admin)])
def stats(request: Request, repo=Depends(get_repository), engine=Depends(get_engine),
          s=Depends(get_settings)):
    total = repo.count_templates(same_model_only=False)
    same = repo.count_templates(same_model_only=True)
    return StatsOut(
        users=repo.count_users(), templates=same, templates_other_model=total - same,
        templates_undecryptable=request.app.state.recognizer.index.skipped,
        model=s.model_name, model_loaded=engine.loaded, model_error=request.app.state.engine_error,
        providers=list(engine.providers), threshold=s.recognition_threshold,
        threshold_calibrated=s.threshold_calibrated, liveness=request.app.state.liveness_status)
