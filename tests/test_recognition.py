import dataclasses

import pytest

from app.config import Settings
from app.services.recognition import Detection, Identification, TemporalSmoother
from tests.fakes import identity_embedding


def enroll(repo, recognizer, uid, ident):
    repo.create_user(uid, f"Nama {uid}", [identity_embedding(ident, i) for i in range(3)])
    recognizer.reload()


def test_empty_database_is_unknown(recognizer):
    r = recognizer.identify(identity_embedding(1))
    assert not r.matched and r.user_id is None


def test_registered_identity_is_matched(repo, recognizer):
    enroll(repo, recognizer, "a", 1)
    enroll(repo, recognizer, "b", 2)
    r = recognizer.identify(identity_embedding(2, jitter_seed=99))
    assert r.matched and r.user_id == "b" and r.score > 0.9


def test_unregistered_face_is_rejected(repo, recognizer):
    enroll(repo, recognizer, "a", 1)
    r = recognizer.identify(identity_embedding(7, jitter_seed=5))
    assert not r.matched and r.user_id is None and r.score < recognizer._s.recognition_threshold


def test_threshold_validation(settings):
    settings.validate()
    for bad in (dict(recognition_threshold=1.5),
                dict(smoothing_min_votes=9), dict(register_min_samples=11), dict(model_name="x")):
        with pytest.raises(ValueError):
            dataclasses.replace(settings, **bad).validate()


def test_calibrated_threshold_file(tmp_path):
    s = Settings(data_dir=tmp_path)
    s.threshold_file.write_text('{"model":"antelopev2","threshold":0.512}')
    loaded = s.with_calibrated_threshold()
    assert loaded.recognition_threshold == 0.512 and loaded.threshold_calibrated
    s.threshold_file.write_text('{"model":"buffalo_l","threshold":0.3}')
    assert not s.with_calibrated_threshold().threshold_calibrated      # model berbeda -> diabaikan
    assert not s.with_calibrated_threshold(explicit=True).threshold_calibrated


def det(uid, score=0.8, box=(0, 0, 100, 100)):
    return Detection(box, Identification(uid, uid and uid.upper(), score, uid is not None))


def test_single_frame_never_confirms(settings):
    sm = TemporalSmoother(settings)
    assert sm.update([det("a")])[0].status == "tentative"


def test_confirms_after_consistent_votes(settings):
    sm = TemporalSmoother(settings)
    out = [sm.update([det("a")])[0] for _ in range(3)]
    assert [o.status for o in out] == ["tentative", "tentative", "confirmed"]
    assert out[-1].user_id == "a" and out[-1].votes == 3


def test_flicker_between_identities_not_confirmed(settings):
    sm = TemporalSmoother(settings)
    seq = ["a", "b", "a", "b", "c"]
    assert all(sm.update([det(u)])[0].status != "confirmed" for u in seq)


def test_unknown_stays_unknown_and_tracks_are_separate(settings):
    sm = TemporalSmoother(settings)
    for _ in range(4):
        res = sm.update([det(None, 0.2, (0, 0, 100, 100)), det("a", 0.9, (300, 0, 400, 100))])
    assert res[0].status == "unknown" and res[0].user_id is None
    assert res[1].status == "confirmed" and res[0].track_id != res[1].track_id


def test_track_expires(settings):
    sm = TemporalSmoother(settings)
    first = sm.update([det("a")])[0].track_id
    for _ in range(settings.track_ttl_frames + 2):
        sm.update([])
    assert sm.update([det("a")])[0].track_id != first
