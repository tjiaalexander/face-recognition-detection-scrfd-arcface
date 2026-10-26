"""Antarmuka liveness. SENGAJA tidak ada implementasi palsu: tanpa pemeriksaan nyata, status
selalu 'not_configured' dan passed=False. Tindakan sensitif harus menolak jika passed bukan True."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, Sequence

import numpy as np

Status = Literal["not_configured", "passed", "failed", "inconclusive"]


@dataclass(frozen=True)
class LivenessResult:
    status: Status
    passed: bool
    detail: str = ""


class LivenessChecker(ABC):
    status_name: str = "not_configured"

    @abstractmethod
    async def check(self, frames: Sequence[np.ndarray]) -> LivenessResult:
        """Periksa apakah frame berasal dari orang nyata (mis. model anti-spoofing atau challenge-response)."""


class NotConfiguredLiveness(LivenessChecker):
    async def check(self, frames: Sequence[np.ndarray]) -> LivenessResult:
        return LivenessResult("not_configured", False,
                              "Liveness belum dikonfigurasi; identitas tidak boleh dipakai untuk tindakan sensitif.")


def build_liveness(mode: str) -> LivenessChecker:
    if mode == "none":
        return NotConfiguredLiveness()
    raise NotImplementedError(
        f"LIVENESS_MODE='{mode}' belum diimplementasikan. Buat subclass LivenessChecker "
        "(lihat docs/PRIVACY.md) lalu daftarkan di build_liveness().")


def allowed_for_sensitive_action(liveness: LivenessResult, confirmed: bool) -> bool:
    return bool(confirmed and liveness.passed and liveness.status == "passed")
