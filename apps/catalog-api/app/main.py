
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4
import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text

from app.api.v1 import assets, audit, governance, glossary, ingestion_jobs, sources
from app.core.config import get_settings
from app.core.observability import REQUEST_COUNT, REQUEST_LATENCY, UNHANDLED_ERRORS, configure_logging
from app.db.session import create_schema, engine

settings = get_settings()
logger = logging.getLogger("datagenie.catalog")


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging(settings.log_level)
    if settings.environment == "development":
        create_schema()
    yield


app = FastAPI(title=settings.app_name, version="0.3.0", lifespan=lifespan)
app.include_router(assets.router, prefix=f"{settings.api_v1_prefix}/assets", tags=["Assets"])
app.include_router(sources.router, prefix=f"{settings.api_v1_prefix}/sources", tags=["Sources"])
app.include_router(ingestion_jobs.router, prefix=f"{settings.api_v1_prefix}/ingestion-jobs", tags=["Ingestion jobs"])
app.include_router(glossary.router, prefix=f"{settings.api_v1_prefix}/glossary", tags=["Glossary"])
app.include_router(governance.router, prefix=f"{settings.api_v1_prefix}/governance", tags=["Governance"])
app.include_router(audit.router, prefix=f"{settings.api_v1_prefix}/audit-events", tags=["Audit events"])


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get(settings.request_id_header) or str(uuid4())
    request.state.request_id = request_id
    started = perf_counter()
    response: Response | None = None
    try:
        response = await call_next(request)
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


@app.get("/health", tags=["Operations"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/live", tags=["Operations"])
def liveness() -> dict[str, str]:
    return {"status": "live"}


@app.get("/health/ready", tags=["Operations"])
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
