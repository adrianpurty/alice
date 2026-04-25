import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch


class TestRateLimiter:
    @pytest.fixture
    def mock_repo(self):
        repo = MagicMock()
        return repo

    @pytest.fixture
    def limiter(self, mock_repo):
        from core.security.rate_limit import RateLimiter

        return RateLimiter(mock_repo)

    def test_init(self, limiter, mock_repo):
        assert limiter._repo == mock_repo

    def test_get_plan_existing_user(self, limiter, mock_repo):
        mock_profile = MagicMock()
        mock_profile.plan = "pro"
        mock_repo.get_profile.return_value = mock_profile

        plan = limiter.get_plan("user-123")
        assert plan == "pro"
        mock_repo.get_profile.assert_called_once_with("user-123")

    def test_get_plan_unknown_user(self, limiter, mock_repo):
        mock_repo.get_profile.return_value = None

        plan = limiter.get_plan("user-123")
        assert plan == "free"

    def test_check_limit_unlimited_plan(self, limiter, mock_repo):
        mock_profile = MagicMock()
        mock_profile.plan = "pro"
        mock_repo.get_profile.return_value = mock_profile

        allowed, reason = limiter.check_limit("user-123", "tts_generate")
        assert allowed is True
        assert reason is None

    def test_check_limit_unlimited_pay_as_you_go(self, limiter, mock_repo):
        mock_profile = MagicMock()
        mock_profile.plan = "pay_as_you_go"
        mock_repo.get_profile.return_value = mock_profile

        allowed, reason = limiter.check_limit("user-123", "tts_generate")
        assert allowed is True
        assert reason is None

    def test_check_limit_unlimited_enterprise(self, limiter, mock_repo):
        mock_profile = MagicMock()
        mock_profile.plan = "enterprise"
        mock_repo.get_profile.return_value = mock_profile

        allowed, reason = limiter.check_limit("user-123", "tts_generate")
        assert allowed is True
        assert reason is None

    def test_check_limit_within_limit(self, limiter, mock_repo):
        mock_profile = MagicMock()
        mock_profile.plan = "free"
        mock_repo.get_profile.return_value = mock_profile

        with patch.object(limiter, "_get_monthly_usage", return_value=50):
            allowed, reason = limiter.check_limit("user-123", "tts_generate")
            assert allowed is True
            assert reason is None

    def test_check_limit_exceeds_limit(self, limiter, mock_repo):
        mock_profile = MagicMock()
        mock_profile.plan = "free"
        mock_repo.get_profile.return_value = mock_profile

        with patch.object(limiter, "_get_monthly_usage", return_value=100):
            allowed, reason = limiter.check_limit("user-123", "tts_generate")
            assert allowed is False
            assert "Rate limit exceeded" in reason
            assert "100" in reason
            assert "free" in reason

    def test_get_remaining_unlimited(self, limiter, mock_repo):
        mock_profile = MagicMock()
        mock_profile.plan = "pro"
        mock_repo.get_profile.return_value = mock_profile

        remaining = limiter.get_remaining("user-123")
        assert remaining == -1

    def test_get_remaining_with_limit(self, limiter, mock_repo):
        mock_profile = MagicMock()
        mock_profile.plan = "free"
        mock_repo.get_profile.return_value = mock_profile

        with patch.object(limiter, "_get_monthly_usage", return_value=50):
            remaining = limiter.get_remaining("user-123")
            assert remaining == 50

    def test_get_remaining_zero(self, limiter, mock_repo):
        mock_profile = MagicMock()
        mock_profile.plan = "free"
        mock_repo.get_profile.return_value = mock_profile

        with patch.object(limiter, "_get_monthly_usage", return_value=100):
            remaining = limiter.get_remaining("user-123")
            assert remaining == 0


class TestRateLimitError:
    def test_exception(self):
        from core.security.rate_limit import RateLimitError

        msg = "Rate limit exceeded"
        error = RateLimitError(msg)
        assert str(error) == msg
