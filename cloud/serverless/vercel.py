"""Serverless HTTP API for NexTTS cloud service."""

from __future__ import annotations

import base64
import os
from typing import Any

from flask import Blueprint, Flask, jsonify, request

try:
    from core.monitoring import metrics
    from core.monitoring.health import HealthChecker
except ModuleNotFoundError:
    from monitoring import metrics
    from monitoring.health import HealthChecker

try:
    from cloud.auth.jwt import JWTValidationError, create_validator
except ModuleNotFoundError:
    from auth.jwt import JWTValidationError, create_validator

try:
    from core.billing import BillingService
    from core.billing.stripe import STRIPE_PRICES
except ModuleNotFoundError:
    from billing import BillingService
    from billing.stripe import STRIPE_PRICES

api = Blueprint("api", __name__)

billing_service = BillingService()
health_checker = HealthChecker(None, billing_service)


def _get_token() -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    if auth:
        return auth
    return request.args.get("token")


def _require_auth() -> str:
    token = _get_token()
    if not token:
        raise JWTValidationError("Missing authorization token")
    validator = create_validator()
    return validator.extract_user_id(token)


def _handle_error(e: Exception) -> tuple[dict, int]:
    name = type(e).__name__
    msg = str(e)
    return jsonify({"error": name, "message": msg}), 400


@api.route("/health", methods=["GET"])
def health():
    """Health check endpoint with system diagnostics."""
    health_result = health_checker.check_all()
    status_code = 200 if health_result["status"] == "healthy" else 503
    return jsonify(health_result), status_code


@api.route("/metrics", methods=["GET"])
def prometheus_metrics():
    """Prometheus metrics endpoint."""
    return (
        metrics.metrics(),
        200,
        {"Content-Type": "text/plain; version=0.0.4; charset=utf-8"},
    )


@api.route("/v1/tts/stream", methods=["GET", "POST"])
def stream_tts():
    """Stream TTS audio chunks.

    GET: Initiate stream with text as query param
    POST: Full stream request with JSON body
    """
    try:
        _require_auth()
    except JWTValidationError as e:
        return _handle_error(e)

    try:
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            text = data.get("text", "")
            voice = data.get("voice", "")
            inference_steps = int(data.get("inference_steps", 50))
            temperature = float(data.get("temperature", 0.7))
            cfg_scale = float(data.get("cfg_scale", 1.0))
        else:
            text = request.args.get("text", "")
            voice = request.args.get("voice", "")
            inference_steps = int(request.args.get("inference_steps", 50))
            temperature = float(request.args.get("temperature", 0.7))
            cfg_scale = float(request.args.get("cfg_scale", 1.0))

        if not text:
            return jsonify({"error": "BadRequest", "message": "text is required"}), 400

        return jsonify(
            {
                "message": "Streaming endpoint - connect via gRPC for actual streaming",
                "text": text,
                "voice": voice,
                "inference_steps": inference_steps,
                "temperature": temperature,
                "cfg_scale": cfg_scale,
            }
        )

    except (ValueError, TypeError) as e:
        return _handle_error(e)


@api.route("/v1/tts/generate", methods=["POST"])
def generate_tts():
    """Generate full TTS audio.

    POST: Generate audio from text
    Returns base64-encoded WAV audio.
    """
    try:
        _require_auth()
    except JWTValidationError as e:
        return _handle_error(e)

    try:
        data = request.get_json(silent=True) or {}
        text = data.get("text", "")
        voice = data.get("voice", "")
        inference_steps = int(data.get("inference_steps", 50))
        output_format = data.get("format", "wav")

        if not text:
            return jsonify({"error": "BadRequest", "message": "text is required"}), 400

        return jsonify(
            {
                "message": "Generate endpoint - connect via gRPC for actual synthesis",
                "text": text,
                "voice": voice,
                "inference_steps": inference_steps,
                "format": output_format,
            }
        )

    except (ValueError, TypeError) as e:
        return _handle_error(e)


@api.route("/v1/asr/transcribe", methods=["POST"])
def transcribe():
    """Transcribe audio data.

    POST: Upload audio for transcription
    Supports base64-encoded PCM16 audio.
    """
    try:
        _require_auth()
    except JWTValidationError as e:
        return _handle_error(e)

    try:
        data = request.get_json(silent=True) or {}
        audio_data = data.get("audio_data", "")
        hotwords = data.get("hotwords", {})
        include_timestamps = bool(data.get("include_timestamps", False))
        include_speakers = bool(data.get("include_speakers", False))

        if not audio_data:
            return jsonify(
                {"error": "BadRequest", "message": "audio_data is required"}
            ), 400

        return jsonify(
            {
                "message": "Transcribe endpoint - connect via gRPC for actual transcription",
                "text": "",
                "segments": [],
            }
        )

    except (ValueError, TypeError) as e:
        return _handle_error(e)


@api.route("/v1/billing/subscribe", methods=["POST"])
def subscribe():
    """Create a subscription for the authenticated user.

    POST: { "plan": "pro" | "enterprise" }
    """
    try:
        user_id = _require_auth()
    except JWTValidationError as e:
        return _handle_error(e)

    try:
        data = request.get_json(silent=True) or {}
        plan = data.get("plan", "pro")

        if plan not in STRIPE_PRICES:
            return jsonify(
                {"error": "BadRequest", "message": f"Invalid plan: {plan}"}
            ), 400

        import asyncio

        customer_id = f"cus_{user_id}"
        subscription = asyncio.get_event_loop().run_until_complete(
            billing_service.create_subscription(customer_id, plan)
        )

        return jsonify(
            {
                "subscription_id": subscription["id"],
                "status": subscription["status"],
            }
        )

    except ValueError as e:
        return _handle_error(e)


@api.route("/v1/billing/invoices", methods=["GET"])
def invoices():
    """List invoices for the authenticated user.

    Returns list of invoices.
    """
    try:
        user_id = _require_auth()
    except JWTValidationError as e:
        return _handle_error(e)

    try:
        customer_id = f"cus_{user_id}"
        import asyncio

        invoices_list = asyncio.get_event_loop().run_until_complete(
            billing_service.get_invoices(customer_id)
        )

        return jsonify({"invoices": invoices_list})

    except Exception as e:
        return _handle_error(e)


@api.route("/v1/billing/portal", methods=["POST"])
def portal():
    """Create a customer portal session.

    POST: { "return_url": "https://..." }
    """
    try:
        user_id = _require_auth()
    except JWTValidationError as e:
        return _handle_error(e)

    try:
        customer_id = f"cus_{user_id}"
        import asyncio

        portal_url = asyncio.get_event_loop().run_until_complete(
            billing_service.create_portal_session(customer_id)
        )

        return jsonify({"portal_url": portal_url})

    except Exception as e:
        return _handle_error(e)


@api.route("/v1/billing/webhook", methods=["POST"])
def webhook():
    """Handle Stripe webhooks.

    POST: Raw Stripe webhook payload
    """
    payload = request.get_data()
    signature = request.headers.get("Stripe-Signature", "")

    try:
        import asyncio

        event = asyncio.get_event_loop().run_until_complete(
            billing_service.handle_webhook(payload, signature)
        )

        if event and event.get("type") == "subscription_updated":
            return jsonify({"status": "processed", "event": "subscription_updated"})
        elif event and event.get("type") == "subscription_deleted":
            return jsonify({"status": "processed", "event": "subscription_deleted"})

        return jsonify({"status": "received"})

    except ValueError as e:
        return jsonify({"error": "WebhookError", "message": str(e)}), 400
    except Exception as e:
        return _handle_error(e)


app = Flask(__name__)
app.register_blueprint(api, url_prefix="/api")
