"""Dependency injection: semua komponen diambil dari app.state sehingga mudah diganti saat tes."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings
from app.services.face_engine import BaseFaceEngine
from app.services.recognition import Recognizer
from app.services.security import AuthService

_bearer = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_repository(request: Request):
    return request.app.state.repo


def get_engine(request: Request) -> BaseFaceEngine:
    return request.app.state.engine


def get_recognizer(request: Request) -> Recognizer:
    return request.app.state.recognizer


def get_auth(request: Request) -> AuthService:
    return request.app.state.auth


def require_admin(creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
                  auth: AuthService = Depends(get_auth)) -> str:
    username = auth.verify_token(creds.credentials) if creds else None
    if username is None:
        raise HTTPException(401, {"code": "unauthorized", "message": "Login diperlukan."},
                            headers={"WWW-Authenticate": "Bearer"})
    return username


def require_model(request: Request, engine: BaseFaceEngine = Depends(get_engine)) -> BaseFaceEngine:
    if not engine.loaded:
        raise HTTPException(503, {"code": "model_unavailable",
                                  "message": request.app.state.engine_error or "Model belum dimuat."})
    return engine
