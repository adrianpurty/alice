from datetime import datetime
from typing import Optional, Tuple

from core.db.repository import PLAN_LIMITS, Repository


class RateLimitError(Exception):
    """Exception raised when rate limit is exceeded."""

    pass


class RateLimiter:
    PLAN_LIMITS = PLAN_LIMITS

    def __init__(self, repo: Repository):
        self._repo = repo

    def get_plan(self, user_id: str) -> str:
        profile = self._repo.get_profile(user_id)
        if not profile:
            return "free"
        return profile.plan

    def check_limit(self, user_id: str, endpoint: str) -> Tuple[bool, Optional[str]]:
        plan = self.get_plan(user_id)
        limits = self.PLAN_LIMITS.get(plan, self.PLAN_LIMITS["free"])

        monthly_limit = limits.get("requests_per_month")
        if monthly_limit is None:
            return True, None

        usage = self._get_monthly_usage(user_id, endpoint)
        remaining = monthly_limit - usage

        if remaining <= 0:
            return (
                False,
                f"Rate limit exceeded. Your {plan} plan allows {monthly_limit} requests per month.",
            )

        return True, None

    def get_remaining(self, user_id: str, endpoint: Optional[str] = None) -> int:
        plan = self.get_plan(user_id)
        limits = self.PLAN_LIMITS.get(plan, self.PLAN_LIMITS["free"])

        monthly_limit = limits.get("requests_per_month")
        if monthly_limit is None:
            return -1

        usage = self._get_monthly_usage(user_id, endpoint)
        return max(0, monthly_limit - usage)

    def _get_monthly_usage(self, user_id: str, endpoint: Optional[str] = None) -> int:
        from datetime import timedelta
        from sqlalchemy import and_, func, select
        from core.db.models import UsageLog
        from core.db.base import SessionLocal

        session = SessionLocal()
        try:
            now = datetime.utcnow()
            start_of_month = now.replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            if now.month == 12:
                end_of_month = start_of_month.replace(year=now.year + 1, month=1)
            else:
                end_of_month = start_of_month.replace(month=now.month + 1)

            query = select(func.count(UsageLog.id)).where(
                and_(
                    UsageLog.user_id == user_id,
                    UsageLog.created_at >= start_of_month,
                    UsageLog.created_at < end_of_month,
                )
            )
            if endpoint:
                query = query.where(UsageLog.endpoint == endpoint)

            result = session.execute(query).scalar()
            return result or 0
        finally:
            session.close()


rate_limiter = RateLimiter(None)
