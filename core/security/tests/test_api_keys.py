import pytest
from unittest.mock import MagicMock


class TestApiKeyService:
    @pytest.fixture
    def service(self):
        from core.security.api_keys import ApiKeyService

        return ApiKeyService()

    def test_generate_key_prefix(self, service):
        key = service.generate_key()
        assert key.startswith("nxtts_")

    def test_generate_key_length(self, service):
        key = service.generate_key()
        assert key.startswith("nxtts_")
        assert len(key) > 38

    def test_hash_key(self, service):
        key = "nxtts_testkey123"
        hashed = service.hash_key(key)
        assert len(hashed) == 64
        assert hashed.isalnum()

    def test_hash_key_consistency(self, service):
        key = "nxtts_testkey123"
        hash1 = service.hash_key(key)
        hash2 = service.hash_key(key)
        assert hash1 == hash2

    def test_validate_key_invalid_prefix(self, service):
        mock_repo = MagicMock()
        result = service.validate_key("invalid_key", mock_repo)
        assert result is None

    def test_validate_key_not_found(self, service):
        mock_repo = MagicMock()
        mock_repo.get_api_key_by_hash.return_value = None
        result = service.validate_key("nxtts_testkey", mock_repo)
        assert result is None

    def test_validate_key_inactive(self, service):
        mock_repo = MagicMock()
        mock_api_key = MagicMock()
        mock_api_key.is_active = False
        mock_repo.get_api_key_by_hash.return_value = mock_api_key
        result = service.validate_key("nxtts_testkey", mock_repo)
        assert result is None

    def test_validate_key_success(self, service):
        mock_repo = MagicMock()
        mock_api_key = MagicMock()
        mock_api_key.is_active = True
        mock_api_key.user_id = "user-123"
        mock_repo.get_api_key_by_hash.return_value = mock_api_key
        result = service.validate_key("nxtts_testkey", mock_repo)
        assert result == "user-123"

    def test_validate_key_updates_usage(self, service):
        mock_repo = MagicMock()
        mock_api_key = MagicMock()
        mock_api_key.is_active = True
        mock_api_key.user_id = "user-123"
        mock_api_key.id = "key-123"
        mock_repo.get_api_key_by_hash.return_value = mock_api_key
        service.validate_key("nxtts_testkey", mock_repo)
        mock_repo.update_key_usage.assert_called_once_with("key-123")

    def test_revoke_key(self, service):
        mock_repo = MagicMock()
        service.revoke_key("key-123", mock_repo)
        mock_repo.revoke_api_key.assert_called_once_with("key-123")

    def test_list_keys(self, service):
        mock_repo = MagicMock()
        mock_keys = [MagicMock(), MagicMock()]
        mock_repo.get_api_keys.return_value = mock_keys
        result = service.list_keys("user-123", mock_repo)
        mock_repo.get_api_keys.assert_called_once_with("user-123")
        assert result == mock_keys
