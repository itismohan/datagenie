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
