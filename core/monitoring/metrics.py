"""Prometheus metrics for NexTTS monitoring."""

from prometheus_client import Counter, Histogram, Gauge, generate_latest

REQUESTS_TOTAL = Counter(
    "nexxtts_requests_total", "Total requests", ["endpoint", "status", "plan"]
)

REQUEST_DURATION = Histogram(
    "nexxtts_request_duration_seconds", "Request duration", ["endpoint"]
)

ACTIVE_CONNECTIONS = Gauge("nexxtts_active_connections", "Active connections")

ERRORS_TOTAL = Counter(
    "nexxtts_errors_total", "Total errors", ["endpoint", "error_type"]
)

TOKENS_USED = Counter(
    "nexxtts_tokens_used_total", "Total tokens used", ["plan", "endpoint"]
)


def record_request(endpoint: str, status: str, plan: str, duration: float) -> None:
    """Record a request with its endpoint, status, plan, and duration."""
    REQUESTS_TOTAL.labels(endpoint=endpoint, status=status, plan=plan).inc()
    REQUEST_DURATION.labels(endpoint=endpoint).observe(duration)


def record_error(endpoint: str, error_type: str) -> None:
    """Record an error for a specific endpoint."""
    ERRORS_TOTAL.labels(endpoint=endpoint, error_type=error_type).inc()


def record_usage(plan: str, endpoint: str, tokens: int) -> None:
    """Record token usage for billing."""
    TOKENS_USED.labels(plan=plan, endpoint=endpoint).inc(tokens)


def metrics() -> bytes:
    """Export all metrics for /metrics endpoint."""
    return generate_latest()


def increment_connections() -> None:
    """Increment active connections."""
    ACTIVE_CONNECTIONS.inc()


def decrement_connections() -> None:
    """Decrement active connections."""
    ACTIVE_CONNECTIONS.dec()
