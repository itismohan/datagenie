import importlib
import sys
from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient


def build_client(monkeypatch, tmp_path) -> tuple[TestClient, str]:
    secret = "test-jwt-secret-that-is-longer-than-thirty-two-characters"
    monkeypatch.setenv("DATAGENIE_ENVIRONMENT", "development")
    monkeypatch.setenv("DATAGENIE_DATABASE_URL", f"sqlite:///{tmp_path / 'catalog.db'}")
    monkeypatch.setenv("DATAGENIE_AUTH_ENABLED", "true")
    monkeypatch.setenv("DATAGENIE_AUTH_JWT_SECRET", secret)

    from app.core.config import get_settings

    get_settings.cache_clear()
    for module_name in ["app.db.session", "app.api.v1.assets", "app.api.v1.sources", "app.api.v1.glossary", "app.api.v1.ingestion_jobs", "app.main"]:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
    import app.main as main_module

    return TestClient(main_module.app), secret


def token(secret: str, subject: str, roles: list[str]) -> str:
    return jwt.encode(
        {"sub": subject, "roles": roles, "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        secret,
        algorithm="HS256",
    )


def test_auth_errors_include_request_id_and_roles_are_enforced(monkeypatch, tmp_path) -> None:
    client, secret = build_client(monkeypatch, tmp_path)
    with client:
        unauthenticated = client.get("/api/v1/assets/", headers={"X-Request-ID": "request-123"})
        assert unauthenticated.status_code == 401
        assert unauthenticated.headers["X-Request-ID"] == "request-123"
        assert unauthenticated.json()["error"] == {
            "code": "unauthorized",
            "message": "A bearer token is required.",
            "request_id": "request-123",
        }

        analyst_headers = {"Authorization": f"Bearer {token(secret, 'analyst@example.com', ['analyst'])}"}
        forbidden = client.get("/api/v1/sources/", headers=analyst_headers)
        assert forbidden.status_code == 403
        assert forbidden.json()["error"]["code"] == "forbidden"


def test_source_creation_is_idempotent_for_an_authenticated_steward(monkeypatch, tmp_path) -> None:
    client, secret = build_client(monkeypatch, tmp_path)
    payload = {
        "name": "finance-warehouse",
        "source_type": "postgresql",
        "host": "warehouse.internal",
        "database_name": "finance",
        "username": "catalog_reader",
        "secret_ref": "env://DATAGENIE_FINANCE_PASSWORD",
    }
    headers = {
        "Authorization": f"Bearer {token(secret, 'steward@example.com', ['data_steward'])}",
        "Idempotency-Key": "source-create-finance-001",
    }
    with client:
        first = client.post("/api/v1/sources/", json=payload, headers=headers)
        second = client.post("/api/v1/sources/", json=payload, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert second.headers["Idempotent-Replayed"] == "true"
    assert "secret_ref" not in first.json()
