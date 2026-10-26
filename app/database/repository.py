"""Operasi database. Embedding tidak pernah keluar dari lapisan ini kecuali
sebagai TemplateIndex untuk Recognizer."""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Sequence

import numpy as np

from app.database.connection import Database
from app.database.models import TemplateIndex, UserRecord
from app.services.crypto import CryptoError, EmbeddingCipher

log = logging.getLogger(__name__)


class UserExistsError(Exception):
    pass


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _like(term: str) -> str:
    return "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


class SQLiteRepository:
    def __init__(self, db: Database, cipher: EmbeddingCipher, model_name: str):
        self.db = db
        self.cipher = cipher
        self.model_name = model_name

    # ---- tulis ----
    def create_user(self, user_id: str, name: str, embeddings: Sequence[np.ndarray],
                    qualities: Sequence[float] | None = None) -> UserRecord:
        now = utcnow()
        qualities = list(qualities) if qualities is not None else [None] * len(embeddings)
        with self.db.transaction() as conn:
            try:
                conn.execute("INSERT INTO users(user_id,name,consent_at,created_at) VALUES(?,?,?,?)",
                             (user_id, name, now, now))
            except sqlite3.IntegrityError as exc:
                raise UserExistsError(user_id) from exc
            conn.executemany(
                "INSERT INTO templates(user_id,model,dim,embedding,quality,created_at) VALUES(?,?,?,?,?,?)",
                [(user_id, self.model_name, int(e.size), self.cipher.encrypt(e), q, now)
                 for e, q in zip(embeddings, qualities)])
        return UserRecord(user_id, name, len(embeddings), now, now)

    def delete_user(self, user_id: str) -> tuple[bool, int]:
        """Hapus pengguna beserta SEMUA templatenya. Return (ada, jumlah_template)."""
        with self.db.transaction() as conn:
            n_t = conn.execute("DELETE FROM templates WHERE user_id=?", (user_id,)).rowcount
            n_u = conn.execute("DELETE FROM users WHERE user_id=?", (user_id,)).rowcount
        return n_u > 0, n_t

    def purge_older_than(self, days: int) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
        ids = [r["user_id"] for r in self.db.query("SELECT user_id FROM users WHERE created_at < ?", (cutoff,))]
        for uid in ids:
            self.delete_user(uid)
        return len(ids)

    # ---- baca ----
    def get_user(self, user_id: str) -> UserRecord | None:
        rows = self.db.query(
            "SELECT u.*, COUNT(t.id) AS template_count FROM users u "
            "LEFT JOIN templates t ON t.user_id=u.user_id WHERE u.user_id=? GROUP BY u.user_id", (user_id,))
        return self._row(rows[0]) if rows else None

    def list_users(self, search: str = "", page: int = 1, page_size: int = 10) -> tuple[list[UserRecord], int]:
        where, params = "", []
        if search.strip():
            where = "WHERE u.user_id LIKE ? ESCAPE '\\' OR u.name LIKE ? ESCAPE '\\'"
            params = [_like(search.strip())] * 2
        total = self.db.query(f"SELECT COUNT(*) AS c FROM users u {where}", params)[0]["c"]
        rows = self.db.query(
            f"SELECT u.*, COUNT(t.id) AS template_count FROM users u "
            f"LEFT JOIN templates t ON t.user_id=u.user_id {where} GROUP BY u.user_id "
            f"ORDER BY u.created_at DESC, u.user_id LIMIT ? OFFSET ?",
            [*params, page_size, (max(page, 1) - 1) * page_size])
        return [self._row(r) for r in rows], total

    def count_users(self) -> int:
        return self.db.query("SELECT COUNT(*) AS c FROM users")[0]["c"]

    def count_templates(self, same_model_only: bool = True) -> int:
        if same_model_only:
            return self.db.query("SELECT COUNT(*) AS c FROM templates WHERE model=?", (self.model_name,))[0]["c"]
        return self.db.query("SELECT COUNT(*) AS c FROM templates")[0]["c"]

    def load_index(self) -> TemplateIndex:
        """Muat template milik model aktif saja (embedding antar model tidak kompatibel)."""
        rows = self.db.query(
            "SELECT t.user_id, t.dim, t.embedding, u.name FROM templates t "
            "JOIN users u ON u.user_id=t.user_id WHERE t.model=? ORDER BY t.id", (self.model_name,))
        ids, vecs, names, skipped = [], [], {}, 0
        for r in rows:
            try:
                vecs.append(self.cipher.decrypt(r["embedding"], r["dim"]))
            except CryptoError as exc:
                skipped += 1
                log.error("Template milik %s dilewati: %s", r["user_id"], exc)
                continue
            ids.append(r["user_id"])
            names[r["user_id"]] = r["name"]
        matrix = np.vstack(vecs).astype(np.float32) if vecs else np.zeros((0, 0), dtype=np.float32)
        return TemplateIndex(ids, names, matrix, skipped)

    @staticmethod
    def _row(r: sqlite3.Row) -> UserRecord:
        return UserRecord(r["user_id"], r["name"], r["template_count"], r["created_at"], r["consent_at"])
