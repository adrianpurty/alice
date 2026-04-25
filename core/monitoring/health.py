"""Health checks for NexTTS monitoring."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import psutil

if TYPE_CHECKING:
    from core.billing.stripe import BillingService
    from core.db.repository import Repository


class HealthChecker:
    """Health checker for NexTTS services."""

    def __init__(self, repo: Repository | None, billing_service: BillingService | None):
        self._repo = repo
        self._billing_service = billing_service

    def check_all(self) -> dict[str, Any]:
        """Run all health checks and return combined status."""
        db_check = self.check_database()
        stripe_check = self.check_stripe()
        system_check = self.check_system()

        checks = {
            "database": db_check,
            "stripe": stripe_check,
            "system": system_check,
        }

        healthy_count = sum(
            1 for check in checks.values() if check.get("healthy", False)
        )
        total_checks = len(checks)

        if healthy_count == total_checks:
            status = "healthy"
        elif healthy_count > 0:
            status = "degraded"
        else:
            status = "unhealthy"

        return {
            "status": status,
            "checks": checks,
            "timestamp": time.time(),
        }

    def check_database(self) -> dict[str, Any]:
        """Check database connectivity."""
        try:
            if self._repo is None:
                return {"healthy": False, "message": "Repository not initialized"}

            session = self._repo._session
            session.execute("SELECT 1")
            return {"healthy": True, "message": "Database connection OK"}

        except Exception as e:
            return {"healthy": False, "message": f"Database error: {str(e)}"}

    def check_stripe(self) -> dict[str, Any]:
        """Check Stripe connectivity."""
        try:
            if self._billing_service is None:
                return {"healthy": False, "message": "Billing service not initialized"}

            if not self._billing_service.is_configured:
                return {
                    "healthy": True,
                    "message": "Stripe not configured (test mode)",
                }

            import asyncio

            async def ping_stripe():
                if self._billing_service._stripe:
                    self._billing_service._stripe.users.me()
                    return True
                return False

            result = asyncio.get_event_loop().run_until_complete(ping_stripe())
            return {"healthy": result, "message": "Stripe API OK"}

        except Exception as e:
            return {"healthy": False, "message": f"Stripe error: {str(e)}"}

    def check_system(self) -> dict[str, Any]:
        """Check system resources (CPU and memory)."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            return {
                "healthy": cpu_percent < 90 and memory_percent < 90,
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
            }

        except Exception as e:
            return {
                "healthy": False,
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "message": f"System check error: {str(e)}",
            }
