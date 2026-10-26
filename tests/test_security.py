import dataclasses
import time

from app.services.security import AuthService, SlidingWindowLimiter, hash_password, verify_password


def test_password_hash_roundtrip():
    h = hash_password("kata-sandi")
    assert h.startswith("scrypt$") and "kata-sandi" not in h
    assert verify_password("kata-sandi", h) and not verify_password("salah", h)
    assert not verify_password("x", "bukan-hash")


def test_auth_service_plain_and_hash(settings):
    a = AuthService(settings, "rahasia-jwt")
    assert a.verify_credentials("admin", "rahasia-uji") and not a.verify_credentials("admin", "x")
    assert not a.verify_credentials("root", "rahasia-uji")
    b = AuthService(dataclasses.replace(settings, admin_password="", admin_password_hash=hash_password("p4ss")), "s")
    assert b.verify_credentials("admin", "p4ss") and not b.verify_credentials("admin", "rahasia-uji")


def test_token_validation(settings):
    a = AuthService(settings, "rahasia-jwt")
    token, ttl = a.create_token("admin")
    assert a.verify_token(token) == "admin" and ttl == settings.jwt_expire_minutes * 60
    assert a.verify_token(token + "x") is None and a.verify_token("") is None
    assert AuthService(settings, "kunci-lain").verify_token(token) is None
    short = AuthService(dataclasses.replace(settings, jwt_expire_minutes=-1), "rahasia-jwt")
    assert a.verify_token(short.create_token("admin")[0]) is None      # kedaluwarsa


def test_missing_password_generates_random(settings):
    a = AuthService(dataclasses.replace(settings, admin_password=""), "s")
    assert not a.verify_credentials("admin", "") and not a.verify_credentials("admin", "admin")


def test_rate_limiter():
    lim = SlidingWindowLimiter(3, 0.2)
    assert [lim.allow("ip") for _ in range(4)] == [True, True, True, False]
    assert lim.allow("lain")
    time.sleep(0.25)
    assert lim.allow("ip")
