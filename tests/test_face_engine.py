import asyncio

import numpy as np
import pytest

from app.config import Settings
from app.services.face_engine import FaceEngineError, InsightFaceEngine, ModelNotAvailableError
from app.utils.images import FrameError, decode_image, peek_dimensions
from tests.fakes import FakeEngine, png, render_scene


def test_real_engine_reports_missing_model_clearly(tmp_path):
    eng = InsightFaceEngine(Settings(data_dir=tmp_path))
    with pytest.raises(ModelNotAvailableError) as e:
        eng.load()
    assert "download_models" in str(e.value) and not eng.loaded


def test_engine_refuses_inference_before_load():
    with pytest.raises(FaceEngineError):
        asyncio.run(FakeEngine().analyze_async(np.zeros((50, 50, 3), np.uint8)))


def test_fake_engine_detection_counts():
    eng = FakeEngine()
    eng.load()
    run = lambda img: asyncio.run(eng.analyze_async(img))  # noqa: E731
    assert run(np.zeros((480, 640, 3), np.uint8)) == []
    one = run(render_scene([(2, 50, 50, 100)]))
    assert len(one) == 1 and abs(np.linalg.norm(one[0].embedding) - 1) < 1e-5
    assert len(run(render_scene([(1, 20, 20, 100), (3, 300, 200, 150)]))) == 2
    assert eng.calls == 3        # satu inference per frame


def test_decode_rejects_bad_frames():
    ok = png(render_scene([(1, 10, 10, 50)]))
    assert decode_image(ok, 1_000_000, 1920).shape == (480, 640, 3)
    for bad, code in [(b"", "invalid_frame"), (b"not an image", "invalid_frame"),
                      (ok, "frame_too_large"), (b"\x89PNG\r\n\x1a\n" + b"\0" * 8 + b"\0\0\x27\x10\0\0\x27\x10" + b"\0" * 20, "frame_dimensions")]:
        with pytest.raises(FrameError) as e:
            decode_image(bad, 100 if code == "frame_too_large" else 1_000_000, 1920)
        assert e.value.code == code


def test_peek_dimensions_png_and_jpeg():
    import cv2
    img = np.zeros((30, 40, 3), np.uint8)
    assert peek_dimensions(cv2.imencode(".png", img)[1].tobytes()) == (40, 30)
    assert peek_dimensions(cv2.imencode(".jpg", img)[1].tobytes()) == (40, 30)
