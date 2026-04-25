"""Tests for health checks."""

import unittest
from unittest.mock import patch, MagicMock


class TestHealthChecker(unittest.TestCase):
    """Test HealthChecker class."""

    def test_init_with_none(self):
        """Test initialization with None dependencies."""
        from core.monitoring.health import HealthChecker

        checker = HealthChecker(None, None)
        self.assertIsNone(checker._repo)
        self.assertIsNone(checker._billing_service)

    def test_check_all_all_healthy(self):
        """Test check_all when all checks are healthy."""
        from core.monitoring.health import HealthChecker

        checker = HealthChecker(None, None)
        result = checker.check_all()

        self.assertIn("status", result)
        self.assertIn("checks", result)
        self.assertIn("timestamp", result)
        self.assertIn("database", result["checks"])
        self.assertIn("stripe", result["checks"])
        self.assertIn("system", result["checks"])

    def test_check_database_no_repo(self):
        """Test database check when repo is None."""
        from core.monitoring.health import HealthChecker

        checker = HealthChecker(None, None)
        result = checker.check_database()

        self.assertFalse(result["healthy"])
        self.assertIn("not initialized", result["message"])

    def test_check_stripe_no_service(self):
        """Test Stripe check when billing service is None."""
        from core.monitoring.health import HealthChecker

        checker = HealthChecker(None, None)
        result = checker.check_stripe()

        self.assertFalse(result["healthy"])
        self.assertIn("not initialized", result["message"])

    def test_check_stripe_not_configured(self):
        """Test Stripe check when not configured."""
        from core.billing.stripe import BillingService
        from core.monitoring.health import HealthChecker

        billing_service = BillingService(api_key=None)
        checker = HealthChecker(None, billing_service)
        result = checker.check_stripe()

        self.assertTrue(result["healthy"])
        self.assertIn("not configured", result["message"])

    def test_check_system(self):
        """Test system resource check."""
        from core.monitoring.health import HealthChecker

        checker = HealthChecker(None, None)
        result = checker.check_system()

        self.assertIn("healthy", result)
        self.assertIn("cpu_percent", result)
        self.assertIn("memory_percent", result)
        self.assertIsInstance(result["cpu_percent"], float)
        self.assertIsInstance(result["memory_percent"], float)

    def test_status_logic_all_healthy(self):
        """Test status is healthy when all checks pass."""
        from core.billing.stripe import BillingService
        from core.monitoring.health import HealthChecker

        mock_repo = MagicMock()
        mock_repo._session = MagicMock()

        billing_service = BillingService(api_key=None)
        checker = HealthChecker(mock_repo, billing_service)
        result = checker.check_all()

        self.assertEqual(result["status"], "healthy")

    def test_check_database_with_mock(self):
        """Test database check with mocked session."""
        from core.monitoring.health import HealthChecker

        mock_repo = MagicMock()
        mock_session = MagicMock()
        mock_repo._session = mock_session

        checker = HealthChecker(mock_repo, None)
        result = checker.check_database()

        self.assertTrue(result["healthy"])
        mock_session.execute.assert_called_once()

    def test_check_database_with_exception(self):
        """Test database check handles exceptions."""
        from core.monitoring.health import HealthChecker

        mock_repo = MagicMock()
        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("DB connection failed")
        mock_repo._session = mock_session

        checker = HealthChecker(mock_repo, None)
        result = checker.check_database()

        self.assertFalse(result["healthy"])
        self.assertIn("connection failed", result["message"])


class TestHealthEndpoint(unittest.TestCase):
    """Test /health endpoint."""

    def test_health_endpoint_returns_json(self):
        """Test health endpoint returns proper JSON."""
        from cloud.serverless.vercel import api, health_checker
        from flask import Flask

        app = Flask(__name__)
        app.register_blueprint(api)
        client = app.test_client()

        response = client.get("/health")

        self.assertIn(response.status_code, [200, 503])
        data = response.get_json()
        self.assertIn("status", data)
        self.assertIn("checks", data)
        self.assertIn("timestamp", data)


if __name__ == "__main__":
    unittest.main()
