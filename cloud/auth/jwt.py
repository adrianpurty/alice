"""JWT and API Key authentication for NexTTS cloud service."""

from __future__ import annotations

import os
from typing import Any, Optional

import jwt

from core.security.api_keys import ApiKeyService, api_key_service
from core.db.repository import Repository


class JWTValidationError(ValueError):
    """Raised when JWT validation fails."""

    pass


class JWTValidator:
    """JWT token validator for NexTTS cloud service."""

    def __init__(self, secret_key: str):
        """Initialize JWT validator.

        Args:
            secret_key: Secret key for JWT verification.
        """
        self._secret_key = secret_key
        self._algorithm = "HS256"

    def validate(self, token: str) -> dict[str, Any]:
        """Validate a JWT token and return claims.

        Args:
            token: JWT token string.

        Returns:
            Decoded token claims.

        Raises:
            JWTValidationError: If token is invalid, expired, or malformed.
        """
        try:
            claims = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
            )
            return claims
        except jwt.ExpiredSignatureError:
            raise JWTValidationError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise JWTValidationError(f"Invalid token: {e}")

    def extract_user_id(self, token: str) -> str:
        """Extract user_id from JWT token.

        Args:
            token: JWT token string.

        Returns:
            User ID from token claims.

        Raises:
            JWTValidationError: If token is invalid or missing user_id.
        """
        claims = self.validate(token)
        user_id = claims.get("user_id") or claims.get("sub")
        if not user_id:
            raise JWTValidationError("Token missing user_id claim")
        return str(user_id)

    def get_rate_limit(self, token: str) -> int | None:
        """Extract rate limit from JWT token.

        Args:
            token: JWT token string.

        Returns:
            Rate limit from token claims, or None if not specified.
        """
        try:
            claims = self.validate(token)
            rate_limit = claims.get("rate_limit")
            return int(rate_limit) if rate_limit is not None else None
        except JWTValidationError:
            return None


def get_secret() -> str:
    """Get JWT secret from environment.

    Returns:
        JWT secret key.

    Raises:
        ValueError: If JWT_SECRET is not set.
    """
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        raise ValueError("JWT_SECRET environment variable is not set")
    return secret


def create_validator() -> JWTValidator:
    """Create JWT validator with secret from environment.

    Returns:
        JWTValidator instance.
    """
    return JWTValidator(secret_key=get_secret())


def extract_token_from_metadata(metadata: list[tuple[str, str]]) -> str | None:
    """Extract JWT token from gRPC metadata.

    Args:
        metadata: gRPC metadata as list of (key, value) tuples.

    Returns:
        Token string if found in authorization header, None otherwise.
    """
    if not metadata:
        return None

    for key, value in metadata:
        if key.lower() == "authorization":
            if value.startswith("Bearer "):
                return value[7:]
            return value

    return None


def get_user_id_from_context(context) -> str | None:
    """Get user_id from gRPC context.

    Args:
        context: gRPC context object.

    Returns:
        User ID if attached to context, None otherwise.
    """
    return context.get("user_id")


def attach_user_to_context(context, user_id: str) -> None:
    """Attach user_id to gRPC context for billing.

    Args:
        context: gRPC context object.
        user_id: User ID to attach.
    """
    context["user_id"] = user_id


def require_auth(func):
    """Decorator to require JWT or API key authentication for gRPC methods.

    Extracts token from gRPC metadata, validates it (tries JWT first, then API key),
    and attaches user_id to the context for billing purposes.

    Args:
        func: gRPC handler function.

    Returns:
        Wrapped function with authentication check.
    """
    from functools import wraps

    @wraps(func)
    def wrapper(self, request, context):
        metadata = context.invocation_metadata()
        token = extract_token_from_metadata(metadata)

        if not token:
            context.abort(
                1,
                "Missing authorization token",
            )

        validator = create_validator()
        user_id = None
        auth_method = None

        if token.startswith("nxtts_"):
            from core.db import create_repository

            repo, _ = create_repository()
            try:
                user_id = api_key_service.validate_key(token, repo)
                auth_method = "api_key"
            finally:
                repo.close()
        else:
            try:
                user_id = validator.extract_user_id(token)
                auth_method = "jwt"
            except JWTValidationError:
                pass

        if not user_id:
            context.abort(
                1,
                "Invalid authentication token",
            )

        attach_user_to_context(context, user_id)
        context["auth_method"] = auth_method
        return func(self, request, context)

    return wrapper
