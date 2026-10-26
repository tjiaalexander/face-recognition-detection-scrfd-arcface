import numpy as np
import pytest

from app.database.connection import Database
from app.database.repository import SQLiteRepository, UserExistsError
from app.services.crypto import EmbeddingCipher
from tests.fakes import identity_embedding


def make(repo, uid, name="Nama", ident=1, n=3):
    return repo.create_user(uid, name, [identity_embedding(ident, i) for i in range(n)])


def test_empty_database(repo):
    assert repo.count_users() == 0
    assert repo.list_users() == ([], 0)
    idx = repo.load_index()
    assert idx.size == 0


def test_create_list_search_paginate(repo):
    for i in range(25):
        make(repo, f"u{i:02d}", f"Orang {i}", ident=i % 10)
    items, total = repo.list_users(page=1, page_size=10)
    assert total == 25 and len(items) == 10 and items[0].template_count == 3
    assert len(repo.list_users(page=3, page_size=10)[0]) == 5
    assert repo.list_users(search="Orang 7")[1] == 1
    assert repo.list_users(search="%")[1] == 0       # wildcard di-escape
    assert repo.list_users(search="u1")[1] == 10


def test_duplicate_user_id_rolls_back(repo):
    make(repo, "a")
    with pytest.raises(UserExistsError):
        make(repo, "a")
    assert repo.count_templates() == 3


def test_delete_removes_all_templates(repo):
    make(repo, "a", n=4)
    make(repo, "b", ident=2)
    existed, n = repo.delete_user("a")
    assert existed and n == 4
    assert repo.get_user("a") is None
    assert repo.db.query("SELECT COUNT(*) c FROM templates WHERE user_id='a'")[0]["c"] == 0
    assert repo.count_templates() == 3
    assert repo.delete_user("a") == (False, 0)


def test_index_filters_by_model_and_survives_wrong_key(repo):
    make(repo, "a")
    other = SQLiteRepository(repo.db, repo.cipher, "buffalo_l")
    assert other.load_index().size == 0 and other.count_templates(False) == 3
    wrong = SQLiteRepository(repo.db, EmbeddingCipher(EmbeddingCipher.generate_key()), repo.model_name)
    idx = wrong.load_index()
    assert idx.size == 0 and idx.skipped == 3


def test_purge_older_than(repo):
    make(repo, "old")
    repo.db.query("SELECT 1")
    with repo.db.transaction() as c:
        c.execute("UPDATE users SET created_at='2000-01-01T00:00:00+00:00'")
    make(repo, "new", ident=2)
    assert repo.purge_older_than(30) == 1
    assert repo.get_user("old") is None and repo.get_user("new")
