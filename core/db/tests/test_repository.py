import uuid
from unittest.mock import MagicMock, patch

import pytest


class TestRepository:
    @pytest.fixture(autouse=True)
    def setup(self):
        from core.db import repository

        self.repo = repository.Repository(session=MagicMock())
        self.mock_session = self.repo._session

    def test_create_profile(self):
        mock_profile = MagicMock()
        self.mock_session.add = MagicMock()
        self.mock_session.flush = MagicMock()
        self.mock_session.refresh = MagicMock()
        self.mock_session.add.return_value = mock_profile

        result = self.repo.create_profile("test@example.com")

        self.mock_session.add.assert_called_once()
        self.mock_session.flush.assert_called_once()
        assert result.email == "test@example.com"

    def test_get_profile(self):
        mock_profile = MagicMock()
        self.mock_session.get.return_value = mock_profile
        test_id = str(uuid.uuid4())

        result = self.repo.get_profile(test_id)

        self.mock_session.get.assert_called_once()
        assert result == mock_profile

    def test_get_profile_by_email(self):
        mock_profile = MagicMock()
        with patch.object(self.repo._session, "execute") as mock_execute:
            mock_execute.return_value.scalar_one_or_none.return_value = mock_profile

            result = self.repo.get_profile_by_email("test@example.com")

            assert result == mock_profile

    def test_get_plan_limits_free(self):
        limits = self.repo.get_plan_limits("free")
        assert limits == {"requests_per_month": 100, "voices": 1, "audio_minutes": 10}

    def test_get_plan_limits_pro(self):
        limits = self.repo.get_plan_limits("pro")
        assert limits == {
            "requests_per_month": None,
            "voices": 10,
            "audio_minutes": None,
        }

    def test_get_plan_limits_unknown(self):
        limits = self.repo.get_plan_limits("unknown_plan")
        assert limits == {"requests_per_month": 100, "voices": 1, "audio_minutes": 10}

    def test_get_plan_limits_enterprise(self):
        limits = self.repo.get_plan_limits("enterprise")
        assert limits == {
            "requests_per_month": None,
            "voices": None,
            "audio_minutes": None,
        }


class TestHashKey:
    def test_hash_key_consistency(self):
        from core.db.repository import _hash_key

        key = "test_key_123"
        hash1 = _hash_key(key)
        hash2 = _hash_key(key)

        assert hash1 == hash2
        assert len(hash1) == 64

    def test_hash_key_different(self):
        from core.db.repository import _hash_key

        hash1 = _hash_key("key1")
        hash2 = _hash_key("key2")

        assert hash1 != hash2
