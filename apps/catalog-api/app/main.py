
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4
import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text

from app.api.v1 import assets, audit, governance, glossary, ingestion_jobs, operations, policy, search_index, sources
from app.core.config import get_settings
from app.core.error_tracking import configure_error_tracking
from app.core.openapi import OPENAPI_TAGS, build_openapi
from app.core.observability import (
    RATE_LIMIT_REJECTIONS,
    RATE_LIMIT_STORE_FAILURES,
    REQUEST_COUNT,
    REQUEST_LATENCY,
    UNHANDLED_ERRORS,
    configure_logging,
)
from app.core.rate_limit import RateLimitStoreUnavailable, get_rate_limit_store, rate_limit_key
from app.db.session import create_schema, engine

settings = get_settings()
logger = logging.getLogger("datagenie.catalog")


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging(settings.log_level)
    configure_error_tracking(settings)
    if settings.environment == "development":
        create_schema()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    summary="Tenant-isolated metadata governance and discovery platform",
    description="Interactive documentation and the versioned OpenAPI contract are available under `/api`.",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_tags=OPENAPI_TAGS,
    lifespan=lifespan,
)
app.openapi = lambda: build_openapi(app)
app.include_router(assets.router, prefix=f"{settings.api_v1_prefix}/assets", tags=["Assets"])
app.include_router(sources.router, prefix=f"{settings.api_v1_prefix}/sources", tags=["Sources"])
app.include_router(ingestion_jobs.router, prefix=f"{settings.api_v1_prefix}/ingestion-jobs", tags=["Ingestion jobs"])
app.include_router(glossary.router, prefix=f"{settings.api_v1_prefix}/glossary", tags=["Glossary"])
app.include_router(governance.router, prefix=f"{settings.api_v1_prefix}/governance", tags=["Governance"])
app.include_router(search_index.router, prefix=f"{settings.api_v1_prefix}/search-index", tags=["Search index"])
app.include_router(operations.router, prefix=f"{settings.api_v1_prefix}/operations", tags=["Operations"])
app.include_router(audit.router, prefix=f"{settings.api_v1_prefix}/audit-events", tags=["Audit events"])
app.include_router(policy.router, prefix=f"{settings.api_v1_prefix}/policy", tags=["Policy decisions"])


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get(settings.request_id_header) or str(uuid4())
    request.state.request_id = request_id
    started = perf_counter()
    response: Response | None = None
    rate_limit_headers: dict[str, str] = {}
    try:
        exempt_path = request.url.path in {"/health", "/health/live", "/health/ready", "/metrics"}
        if settings.rate_limit_enabled and not exempt_path:
            try:
                result = get_rate_limit_store(settings.rate_limit_redis_url or "").check(
                    rate_limit_key(request, settings.rate_limit_window_seconds),
                    settings.rate_limit_requests,
                    settings.rate_limit_window_seconds,
                )
                rate_limit_headers = {
                    "RateLimit-Limit": str(result.limit),
                    "RateLimit-Remaining": str(result.remaining),
                }
                if not result.allowed:
                    RATE_LIMIT_REJECTIONS.labels(method=request.method).inc()
                    response = JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content=error_body(request, "rate_limit_exceeded", "Too many requests. Retry after the supplied interval."),
                        headers={**rate_limit_headers, "Retry-After": str(result.retry_after_seconds)},
                    )
                    return response
            except RateLimitStoreUnavailable:
                policy = "open" if settings.rate_limit_fail_open else "closed"
                RATE_LIMIT_STORE_FAILURES.labels(policy=policy).inc()
                if not settings.rate_limit_fail_open:
                    response = JSONResponse(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        content=error_body(request, "rate_limit_unavailable", "Request protection is temporarily unavailable."),
                    )
                    return response
                logger.warning("rate_limit_store_unavailable", extra={"request_id": request_id, "path": request.url.path})

        response = await call_next(request)
        response.headers.update(rate_limit_headers)
        return response
    finally:
        elapsed = perf_counter() - started
        route = getattr(request.scope.get("route"), "path", request.url.path)
        status_code = response.status_code if response is not None else 500
        REQUEST_COUNT.labels(route=route, method=request.method, status=str(status_code)).inc()
        REQUEST_LATENCY.labels(route=route, method=request.method).observe(elapsed)
        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "route": route,
                "status_code": status_code,
                "duration_ms": round(elapsed * 1000, 2),
                "actor": getattr(getattr(request.state, "principal", None), "subject", None),
            },
        )
        if response is not None:
            response.headers[settings.request_id_header] = request_id


def error_body(request: Request, code: str, message: str, details: object | None = None) -> dict:
    payload: dict = {
        "error": {
            "code": code,
            "message": message,
            "request_id": getattr(request.state, "request_id", "unknown"),
        }
    }
    if details is not None:
        payload["error"]["details"] = details
    return payload


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        code = str(exc.detail.get("code", "http_error"))
        message = str(exc.detail.get("message", "Request failed."))
        details = exc.detail.get("details")
    else:
        code = "http_error"
        message = str(exc.detail)
        details = None
    return JSONResponse(status_code=exc.status_code, content=error_body(request, code, message, details), headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_body(request, "validation_error", "The request did not pass validation.", exc.errors()),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    UNHANDLED_ERRORS.labels(exception_type=type(exc).__name__).inc()
    logger.exception(
        "unhandled_exception",
        extra={"request_id": getattr(request.state, "request_id", "unknown"), "path": request.url.path},
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_body(request, "internal_error", "An unexpected server error occurred."),
    )


@app.get("/health", tags=["Platform health"], summary="Compatibility health probe")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/live", tags=["Platform health"], summary="Process liveness probe")
def liveness() -> dict[str, str]:
    return {"status": "live"}


@app.get("/health/ready", tags=["Platform health"], summary="Database readiness probe")
def readiness() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "not_ready", "message": "The catalog database is unavailable."},
        ) from exc
    return {"status": "ready"}


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
