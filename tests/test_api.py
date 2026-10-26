"""Tes integrasi API + WebSocket memakai FakeEngine. Butuh: fastapi, httpx (pip install -r requirements-dev.txt)."""
import base64
import dataclasses

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402
from tests.fakes import FakeEngine, png, render_scene  # noqa: E402

PASSWORD = "rahasia-uji"


def b64(img):
    return base64.b64encode(png(img)).decode()


def frames(ident, n=4, extra=()):
    return [b64(render_scene([(ident, 40 + 20 * i, 60, 120), *extra])) for i in range(n)]


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings, FakeEngine())) as c:
        yield c


@pytest.fixture
def auth(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": PASSWORD})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def register(client, auth, uid="u1", ident=1, **kw):
    body = {"user_id": uid, "name": "Budi", "consent": True, "frames": frames(ident)} | kw
    return client.post("/api/users/register", json=body, headers=auth)


def test_health_is_public_and_minimal(client):
    assert client.get("/api/health").json() == {"status": "ok", "model_loaded": True}


def test_admin_endpoints_require_auth(client):
    for method, path in [("get", "/api/users"), ("get", "/api/stats"), ("get", "/api/users/x"),
                         ("delete", "/api/users/x"), ("post", "/api/users/register")]:
        assert getattr(client, method)(path).status_code in (401, 403), path
    assert client.get("/api/users", headers={"Authorization": "Bearer palsu"}).status_code == 401


def test_login_wrong_password_and_rate_limit(client):
    assert client.post("/api/auth/login", json={"username": "admin", "password": "salah"}).status_code == 401
    codes = [client.post("/api/auth/login", json={"username": "admin", "password": "salah"}).status_code
             for _ in range(8)]
    assert 429 in codes


def test_register_list_detail_delete(client, auth):
    r = register(client, auth)
    assert r.status_code == 201, r.text
    assert r.json()["accepted_samples"] == 4 and "embedding" not in r.text
    assert client.get("/api/users", headers=auth).json()["total"] == 1
    assert client.get("/api/users?search=bud", headers=auth).json()["total"] == 1
    assert client.get("/api/users/u1", headers=auth).json()["template_count"] == 4
    assert client.get("/api/stats", headers=auth).json()["templates"] == 4
    d = client.delete("/api/users/u1", headers=auth)
    assert d.status_code == 200 and d.json()["deleted_templates"] == 4
    assert client.get("/api/stats", headers=auth).json()["templates"] == 0
    assert client.get("/api/users/u1", headers=auth).status_code == 404
    assert client.delete("/api/users/u1", headers=auth).status_code == 404


def test_model_selection_api(client, auth):
    models = client.get("/api/system/models", headers=auth)
    assert models.status_code == 200, models.text
    payload = models.json()
    assert {"antelopev2", "buffalo_l", "buffalo_s"}.issubset(set(payload["models"]))
    assert payload["current"] == "antelopev2"

    switched = client.post("/api/system/model", json={"model": "buffalo_l"}, headers=auth)
    assert switched.status_code == 200, switched.text
    assert switched.json()["model"] == "buffalo_l"

    switched_back = client.post("/api/system/model", json={"model": "antelopev2"}, headers=auth)
    assert switched_back.status_code == 200, switched_back.text
    assert switched_back.json()["model"] == "antelopev2"


def test_register_validation(client, auth):
    assert register(client, auth, consent=False).status_code == 422
    assert register(client, auth, user_id="bad id!").status_code == 422
    no_face = [b64(render_scene([])) for _ in range(4)]
    r = register(client, auth, frames=no_face)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "not_enough_samples"
    multi = register(client, auth, frames=frames(1, extra=[(2, 400, 250, 120)]))
    assert multi.status_code == 422
    assert register(client, auth, frames=["bukan-base64!!"]).status_code == 422
    assert register(client, auth, uid="ok", frames=frames(1, n=2)).status_code == 422   # < min sampel


def test_register_rejects_duplicate_id_but_allows_twin_like_faces(client, auth):
    assert register(client, auth).status_code == 201
    assert register(client, auth, ident=2).status_code == 409                      # ID sama
    dup = register(client, auth, uid="u2", ident=1)                                # wajah kembar boleh diterima
    assert dup.status_code == 201, dup.text
    assert register(client, auth, uid="u3", ident=4).status_code == 201


def test_oversized_body_rejected(client, auth):
    r = client.post("/api/users/register", content=b"x" * 14_000_000, headers=auth)
    assert r.status_code == 413


def test_model_failure_is_reported(settings):
    with TestClient(create_app(settings, FakeEngine(fail_load=True))) as c:
        assert c.get("/api/health").json()["model_loaded"] is False
        tok = c.post("/api/auth/login", json={"username": "admin", "password": PASSWORD}).json()["access_token"]
        h = {"Authorization": f"Bearer {tok}"}
        assert "gagal dimuat" in c.get("/api/stats", headers=h).json()["model_error"]
        assert c.post("/api/users/register", headers=h, json={
            "user_id": "a", "name": "A", "consent": True, "frames": ["x"]}).status_code == 503


def connect(client, auth):
    ws = client.websocket_connect("/ws/recognize")
    ws = ws.__enter__()
    ws.send_json({"type": "auth", "token": auth["Authorization"].split()[1]})
    assert ws.receive_json()["type"] == "ready"
    return ws


def send(ws, frame_id, img_bytes):
    ws.send_bytes(frame_id.to_bytes(4, "big") + img_bytes)
    return ws.receive_json()


def test_ws_requires_valid_token(client):
    with client.websocket_connect("/ws/recognize") as ws:
        ws.send_json({"type": "auth", "token": "palsu"})
        with pytest.raises(Exception):
            ws.receive_json()


def test_ws_no_face_unknown_and_confirmed_after_multiple_frames(client, auth):
    assert register(client, auth).status_code == 201
    ws = connect(client, auth)
    try:
        assert send(ws, 1, png(render_scene([])))["faces"] == []
        stranger = send(ws, 2, png(render_scene([(7, 100, 100, 120)])))
        assert stranger["faces"][0]["status"] == "unknown" and stranger["faces"][0]["user_id"] is None
        statuses = []
        for i in range(4):
            res = send(ws, 10 + i, png(render_scene([(1, 100, 100, 120)])))
            statuses.append(res["faces"][0]["status"])
        assert statuses[0] == "tentative" and statuses[-1] == "confirmed"
        assert res["faces"][0]["user_id"] == "u1" and res["frame_id"] == 13
        assert "embedding" not in str(res)
    finally:
        ws.__exit__(None, None, None)


def test_ws_multiple_faces_and_low_quality(client, auth):
    register(client, auth)
    ws = connect(client, auth)
    try:
        res = send(ws, 1, png(render_scene([(1, 30, 30, 120), (6, 300, 200, 150)])))
        assert len(res["faces"]) == 2
        small = send(ws, 2, png(render_scene([(1, 30, 30, 30)])))
        assert small["faces"][0]["status"] == "low_quality"
    finally:
        ws.__exit__(None, None, None)


def test_ws_invalid_frame_and_reconnect(client, auth):
    ws = connect(client, auth)
    err = send(ws, 5, b"bukan gambar")
    assert err["type"] == "error" and err["code"] == "invalid_frame" and err["frame_id"] == 5
    ws.__exit__(None, None, None)
    ws2 = connect(client, auth)                      # sambung kembali setelah terputus
    try:
        assert send(ws2, 1, png(render_scene([(1, 100, 100, 120)])))["type"] == "result"
    finally:
        ws2.__exit__(None, None, None)


def test_ws_database_empty_gives_unknown(client, auth):
    ws = connect(client, auth)
    try:
        assert send(ws, 1, png(render_scene([(1, 100, 100, 120)])))["faces"][0]["status"] == "unknown"
    finally:
        ws.__exit__(None, None, None)
