"""Stripe billing service for NexTTS."""

from __future__ import annotations

import os
from typing import Any

try:
    import stripe as stripe_lib
except ImportError:
    stripe_lib = None

STRIPE_PRICES = {
    "pro": os.environ.get("STRIPE_PRICE_PRO", "price_pro"),
    "enterprise": os.environ.get("STRIPE_PRICE_ENTERPRISE", "price_enterprise"),
}

STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")


class BillingService:
    """Stripe billing service for managing customers and subscriptions."""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or STRIPE_API_KEY
        self._stripe = (
            stripe_lib.StripeClient(self._api_key)
            if self._api_key and stripe_lib
            else None
        )

    @property
    def is_configured(self) -> bool:
        return self._stripe is not None

    async def create_customer(self, email: str, user_id: str) -> str:
        """Create a Stripe customer.

        Args:
            email: Customer email address
            user_id: Internal user ID

        Returns:
            Stripe customer ID
        """
        if not self._stripe:
            return f"cus_test_{user_id}"

        customer = self._stripe.customers.create(
            email=email, metadata={"user_id": user_id}
        )
        return customer.id

    async def create_subscription(self, customer_id: str, plan: str) -> dict[str, Any]:
        """Create a subscription for a customer.

        Args:
            customer_id: Stripe customer ID
            plan: Plan name ('pro' or 'enterprise')

        Returns:
            Subscription object with id and status
        """
        if not self._stripe:
            return {
                "id": f"sub_test_{customer_id}",
                "status": "active",
                "items": {"data": [{"id": f"si_test_{customer_id}"}]},
            }

        price_id = STRIPE_PRICES.get(plan)
        if not price_id:
            raise ValueError(f"Unknown plan: {plan}")

        subscription = self._stripe.subscriptions.create(
            customer=customer_id,
            items=[{"price": price_id}],
        )
        return {
            "id": subscription.id,
            "status": subscription.status,
            "items": {"data": [{"id": subscription.items.data[0].id}]},
        }

    async def cancel_subscription(self, subscription_id: str) -> dict[str, Any]:
        """Cancel a subscription.

        Args:
            subscription_id: Stripe subscription ID

        Returns:
            Updated subscription object
        """
        if not self._stripe:
            return {
                "id": subscription_id,
                "status": "canceled",
            }

        subscription = self._stripe.subscriptions.cancel(subscription_id)
        return {
            "id": subscription.id,
            "status": subscription.status,
        }

    async def create_usage_record(
        self, subscription_item_id: str, quantity: int
    ) -> dict[str, Any]:
        """Report metered usage for a subscription item.

        Args:
            subscription_item_id: Stripe subscription item ID
            quantity: Usage quantity to record

        Returns:
            Usage record object
        """
        if not self._stripe:
            return {
                "id": f"mbur_test_{subscription_item_id}",
                "quantity": quantity,
            }

        record = self._stripe.usage_records.create(
            subscription_item=subscription_item_id,
            quantity=quantity,
            action="increment",
        )
        return {
            "id": record.id,
            "quantity": record.quantity,
        }

    async def get_invoices(self, customer_id: str) -> list[dict[str, Any]]:
        """List invoices for a customer.

        Args:
            customer_id: Stripe customer ID

        Returns:
            List of invoice objects
        """
        if not self._stripe:
            return []

        invoices = self._stripe.invoices.list(customer=customer_id)
        return [
            {
                "id": inv.id,
                "number": inv.number,
                "amount_due": inv.amount_due,
                "status": inv.status,
                "created": inv.created,
            }
            for inv in invoices.data
        ]

    async def create_portal_session(self, customer_id: str) -> str:
        """Create a customer portal session URL.

        Args:
            customer_id: Stripe customer ID

        Returns:
            Portal session URL
        """
        if not self._stripe:
            return f"https://billing.stripe.com/p/test/{customer_id}"

        session = self._stripe.billing_portal.sessions.create(
            customer=customer_id,
            return_url=os.environ.get(
                "STRIPE_PORTAL_RETURN_URL", "https://nexxtts.com/dashboard"
            ),
        )
        return session.url

    async def handle_webhook(
        self, payload: bytes, signature: str
    ) -> dict[str, Any] | None:
        """Handle Stripe webhook events.

        Args:
            payload: Raw webhook payload
            signature: Stripe signature header

        Returns:
            Event data if valid, None otherwise
        """
        if not self._stripe:
            return {"type": "test.webhook", "data": {"object": {}}}

        webhook_secret = STRIPE_WEBHOOK_SECRET
        if not webhook_secret:
            raise ValueError("STRIPE_WEBHOOK_SECRET not configured")

        try:
            event = self._stripe.webhooks.construct_event(
                payload, signature, webhook_secret
            )
        except Exception as e:
            raise ValueError(f"Invalid webhook signature: {e}")

        event_type = event.type
        data = event.data.object

        if event_type == "customer.subscription.updated":
            return {
                "type": "subscription_updated",
                "subscription_id": data.id,
                "status": data.status,
                "customer_id": data.customer,
            }
        elif event_type == "customer.subscription.deleted":
            return {
                "type": "subscription_deleted",
                "subscription_id": data.id,
                "customer_id": data.customer,
            }

        return {"type": event_type, "data": {"object": data}}
