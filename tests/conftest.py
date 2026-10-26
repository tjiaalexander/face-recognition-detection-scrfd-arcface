import dataclasses

import pytest

from app.config import Settings
from app.database.connection import Database
from app.database.repository import SQLiteRepository
from app.services.crypto import EmbeddingCipher
from app.services.recognition import Recognizer


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=tmp_path, database_path=":memory:", model_name="antelopev2",
                    admin_password="rahasia-uji", ws_max_fps=1000.0, min_face_px=60,
                    register_min_samples=3)


@pytest.fixture
def repo(settings):
    return SQLiteRepository(Database(":memory:"), EmbeddingCipher(EmbeddingCipher.generate_key()), settings.model_name)


@pytest.fixture
def recognizer(repo, settings):
    return Recognizer(repo, settings)


def with_settings(s: Settings, **kw) -> Settings:
    return dataclasses.replace(s, **kw)
