"""Tests for monitoring metrics module."""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch

parent = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(parent))

try:
    from core.monitoring import metrics
except ModuleNotFoundError:
    from monitoring import metrics


class TestRecordRequest:
    def test_record_request_increments_counter(self):
        with patch.object(metrics.REQUESTS_TOTAL, "labels") as mock_labels:
            mock_counter = metrics.REQUESTS_TOTAL.labels.return_value
            metrics.record_request("stream", "200", "free", 0.5)
            mock_labels.assert_called_once_with(
                endpoint="stream", status="200", plan="free"
            )
            mock_counter.inc.assert_called_once()

    def test_record_request_records_duration(self):
        with patch.object(metrics.REQUEST_DURATION, "labels") as mock_labels:
            mock_histogram = metrics.REQUEST_DURATION.labels.return_value
            metrics.record_request("generate", "200", "pro", 1.2)
            mock_histogram.observe.assert_called_once_with(1.2)


class TestRecordError:
    def test_record_error_increments_counter(self):
        with patch.object(metrics.ERRORS_TOTAL, "labels") as mock_labels:
            mock_counter = metrics.ERRORS_TOTAL.labels.return_value
            metrics.record_error("stream", "TimeoutError")
            mock_labels.assert_called_once_with(
                endpoint="stream", error_type="TimeoutError"
            )
            mock_counter.inc.assert_called_once()


class TestRecordUsage:
    def test_record_usage_increments_counter(self):
        with patch.object(metrics.TOKENS_USED, "labels") as mock_labels:
            mock_counter = metrics.TOKENS_USED.labels.return_value
            metrics.record_usage("pro", "generate", 150)
            mock_labels.assert_called_once_with(plan="pro", endpoint="generate")
            mock_counter.inc.assert_called_once_with(150)


class TestConnectionGauges:
    def test_increment_connections(self):
        with patch.object(metrics.ACTIVE_CONNECTIONS, "inc") as mock_inc:
            metrics.increment_connections()
            mock_inc.assert_called_once()

    def test_decrement_connections(self):
        with patch.object(metrics.ACTIVE_CONNECTIONS, "dec") as mock_dec:
            metrics.decrement_connections()
            mock_dec.assert_called_once()


class TestMetricsExport:
    def test_metrics_returns_bytes(self):
        with patch.object(metrics, "generate_latest") as mock_generate:
            mock_generate.return_value = b"# HELP nexxtts_requests_total"
            result = metrics.metrics()
            mock_generate.assert_called_once()
            assert isinstance(result, bytes)
