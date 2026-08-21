import asyncio

import httpx
import pytest
from fastapi import HTTPException

from app.services import search_service


class FakeAsyncClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def get(self, url, params, headers):
        self.calls.append({"url": url, "params": params, "headers": headers})
        return self.response


def test_catalog_delegation_forwards_governance_filters_auth_and_request_id(monkeypatch):
    request = httpx.Request("GET", "http://catalog-api:8000/api/v1/assets")
    response = httpx.Response(
        200,
        json={"items": [{"id": "asset-1", "name": "payments", "discovery_score": 92}], "total": 1},
        headers={"X-Request-ID": "catalog-request-1"},
        request=request,
    )
    client = FakeAsyncClient(response)
    monkeypatch.setattr(search_service.httpx, "AsyncClient", lambda **_kwargs: client)

    payload, request_id = asyncio.run(
        search_service.search_assets(
            {"q": "payments", "domain": "Finance", "quality_min": "85", "explainable_quality_only": "true"},
            "Bearer delegated-token",
            "search-request-1",
        )
    )

    assert payload["total"] == 1
    assert request_id == "catalog-request-1"
    assert client.calls == [
        {
            "url": "http://catalog-api:8000/api/v1/assets",
            "params": {"q": "payments", "domain": "Finance", "quality_min": "85", "explainable_quality_only": "true"},
            "headers": {"Authorization": "Bearer delegated-token", "X-Request-ID": "search-request-1"},
        }
    ]


def test_catalog_failures_are_not_masked_as_stubbed_search_results(monkeypatch):
    request = httpx.Request("GET", "http://catalog-api:8000/api/v1/assets")
    client = FakeAsyncClient(
        httpx.Response(
            403,
            json={"error": {"code": "forbidden", "message": "Insufficient role."}},
            request=request,
        )
    )
    monkeypatch.setattr(search_service.httpx, "AsyncClient", lambda **_kwargs: client)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(search_service.search_assets({"q": "payments"}, "Bearer read-only-token", None))

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["error"]["code"] == "forbidden"
