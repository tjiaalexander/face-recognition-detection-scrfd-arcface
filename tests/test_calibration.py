import numpy as np

from app.services.calibration import build_trials, choose_threshold, evaluate, split_dataset


def people(n_people=12, n_imgs=10):
    return {f"p{i}": [f"p{i}_{j}" for j in range(n_imgs)] for i in range(n_people)}


def test_split_has_no_leakage():
    sp = split_dataset(people())
    gallery = set(sp.enroll)
    ci, ei = set(sp.calib_impostors), set(sp.eval_impostors)
    assert gallery and ci and ei
    assert not (gallery & ci) and not (gallery & ei) and not (ci & ei)      # orang tidak tumpang tindih
    for p in gallery:
        e, c, v = set(sp.enroll[p]), set(sp.calib_known[p]), set(sp.eval_known[p])
        assert not (e & c) and not (e & v) and not (c & v) and v and c and e   # gambar tidak tumpang tindih


def test_split_is_deterministic_and_skips_small():
    data = people(8, 10) | {"kecil": ["x"]}
    a, b = split_dataset(data, seed=1), split_dataset(data, seed=1)
    assert a.enroll == b.enroll
    assert "kecil" in a.skipped or "kecil" in a.calib_impostors or "kecil" in a.eval_impostors


def test_choose_threshold_respects_far_target():
    rng = np.random.default_rng(0)
    imp = rng.normal(0.1, 0.1, 5000)
    t, warn = choose_threshold(imp, 0.01)
    assert warn is None and (imp >= t).mean() <= 0.01
    _, warn2 = choose_threshold(imp[:50], 0.001)
    assert warn2 is not None


def test_evaluate_metrics_on_synthetic_embeddings():
    rng = np.random.default_rng(1)
    dim = 64
    unit = lambda v: v / np.linalg.norm(v, axis=-1, keepdims=True)  # noqa: E731
    centers = unit(rng.normal(size=(5, dim)))
    gallery = {f"p{i}": unit(centers[i] + 0.05 * rng.normal(size=(2, dim))) for i in range(5)}
    known = {f"p{i}": unit(centers[i] + 0.1 * rng.normal(size=(6, dim))) for i in range(5)}
    imps = unit(rng.normal(size=(200, dim)))
    tr = build_trials(gallery, known, list(imps))
    t, _ = choose_threshold(tr.impostor_scores, 0.01)
    m = evaluate(tr, t)
    assert m["far"] <= 0.01 and m["recall"] > 0.9 and m["precision"] > 0.9
    assert m["frr"] + m["recall"] >= 0.999 - m["misidentification_rate"]
