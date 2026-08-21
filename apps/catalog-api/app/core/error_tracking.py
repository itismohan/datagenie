import sentry_sdk

from app.core.config import Settings


def configure_error_tracking(settings: Settings) -> None:
    """Initialize vendor-neutral Sentry-compatible error tracking without PII collection."""
    if not settings.error_tracking_dsn:
        return
    sentry_sdk.init(
        dsn=settings.error_tracking_dsn,
        environment=settings.environment,
        traces_sample_rate=settings.error_tracking_traces_sample_rate,
        send_default_pii=False,
    )
