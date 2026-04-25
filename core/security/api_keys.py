import hashlib
import secrets
from typing import Optional

from core.db.repository import Repository


class ApiKeyError(Exception):
    pass


class InvalidApiKeyError(ApiKeyError):
    pass


class ApiKeyService:
    PREFIX = "nxtts_"

    def generate_key(self) -> str:
        return f"{self.PREFIX}{secrets.token_urlsafe(32)}"

    def hash_key(self, key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()

    def validate_key(self, key: str, repo: Repository) -> Optional[str]:
        if not key.startswith(self.PREFIX):
            return None

        key_hash = self.hash_key(key)
        api_key = repo.get_api_key_by_hash(key_hash)

        if not api_key:
            return None

        if not api_key.is_active:
            return None

        repo.update_key_usage(str(api_key.id))
        return str(api_key.user_id)

    def revoke_key(self, key_id: str, repo: Repository) -> None:
        repo.revoke_api_key(key_id)

    def list_keys(self, user_id: str, repo: Repository) -> list:
        return repo.get_api_keys(user_id)


api_key_service = ApiKeyService()
