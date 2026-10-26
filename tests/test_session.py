"""Alur recognition end-to-end tanpa HTTP: decode -> deteksi -> kualitas -> match -> smoothing."""
import asyncio

import pytest

from app.services.liveness import NotConfiguredLiveness
from app.services.session import RecognitionSession
from app.utils.images import FrameError
from tests.fakes import FakeEngine, identity_embedding, png, render_scene


def make(settings, recognizer):
    eng = FakeEngine()
    eng.load()
    return eng, RecognitionSession(settings, eng, recognizer, NotConfiguredLiveness())


def frame(i, faces):
    return i.to_bytes(4, "big") + png(render_scene(faces))


def run(session, payload):
    return asyncio.run(session.process(payload))


def test_empty_db_no_face_and_invalid(settings, recognizer):
    eng, s = make(settings, recognizer)
    assert run(s, frame(1, []))["faces"] == []
    with pytest.raises(FrameError):
        run(s, (2).to_bytes(4, "big") + b"sampah")


def test_one_inference_per_frame_and_multi_faces(settings, recognizer):
    eng, s = make(settings, recognizer)
    res = run(s, frame(7, [(1, 30, 30, 120), (2, 300, 200, 150)]))
    assert eng.calls == 1 and len(res["faces"]) == 2 and res["frame_id"] == 7
    assert res["liveness"] == "not_configured"


def test_confirmation_needs_multiple_frames(settings, recognizer, repo):
    repo.create_user("a", "Ani", [identity_embedding(1, i) for i in range(3)])
    recognizer.reload()
    eng, s = make(settings, recognizer)
    st = [run(s, frame(i, [(1, 100, 100, 120)]))["faces"][0] for i in range(4)]
    assert [f["status"] for f in st] == ["tentative", "tentative", "confirmed", "confirmed"]
    assert st[-1]["user_id"] == "a" and st[-1]["name"] == "Ani"
    stranger = run(s, frame(9, [(7, 400, 100, 120)]))["faces"][0]
    assert stranger["status"] == "unknown" and stranger["user_id"] is None


def test_low_quality_faces_are_not_recognised(settings, recognizer, repo):
    repo.create_user("a", "Ani", [identity_embedding(1, i) for i in range(3)])
    recognizer.reload()
    eng, s = make(settings, recognizer)
    f = run(s, frame(1, [(1, 100, 100, 30)]))["faces"][0]
    assert f["status"] == "low_quality" and f["user_id"] is None and "face_too_small" in f["quality"]["reasons"]
    dark = run(s, (2).to_bytes(4, "big") + png(render_scene([(1, 100, 100, 120)], gain=0.15)))["faces"][0]
    assert dark["status"] == "low_quality" and "too_dark" in dark["quality"]["reasons"]
