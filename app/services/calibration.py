"""Logika kalibrasi threshold dan evaluasi (FAR, FRR, precision, recall).

Aturan anti-kebocoran:
  * Orang dibagi menjadi: gallery (terdaftar) dan impostor (tidak terdaftar). Impostor dibagi lagi
    menjadi impostor-kalibrasi dan impostor-evaluasi yang SALING LEPAS (orang berbeda).
  * Gambar milik orang gallery dibagi tiga bagian lepas: enroll / kalibrasi / evaluasi.
  * Threshold hanya dipilih dari data kalibrasi; angka akhir dihitung pada data evaluasi.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Sequence, TypeVar

import numpy as np

T = TypeVar("T")


@dataclass
class Split:
    enroll: dict[str, list]
    calib_known: dict[str, list]
    eval_known: dict[str, list]
    calib_impostors: dict[str, list]
    eval_impostors: dict[str, list]
    skipped: list[str]


def split_dataset(per_person: dict[str, list[T]], seed: int = 42, impostor_fraction: float = 0.4,
                  min_images: int = 3) -> Split:
    rng = random.Random(seed)
    people = sorted(p for p, imgs in per_person.items() if len(imgs) >= 1)
    skipped = [p for p, imgs in per_person.items() if len(imgs) < 1]
    rng.shuffle(people)
    n_imp = max(2, int(round(len(people) * impostor_fraction))) if len(people) >= 4 else 0
    impostors, gallery = people[:n_imp], people[n_imp:]
    half = len(impostors) // 2
    calib_imp = {p: list(per_person[p]) for p in impostors[:half]}
    eval_imp = {p: list(per_person[p]) for p in impostors[half:]}
    enroll, calib, evalk = {}, {}, {}
    for p in gallery:
        imgs = list(per_person[p])
        if len(imgs) < min_images:
            skipped.append(p)
            continue
        rng.shuffle(imgs)
        n_e = max(1, int(len(imgs) * 0.4))
        n_c = max(1, int(len(imgs) * 0.3))
        enroll[p], calib[p], evalk[p] = imgs[:n_e], imgs[n_e:n_e + n_c], imgs[n_e + n_c:]
        if not evalk[p]:  # pastikan evaluasi tidak kosong tanpa memakai gambar enroll
            evalk[p] = [calib[p].pop()] if len(calib[p]) > 1 else []
    return Split(enroll, calib, evalk, calib_imp, eval_imp, skipped)


def best_matches(gallery: dict[str, np.ndarray], probes: np.ndarray) -> tuple[list[str], np.ndarray]:
    """Untuk tiap probe: pengguna gallery dengan skor tertinggi dan skornya."""
    ids = [u for u, m in gallery.items() for _ in range(len(m))]
    mat = np.vstack([m for m in gallery.values()])
    sims = probes @ mat.T
    idx = sims.argmax(axis=1)
    return [ids[i] for i in idx], sims[np.arange(len(probes)), idx]


@dataclass
class Trials:
    known_true: list[str]
    known_pred: list[str]
    known_scores: np.ndarray
    impostor_scores: np.ndarray


def build_trials(gallery: dict[str, np.ndarray], known_probes: dict[str, np.ndarray],
                 impostor_probes: Sequence[np.ndarray]) -> Trials:
    true, probes = [], []
    for person, embs in known_probes.items():
        for e in embs:
            true.append(person)
            probes.append(e)
    pred, scores = best_matches(gallery, np.vstack(probes)) if probes else ([], np.zeros(0))
    imp = np.vstack(impostor_probes) if len(impostor_probes) else np.zeros((0, 1))
    imp_scores = best_matches(gallery, imp)[1] if len(imp) else np.zeros(0)
    return Trials(true, pred, scores, imp_scores)


def choose_threshold(impostor_scores: np.ndarray, far_target: float) -> tuple[float, str | None]:
    """Threshold terkecil dengan FAR kalibrasi <= far_target. Mengembalikan (threshold, peringatan)."""
    if len(impostor_scores) == 0:
        raise ValueError("Tidak ada data impostor untuk kalibrasi.")
    s = np.sort(impostor_scores)
    warn = None
    if far_target * len(s) < 1:
        warn = (f"Hanya {len(s)} percobaan impostor; FAR {far_target:g} tidak dapat diukur dengan andal. "
                "Tambah data impostor.")
    k = int(np.floor(far_target * len(s)))        # jumlah false accept yang masih ditoleransi
    t = float(s[-1]) + 1e-6 if k == 0 else float(s[-k - 1]) + 1e-6
    return t, warn


def evaluate(trials: Trials, threshold: float) -> dict:
    n_known, n_imp = len(trials.known_true), len(trials.impostor_scores)
    accepted = trials.known_scores >= threshold
    correct = np.array([t == p for t, p in zip(trials.known_true, trials.known_pred)], dtype=bool) \
        if n_known else np.zeros(0, dtype=bool)
    tp = int((accepted & correct).sum())
    misid = int((accepted & ~correct).sum())
    imp_fp = int((trials.impostor_scores >= threshold).sum())
    fp = misid + imp_fp
    return {
        "threshold": threshold, "known_probes": n_known, "impostor_probes": n_imp,
        "far": imp_fp / n_imp if n_imp else None,
        "frr": int((~accepted).sum()) / n_known if n_known else None,
        "misidentification_rate": misid / n_known if n_known else None,
        "precision": tp / (tp + fp) if (tp + fp) else None,
        "recall": tp / n_known if n_known else None,
    }
