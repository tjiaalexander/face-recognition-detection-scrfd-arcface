from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class UserRecord:
    user_id: str
    name: str
    template_count: int
    created_at: str
    consent_at: str


@dataclass
class TemplateIndex:
    """Seluruh template (sudah didekripsi) di memori untuk pencocokan cepat."""
    user_ids: list[str] = field(default_factory=list)   # satu entri per template
    names: dict[str, str] = field(default_factory=dict)
    matrix: np.ndarray = field(default_factory=lambda: np.zeros((0, 0), dtype=np.float32))
    skipped: int = 0                                     # template gagal didekripsi

    @property
    def size(self) -> int:
        return len(self.user_ids)
