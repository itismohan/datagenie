import importlib
import sys
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient


def build_rate_limited_client(monkeypatch, tmp_path) -> tuple[TestClient, str, object]:
    secret = "test-jwt-secret-that-is-longer-than-thirty-two-characters"
    monkeypatch.setenv("DATAGENIE_ENVIRONMENT", "development")
    monkeypatch.setenv("DATAGENIE_DATABASE_URL", f"sqlite:///{tmp_path / 'catalog.db'}")
    monkeypatch.setenv("DATAGENIE_AUTH_ENABLED", "true")
    monkeypatch.setenv("DATAGENIE_AUTH_JWT_SECRET", secret)
    monkeypatch.setenv("DATAGENIE_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("DATAGENIE_RATE_LIMIT_REDIS_URL", "redis://test-rate-limit")
    monkeypatch.setenv("DATAGENIE_RATE_LIMIT_REQUESTS", "2")

    from app.core.config import get_settings

    get_settings.cache_clear()
    for module_name in [
        "app.db.session",
        "app.api.v1.assets",
        "app.api.v1.sources",
        "app.api.v1.glossary",
        "app.api.v1.ingestion_jobs",
        "app.api.v1.governance",
        "app.main",
    ]:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
    import app.main as main_module

    return TestClient(main_module.app), secret, main_module


def token(secret: str) -> str:
    return jwt.encode(
        {"sub": "analyst@example.com", "roles": ["analyst"], "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        secret,
        algorithm="HS256",
    )


class FakeStore:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def check(self, key, limit, window_seconds):
        self.calls.append((key, limit, window_seconds))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def test_rate_limit_returns_headers_then_a_correlated_429(monkeypatch, tmp_path):
    from app.core.rate_limit import RateLimitResult

    client, secret, main_module = build_rate_limited_client(monkeypatch, tmp_path)
    store = FakeStore(
        [
            RateLimitResult(allowed=True, limit=2, remaining=1, retry_after_seconds=60),
            RateLimitResult(allowed=False, limit=2, remaining=0, retry_after_seconds=41),
        ]
    )
    monkeypatch.setattr(main_module, "get_rate_limit_store", lambda _url: store)
    headers = {"Authorization": f"Bearer {token(secret)}", "X-Request-ID": "rate-limit-test"}

    with client:
        allowed = client.get("/api/v1/assets/", headers=headers)
        blocked = client.get("/api/v1/assets/", headers=headers)

    assert allowed.status_code == 200
    assert allowed.headers["RateLimit-Limit"] == "2"
    assert allowed.headers["RateLimit-Remaining"] == "1"
    assert blocked.status_code == 429
    assert blocked.headers["RateLimit-Remaining"] == "0"
    assert blocked.headers["Retry-After"] == "41"
    assert blocked.headers["X-Request-ID"] == "rate-limit-test"
    assert blocked.json()["error"] == {
        "code": "rate_limit_exceeded",
        "message": "Too many requests. Retry after the supplied interval.",
        "request_id": "rate-limit-test",
    }
    assert len(store.calls) == 2


def test_rate_limit_fails_closed_when_redis_is_unavailable(monkeypatch, tmp_path):
    from app.core.rate_limit import RateLimitStoreUnavailable

    client, secret, main_module = build_rate_limited_client(monkeypatch, tmp_path)
    monkeypatch.setattr(main_module, "get_rate_limit_store", lambda _url: FakeStore([RateLimitStoreUnavailable()]))

    with client:
        response = client.get("/api/v1/assets/", headers={"Authorization": f"Bearer {token(secret)}"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "rate_limit_unavailable"


def test_health_probes_are_not_rate_limited(monkeypatch, tmp_path):
    client, _secret, main_module = build_rate_limited_client(monkeypatch, tmp_path)
    store = FakeStore([])
    monkeypatch.setattr(main_module, "get_rate_limit_store", lambda _url: store)

    with client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert store.calls == []


def test_staging_requires_a_fail_closed_distributed_rate_limit_store():
    from app.core.config import Settings
    from pydantic import ValidationError

    common = {
        "environment": "staging",
        "database_url": "postgresql+psycopg://catalog:password@db.example/datagenie",
        "auth_enabled": True,
        "auth_jwt_secret": "test-jwt-secret-that-is-longer-than-thirty-two-characters",
        "connector_redis_url": "redis://redis.example:6379/2",
        "error_tracking_dsn": "https://public@example.invalid/1",
        "webhook_allowed_hosts": "hooks.example.invalid",
    }
    with pytest.raises(ValidationError, match="RATE_LIMIT_ENABLED"):
        Settings(**common)
    with pytest.raises(ValidationError, match="FAIL_OPEN"):
        Settings(
            **common,
            rate_limit_enabled=True,
            rate_limit_redis_url="redis://redis.example:6379/1",
            rate_limit_fail_open=True,
        )

    settings = Settings(
        **common,
        rate_limit_enabled=True,
        rate_limit_redis_url="redis://redis.example:6379/1",
        rate_limit_fail_open=False,
    )
    assert settings.rate_limit_enabled is True
