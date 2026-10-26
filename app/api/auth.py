from fastapi import APIRouter, Depends, HTTPException, Request

from app.dependencies import get_auth, require_admin
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.security import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, auth: AuthService = Depends(get_auth)):
    ip = request.client.host if request.client else "unknown"
    if not request.app.state.login_limiter.allow(ip):
        raise HTTPException(429, {"code": "rate_limited", "message": "Terlalu banyak percobaan login. Coba lagi sebentar."})
    if not auth.verify_credentials(body.username, body.password):
        raise HTTPException(401, {"code": "invalid_credentials", "message": "Username atau password salah."})
    token, ttl = auth.create_token(body.username)
    return TokenResponse(access_token=token, expires_in=ttl)


@router.get("/me")
def me(username: str = Depends(require_admin)):
    return {"username": username}
