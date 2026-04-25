"""Tests for JWT authentication."""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone

import jwt as pyjwt


class TestJWTValidator(unittest.TestCase):
    """Test JWTValidator class."""

    TEST_SECRET = "test-secret-key-for-unit-tests"

    def _create_token(self, payload: dict, secret: str = None) -> str:
        """Helper to create a JWT token for testing."""
        secret = secret or self.TEST_SECRET
        return pyjwt.encode(payload, secret, algorithm="HS256")

    def test_validate_valid_token(self):
        """Test validation of a valid token."""
        from cloud.auth.jwt import JWTValidator, JWTValidationError

        validator = JWTValidator(self.TEST_SECRET)
        payload = {"user_id": "user123", "rate_limit": 100}
        token = self._create_token(payload)

        claims = validator.validate(token)

        self.assertEqual(claims["user_id"], "user123")
        self.assertEqual(claims["rate_limit"], 100)

    def test_validate_expired_token(self):
        """Test validation fails for expired token."""
        from cloud.auth.jwt import JWTValidator, JWTValidationError

        validator = JWTValidator(self.TEST_SECRET)
        payload = {
            "user_id": "user123",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = self._create_token(payload)

        with self.assertRaises(JWTValidationError) as ctx:
            validator.validate(token)
        self.assertIn("expired", str(ctx.exception).lower())

    def test_validate_invalid_signature(self):
        """Test validation fails for wrong signature."""
        from cloud.auth.jwt import JWTValidator, JWTValidationError

        validator = JWTValidator(self.TEST_SECRET)
        token = self._create_token({"user_id": "user123"}, secret="wrong-secret")

        with self.assertRaises(JWTValidationError):
            validator.validate(token)

    def test_validate_malformed_token(self):
        """Test validation fails for malformed token."""
        from cloud.auth.jwt import JWTValidator, JWTValidationError

        validator = JWTValidator(self.TEST_SECRET)

        with self.assertRaises(JWTValidationError):
            validator.validate("not-a-valid-jwt")

    def test_extract_user_id_from_user_id_claim(self):
        """Test extracting user_id from user_id claim."""
        from cloud.auth.jwt import JWTValidator

        validator = JWTValidator(self.TEST_SECRET)
        token = self._create_token({"user_id": "user456"})

        user_id = validator.extract_user_id(token)

        self.assertEqual(user_id, "user456")

    def test_extract_user_id_from_sub_claim(self):
        """Test extracting user_id from sub claim as fallback."""
        from cloud.auth.jwt import JWTValidator

        validator = JWTValidator(self.TEST_SECRET)
        token = self._create_token({"sub": "user789"})

        user_id = validator.extract_user_id(token)

        self.assertEqual(user_id, "user789")

    def test_extract_user_id_missing(self):
        """Test extracting user_id fails when missing."""
        from cloud.auth.jwt import JWTValidator, JWTValidationError

        validator = JWTValidator(self.TEST_SECRET)
        token = self._create_token({"other": "claim"})

        with self.assertRaises(JWTValidationError) as ctx:
            validator.extract_user_id(token)
        self.assertIn("user_id", str(ctx.exception).lower())

    def test_get_rate_limit_present(self):
        """Test getting rate limit when present in token."""
        from cloud.auth.jwt import JWTValidator

        validator = JWTValidator(self.TEST_SECRET)
        token = self._create_token({"user_id": "user123", "rate_limit": 50})

        rate_limit = validator.get_rate_limit(token)

        self.assertEqual(rate_limit, 50)

    def test_get_rate_limit_missing(self):
        """Test getting rate limit returns None when missing."""
        from cloud.auth.jwt import JWTValidator

        validator = JWTValidator(self.TEST_SECRET)
        token = self._create_token({"user_id": "user123"})

        rate_limit = validator.get_rate_limit(token)

        self.assertIsNone(rate_limit)

    def test_get_rate_limit_invalid_token(self):
        """Test getting rate limit returns None for invalid token."""
        from cloud.auth.jwt import JWTValidator

        validator = JWTValidator(self.TEST_SECRET)

        rate_limit = validator.get_rate_limit("invalid-token")

        self.assertIsNone(rate_limit)


class TestExtractTokenFromMetadata(unittest.TestCase):
    """Test token extraction from gRPC metadata."""

    def test_extract_from_bearer_token(self):
        """Test extraction from Bearer token."""
        from cloud.auth.jwt import extract_token_from_metadata

        metadata = [("authorization", "Bearer mytoken123")]
        token = extract_token_from_metadata(metadata)

        self.assertEqual(token, "mytoken123")

    def test_extract_from_plain_token(self):
        """Test extraction from plain authorization header."""
        from cloud.auth.jwt import extract_token_from_metadata

        metadata = [("authorization", "mytoken456")]
        token = extract_token_from_metadata(metadata)

        self.assertEqual(token, "mytoken456")

    def test_extract_case_insensitive(self):
        """Test extraction is case insensitive for header name."""
        from cloud.auth.jwt import extract_token_from_metadata

        metadata = [("Authorization", "mytoken789")]
        token = extract_token_from_metadata(metadata)

        self.assertEqual(token, "mytoken789")

    def test_extract_returns_none_when_missing(self):
        """Test returns None when no authorization header."""
        from cloud.auth.jwt import extract_token_from_metadata

        metadata = [("other", "value")]
        token = extract_token_from_metadata(metadata)

        self.assertIsNone(token)

    def test_extract_returns_none_for_empty_metadata(self):
        """Test returns None for empty metadata."""
        from cloud.auth.jwt import extract_token_from_metadata

        token = extract_token_from_metadata(None)
        self.assertIsNone(token)

        token = extract_token_from_metadata([])
        self.assertIsNone(token)


class TestContextHelpers(unittest.TestCase):
    """Test context helper functions."""

    def test_attach_and_get_user_id(self):
        """Test attaching and retrieving user_id from context."""
        from cloud.auth.jwt import attach_user_to_context, get_user_id_from_context

        mock_context = {}
        attach_user_to_context(mock_context, "user999")

        user_id = get_user_id_from_context(mock_context)
        self.assertEqual(user_id, "user999")

    def test_get_user_id_returns_none_when_not_set(self):
        """Test get_user_id returns None when not set."""
        from cloud.auth.jwt import get_user_id_from_context

        mock_context = {}
        user_id = get_user_id_from_context(mock_context)

        self.assertIsNone(user_id)


class TestGetSecret(unittest.TestCase):
    """Test get_secret function."""

    @patch.dict(os.environ, {"JWT_SECRET": "my-secret-value"})
    def test_get_secret_returns_value(self):
        """Test get_secret returns value from environment."""
        from cloud.auth.jwt import get_secret

        secret = get_secret()
        self.assertEqual(secret, "my-secret-value")

    @patch.dict(os.environ, {}, clear=True)
    def test_get_secret_raises_when_not_set(self):
        """Test get_secret raises when environment variable not set."""
        from cloud.auth.jwt import get_secret

        with self.assertRaises(ValueError) as ctx:
            get_secret()
        self.assertIn("JWT_SECRET", str(ctx.exception))


class TestCreateValidator(unittest.TestCase):
    """Test create_validator function."""

    @patch.dict(os.environ, {"JWT_SECRET": "test-secret"})
    def test_create_validator(self):
        """Test create_validator returns configured validator."""
        from cloud.auth.jwt import create_validator, JWTValidator

        validator = create_validator()

        self.assertIsInstance(validator, JWTValidator)


if __name__ == "__main__":
    unittest.main()
