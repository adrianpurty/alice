import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .base import SessionLocal, get_session
from .models import ApiKey, CustomVoice, Profile, UsageLog


PLAN_LIMITS = {
    "free": {"requests_per_month": 100, "voices": 1, "audio_minutes": 10},
    "pay_as_you_go": {"requests_per_month": None, "voices": 5, "audio_minutes": None},
    "pro": {"requests_per_month": None, "voices": 10, "audio_minutes": None},
    "enterprise": {"requests_per_month": None, "voices": None, "audio_minutes": None},
}


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


class Repository:
    def __init__(self, session: Optional[Session] = None):
        self._session = session or SessionLocal()

    def close(self) -> None:
        self._session.close()

    def create_profile(self, email: str) -> Profile:
        profile = Profile(email=email, plan="free")
        self._session.add(profile)
        self._session.flush()
        self._session.refresh(profile)
        return profile

    def get_profile(self, user_id: str) -> Optional[Profile]:
        return self._session.get(Profile, user_id)

    def get_profile_by_email(self, email: str) -> Optional[Profile]:
        return self._session.execute(
            select(Profile).where(Profile.email == email)
        ).scalar_one_or_none()

    def create_api_key(self, user_id: str, name: str) -> str:
        raw_key = f"nv_{secrets.token_urlsafe(32)}"
        key_hash = _hash_key(raw_key)
        api_key = ApiKey(
            user_id=user_id,
            key_hash=key_hash,
            name=name,
        )
        self._session.add(api_key)
        self._session.flush()
        return raw_key

    def get_api_keys(self, user_id: str) -> list[ApiKey]:
        return list(
            self._session.execute(select(ApiKey).where(ApiKey.user_id == user_id))
            .scalars()
            .all()
        )

    def get_api_key_by_hash(self, key_hash: str) -> Optional[ApiKey]:
        return self._session.execute(
            select(ApiKey).where(ApiKey.key_hash == key_hash)
        ).scalar_one_or_none()

    def revoke_api_key(self, key_id: str) -> None:
        api_key = self._session.get(ApiKey, key_id)
        if api_key:
            api_key.is_active = False
            self._session.flush()

    def update_key_usage(self, key_id: str) -> None:
        api_key = self._session.get(ApiKey, key_id)
        if api_key:
            api_key.last_used_at = datetime.utcnow()
            self._session.flush()

    def log_usage(
        self,
        user_id: str,
        endpoint: str,
        tokens: int,
        api_key_id: Optional[str] = None,
    ) -> UsageLog:
        log = UsageLog(
            user_id=user_id,
            endpoint=endpoint,
            tokens_used=tokens,
            api_key_id=api_key_id,
        )
        self._session.add(log)
        self._session.flush()
        return log

    def get_usage(self, user_id: str, endpoint: Optional[str] = None) -> int:
        query = select(func.sum(UsageLog.tokens_used)).where(
            UsageLog.user_id == user_id
        )
        if endpoint:
            query = query.where(UsageLog.endpoint == endpoint)
        result = self._session.execute(query).scalar()
        return result or 0

    def get_requests_count(self, user_id: str) -> int:
        result = self._session.execute(
            select(func.sum(UsageLog.requests_count)).where(UsageLog.user_id == user_id)
        ).scalar()
        return result or 0

    def get_plan_limits(self, plan: str) -> dict:
        return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"]).copy()

    def create_custom_voice(
        self, user_id: str, name: str, voice_data: str, is_public: bool = False
    ) -> CustomVoice:
        voice = CustomVoice(
            user_id=user_id,
            name=name,
            voice_data=voice_data,
            is_public=is_public,
        )
        self._session.add(voice)
        self._session.flush()
        return voice

    def get_custom_voices(self, user_id: str) -> list[CustomVoice]:
        return list(
            self._session.execute(
                select(CustomVoice).where(CustomVoice.user_id == user_id)
            )
            .scalars()
            .all()
        )

    def get_custom_voice(self, voice_id: str) -> Optional[CustomVoice]:
        return self._session.get(CustomVoice, voice_id)

    def delete_custom_voice(self, voice_id: str) -> bool:
        voice = self._session.get(CustomVoice, voice_id)
        if voice:
            self._session.delete(voice)
            self._session.flush()
            return True
        return False

    def health_check(self) -> bool:
        try:
            self._session.execute(select(1))
            return True
        except Exception:
            return False


def create_repository() -> tuple[Repository, Session]:
    session = SessionLocal()
    repo = Repository(session)
    return repo, session
