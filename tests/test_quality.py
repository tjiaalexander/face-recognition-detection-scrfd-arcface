import cv2
import numpy as np

from app.services.face_engine import DetectedFace
from app.services.quality_check import assess_face, enhance_face_image
from app.utils.images import decode_image
from tests.fakes import render_scene


def face(box=(100, 100, 220, 220), kps=None, score=0.99):
    x1, y1, x2, y2 = box
    if kps is None:
        s = x2 - x1
        kps = np.array([[x1 + .3 * s, y1 + .38 * s], [x1 + .7 * s, y1 + .38 * s], [x1 + .5 * s, y1 + .6 * s],
                        [x1 + .35 * s, y1 + .8 * s], [x1 + .65 * s, y1 + .8 * s]], np.float32)
    return DetectedFace(tuple(map(float, box)), kps, score)


IMG = render_scene([(1, 100, 100, 120)])


def test_good_face_passes(settings):
    r = assess_face(IMG, face(), settings)
    assert r.ok, r.reasons


def test_too_small(settings):
    assert "face_too_small" in assess_face(IMG, face((100, 100, 130, 130)), settings).reasons


def test_low_confidence(settings):
    assert "low_confidence" in assess_face(IMG, face(score=0.3), settings).reasons


def test_blurry(settings):
    blurred = cv2.GaussianBlur(IMG, (51, 51), 0)
    assert "blurry" in assess_face(blurred, face(), settings).reasons


def test_dark_and_bright(settings):
    assert "too_dark" in assess_face(render_scene([(1, 100, 100, 120)], gain=0.2), face(), settings).reasons
    assert "too_bright" in assess_face(render_scene([(1, 100, 100, 120)], gain=1.6), face(), settings).reasons


def test_turned_and_tilted(settings):
    f = face()
    f.kps[2] = [f.kps[1][0], f.kps[2][1]]               # hidung digeser ke sisi mata kanan
    assert "face_turned" in assess_face(IMG, f, settings).reasons
    t = face()
    t.kps[1] = [t.kps[1][0], t.kps[0][1] + 80]
    assert "face_tilted" in assess_face(IMG, t, settings).reasons


def test_cut_off(settings):
    assert "face_cut_off" in assess_face(IMG, face((560, 100, 700, 240)), settings).reasons


def test_auto_enhance_increases_visible_contrast():
    dark = np.full((200, 200, 3), 20, dtype=np.uint8)
    enhanced = enhance_face_image(dark)
    assert enhanced.shape == dark.shape
    assert float(enhanced.mean()) > float(dark.mean())


def test_decode_image_downscales_large_phone_images():
    img = np.full((3088, 2316, 3), 180, dtype=np.uint8)
    encoded, _ = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    out = decode_image(encoded.tobytes(), max_bytes=10_000_000, max_side=1920)
    assert out.shape[0] <= 1920
    assert out.shape[1] <= 1920
