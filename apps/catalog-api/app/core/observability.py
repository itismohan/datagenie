import json
import logging
import sys
from datetime import datetime, timezone

from prometheus_client import Counter, Histogram


REQUEST_COUNT = Counter(
    "datagenie_http_requests_total",
    "Completed HTTP requests grouped by API route, method, and status.",
    ["route", "method", "status"],
)
REQUEST_LATENCY = Histogram(
    "datagenie_http_request_duration_seconds",
    "HTTP request duration grouped by API route and method.",
    ["route", "method"],
)
UNHANDLED_ERRORS = Counter(
    "datagenie_unhandled_errors_total",
    "Unexpected application errors grouped by exception class.",
    ["exception_type"],
)
RATE_LIMIT_REJECTIONS = Counter(
    "datagenie_rate_limit_rejections_total",
    "Requests rejected by the distributed API rate limiter.",
    ["method"],
)
RATE_LIMIT_STORE_FAILURES = Counter(
    "datagenie_rate_limit_store_failures_total",
    "Redis rate-limit store failures grouped by enforcement policy.",
    ["policy"],
)
POLICY_DECISIONS = Counter(
    "datagenie_policy_decisions_total",
    "Policy decisions grouped by stable action, outcome, and controlling rule family.",
    ["action", "outcome", "rule_family"],
)
POLICY_DECISION_LATENCY = Histogram(
    "datagenie_policy_decision_duration_seconds",
    "Policy evaluation latency grouped by stable action.",
    ["action"],
)
POLICY_AUDIT_WRITE_FAILURES = Counter(
    "datagenie_policy_audit_write_failures_total",
    "Policy audit persistence failures grouped by stable action.",
    ["action"],
)
POLICY_TENANT_BOUNDARY_VIOLATIONS = Counter(
    "datagenie_policy_tenant_boundary_violations_total",
    "Policy tenant-context mismatches detected before protected evaluation.",
    ["action"],
)


class JsonFormatter(logging.Formatter):
    """Minimal JSON formatter that keeps sensitive headers and bodies out of logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in ("request_id", "method", "path", "route", "status_code", "duration_ms", "actor"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(log_level: str) -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root_logger.handlers = [handler]
