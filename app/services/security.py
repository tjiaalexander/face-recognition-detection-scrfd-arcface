"""Autentikasi admin (JWT HS256), hashing password (scrypt), dan rate limiter sederhana."""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import secrets
import time
from collections import defaultdict, deque

import jwt

from app.config import Settings

log = logging.getLogger(__name__)


def hash_password(password: str, n: int = 2**14, r: int = 8, p: int = 1) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=n, r=r, p=p, dklen=32)
    b64 = lambda b: base64.b64encode(b).decode()  # noqa: E731
    return f"scrypt${n}${r}${p}${b64(salt)}${b64(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = encoded.split("$")
        if scheme != "scrypt":
            return False
        calc = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt),
                              n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(calc, base64.b64decode(digest))
    except (ValueError, TypeError):
        return False


class AuthService:
    def __init__(self, s: Settings, jwt_secret: str):
        self.s = s
        self._secret = jwt_secret
        self._plain = s.admin_password
        self._hash = s.admin_password_hash
        if not self._plain and not self._hash:
            self._plain = secrets.token_urlsafe(12)
            log.warning("ADMIN_PASSWORD belum diatur. Password sementara untuk '%s': %s "
                        "(berubah setiap restart; atur ADMIN_PASSWORD_HASH di .env).",
                        s.admin_username, self._plain)

    def verify_credentials(self, username: str, password: str) -> bool:
        user_ok = hmac.compare_digest(username.encode(), self.s.admin_username.encode())
        if self._hash:
            pass_ok = verify_password(password, self._hash)
        else:
            pass_ok = hmac.compare_digest(password.encode(), self._plain.encode())
        return user_ok and pass_ok

    def create_token(self, username: str) -> tuple[str, int]:
        ttl = self.s.jwt_expire_minutes * 60
        now = int(time.time())
        token = jwt.encode({"sub": username, "iat": now, "exp": now + ttl, "role": "admin"},
                           self._secret, algorithm="HS256")
        return token, ttl

    def verify_token(self, token: str) -> str | None:
        try:
            payload = jwt.decode(token, self._secret, algorithms=["HS256"],
                                 options={"require": ["exp", "sub"]})
        except jwt.PyJWTError:
            return None
        return payload["sub"] if payload.get("role") == "admin" else None


class SlidingWindowLimiter:
    def __init__(self, max_events: int, window_seconds: float):
        self.max, self.window = max_events, window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        q = self._events[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.max:
            return False
        q.append(now)
        return True
