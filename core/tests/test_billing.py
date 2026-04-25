"""Tests for billing service."""

import pytest
from unittest.mock import Mock, patch

import sys
from types import ModuleType

billing_module = sys.modules.get("core.billing.stripe")
original_stripe_lib = None
if billing_module:
    original_stripe_lib = billing_module.stripe_lib


def mock_stripe_lib_present():
    sys.modules["stripe"] = Mock()


def mock_stripe_lib_missing():
    if "stripe" in sys.modules:
        del sys.modules["stripe"]
    billing_module = sys.modules.get("core.billing.stripe")
    if billing_module:
        billing_module.stripe_lib = None


class TestBillingService:
    """Test cases for BillingService."""

    def test_init_without_api_key(self):
        """Test initialization without API key."""
        mock_stripe_lib_missing()
        from core.billing import stripe as billing_stripe

        billing_stripe.STRIPE_API_KEY = None
        service = billing_stripe.BillingService(api_key=None)
        assert not service.is_configured

    def test_init_with_api_key_no_library(self):
        """Test initialization with API key but no stripe library."""
        mock_stripe_lib_missing()
        from core.billing import stripe as billing_stripe

        billing_stripe.STRIPE_API_KEY = "sk_test_123"
        service = billing_stripe.BillingService(api_key="sk_test_123")
        assert not service.is_configured

    @pytest.mark.asyncio
    async def test_create_customer_without_stripe(self):
        """Test creating customer when Stripe is not configured."""
        mock_stripe_lib_missing()
        from core.billing import stripe as billing_stripe

        billing_stripe.STRIPE_API_KEY = None
        service = billing_stripe.BillingService(api_key=None)
        customer_id = await service.create_customer("test@example.com", "user123")
        assert customer_id == "cus_test_user123"

    @pytest.mark.asyncio
    async def test_create_subscription_without_stripe(self):
        """Test creating subscription when Stripe is not configured."""
        mock_stripe_lib_missing()
        from core.billing import stripe as billing_stripe

        billing_stripe.STRIPE_API_KEY = None
        service = billing_stripe.BillingService(api_key=None)
        result = await service.create_subscription("cus_123", "pro")
        assert result["status"] == "active"
        assert "id" in result
        assert "items" in result

    @pytest.mark.asyncio
    async def test_cancel_subscription_without_stripe(self):
        """Test canceling subscription when Stripe is not configured."""
        mock_stripe_lib_missing()
        from core.billing import stripe as billing_stripe

        billing_stripe.STRIPE_API_KEY = None
        service = billing_stripe.BillingService(api_key=None)
        result = await service.cancel_subscription("sub_123")
        assert result["status"] == "canceled"

    @pytest.mark.asyncio
    async def test_create_usage_record_without_stripe(self):
        """Test creating usage record when Stripe is not configured."""
        mock_stripe_lib_missing()
        from core.billing import stripe as billing_stripe

        billing_stripe.STRIPE_API_KEY = None
        service = billing_stripe.BillingService(api_key=None)
        result = await service.create_usage_record("si_123", 100)
        assert result["quantity"] == 100

    @pytest.mark.asyncio
    async def test_get_invoices_without_stripe(self):
        """Test getting invoices when Stripe is not configured."""
        mock_stripe_lib_missing()
        from core.billing import stripe as billing_stripe

        billing_stripe.STRIPE_API_KEY = None
        service = billing_stripe.BillingService(api_key=None)
        invoices = await service.get_invoices("cus_123")
        assert invoices == []

    @pytest.mark.asyncio
    async def test_create_portal_session_without_stripe(self):
        """Test creating portal session when Stripe is not configured."""
        mock_stripe_lib_missing()
        from core.billing import stripe as billing_stripe

        billing_stripe.STRIPE_API_KEY = None
        service = billing_stripe.BillingService(api_key=None)
        url = await service.create_portal_session("cus_123")
        assert url.startswith("https://billing.stripe.com/")

    @pytest.mark.asyncio
    async def test_handle_webhook_without_stripe(self):
        """Test handling webhook when Stripe is not configured."""
        mock_stripe_lib_missing()
        from core.billing import stripe as billing_stripe

        billing_stripe.STRIPE_API_KEY = None
        service = billing_stripe.BillingService(api_key=None)
        result = await service.handle_webhook(b"{}", "sig_123")
        assert result["type"] == "test.webhook"

    @pytest.mark.asyncio
    async def test_create_subscription_with_stripe_raises_for_invalid_plan(self):
        """Test creating subscription with invalid plan when Stripe is configured."""
        mock_stripe_lib_present()
        import stripe as stripe_lib

        stripe_lib.StripeClient = Mock()
        mock_stripe = Mock()
        stripe_lib.StripeClient.return_value = mock_stripe

        from core.billing import stripe as billing_stripe

        billing_stripe.STRIPE_API_KEY = "sk_test_123"
        billing_stripe.stripe_lib = stripe_lib
        service = billing_stripe.BillingService(api_key="sk_test_123")

        with pytest.raises(ValueError, match="Unknown plan"):
            await service.create_subscription("cus_123", "invalid")
