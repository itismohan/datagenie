"""Catalog-backed discovery delegation.

Search remains a separate service boundary for future indexing, but authoritative
results, authorization, governance filters, and transparent ranking are served by
the catalog API. This prevents a second, stale discovery index from becoming an
authorization bypass.
"""

from os import getenv
from typing import Any

import httpx
from fastapi import HTTPException, status


CATALOG_API_URL = getenv("DATAGENIE_CATALOG_API_URL", "http://catalog-api:8000").rstrip("/")
REQUEST_ID_HEADER = "X-Request-ID"


async def search_assets(query_params: dict[str, str], authorization: str | None, request_id: str | None) -> tuple[dict[str, Any], str | None]:
    """Proxy a discovery request to the catalog without weakening catalog RBAC."""
    headers: dict[str, str] = {}
    if authorization:
        headers["Authorization"] = authorization
    if request_id:
        headers[REQUEST_ID_HEADER] = request_id

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            upstream = await client.get(
                f"{CATALOG_API_URL}/api/v1/assets",
                params=query_params,
                headers=headers,
            )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "catalog_unavailable", "message": "Catalog discovery is temporarily unavailable."},
        ) from exc

    if upstream.status_code >= 400:
        try:
            detail = upstream.json()
        except ValueError:
            detail = {"code": "catalog_error", "message": "Catalog discovery request failed."}
        raise HTTPException(status_code=upstream.status_code, detail=detail)

    return upstream.json(), upstream.headers.get(REQUEST_ID_HEADER)
