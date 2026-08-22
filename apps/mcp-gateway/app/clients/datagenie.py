import base64
import hashlib
import hmac
import json
import time
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.schemas import PolicyPacket, Principal


class DownstreamUnavailable(RuntimeError):
    pass


class DownstreamForbidden(RuntimeError):
    pass


class DataGenieClient:
    """Private service-to-service client. Host bearer tokens are never forwarded."""

    def __init__(self, settings: Settings | None = None, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings if settings is not None else get_settings()
        self.client = client or httpx.AsyncClient(timeout=self.settings.mcp_tool_timeout_seconds)
        self._owns_client = client is None

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    def _headers(self, principal: Principal, request_id: str, method: str, path: str) -> dict[str, str]:
        actor = {
            "subject": principal.subject,
            "tenant_id": principal.tenant_id,
            "roles": sorted(principal.roles),
            "scopes": sorted(principal.scopes),
            "host_id": principal.host_id,
            "request_id": request_id,
        }
        actor_b64 = base64.urlsafe_b64encode(json.dumps(actor, separators=(",", ":"), sort_keys=True).encode()).decode().rstrip("=")
        timestamp = str(int(time.time()))
        signing_input = f"{timestamp}\n{method}\n{path}\n{actor_b64}".encode()
        signature = hmac.new(self.settings.downstream_secret_value().encode(), signing_input, hashlib.sha256).hexdigest()
        return {
            "X-DataGenie-Service-Id": self.settings.downstream_service_id,
            "X-DataGenie-Service-Timestamp": timestamp,
            "X-DataGenie-Service-Actor": actor_b64,
            "X-DataGenie-Service-Signature": signature,
            self.settings.request_id_header: request_id,
        }

    async def _request(
        self,
        base_url: str,
        method: str,
        path: str,
        principal: Principal,
        request_id: str,
        *,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = await self.client.request(
                method,
                f"{base_url.rstrip('/')}{path}",
                params=params,
                json=payload,
                headers=self._headers(principal, request_id, method, path),
            )
        except httpx.HTTPError as exc:
            raise DownstreamUnavailable("A required DataGenie service is unavailable.") from exc
        if response.status_code in {401, 403, 404}:
            raise DownstreamForbidden("The downstream service did not permit or expose the requested governed resource.")
        if response.status_code >= 500:
            raise DownstreamUnavailable("A required DataGenie service is unavailable.")
        if response.status_code >= 400:
            raise DownstreamUnavailable("The downstream service rejected the bounded MCP request.")
        try:
            return response.json()
        except ValueError as exc:
            raise DownstreamUnavailable("The downstream service returned an invalid response.") from exc

    async def evaluate_policy(self, principal: Principal, request_id: str, asset_id: str, purpose: str) -> PolicyPacket:
        payload = {
            "action": "asset.read",
            "resource": {"resource_type": "asset", "resource_id": asset_id},
            "purpose": purpose,
            "context": {"workflow_id": "mcp-gateway"},
        }
        response = await self._request(
            self.settings.downstream_catalog_url,
            "POST",
            "/api/v1/policy/internal/mcp/decisions",
            principal,
            request_id,
            payload=payload,
        )
        return PolicyPacket.model_validate(response)

    async def create_governance_proposal(self, principal: Principal, request_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Create intent only through the private signed catalog proposal endpoint."""
        return await self._request(
            self.settings.downstream_catalog_url,
            "POST",
            "/api/v1/internal/mcp/proposals",
            principal,
            request_id,
            payload=payload,
        )

    async def search_assets(self, principal: Principal, request_id: str, params: dict[str, Any]) -> dict[str, Any]:
        return await self._request(
            self.settings.downstream_catalog_url,
            "GET",
            "/api/v1/internal/mcp/assets",
            principal,
            request_id,
            params=params,
        )

    async def asset_context(self, principal: Principal, request_id: str, asset_id: str, purpose: str) -> dict[str, Any]:
        return await self._request(
            self.settings.downstream_catalog_url,
            "GET",
            f"/api/v1/internal/mcp/assets/{asset_id}",
            principal,
            request_id,
            params={"purpose": purpose},
        )

    async def domain(self, principal: Principal, request_id: str, domain_id: str) -> dict[str, Any]:
        return await self._request(
            self.settings.downstream_catalog_url,
            "GET",
            f"/api/v1/internal/mcp/domains/{domain_id}",
            principal,
            request_id,
        )

    async def quality_evidence(self, principal: Principal, request_id: str, asset_id: str, purpose: str, history_limit: int) -> dict[str, Any]:
        # The shared policy call precedes this service request. The quality API
        # independently verifies the signed tenant-bound actor packet.
        return await self._request(
            self.settings.downstream_quality_url,
            "GET",
            f"/api/v1/quality/internal/mcp/assets/{asset_id}/evidence",
            principal,
            request_id,
            params={"history_limit": history_limit},
        )

    async def lineage_impact(
        self,
        principal: Principal,
        request_id: str,
        asset_id: str,
        direction: str,
        depth: int,
        purpose: str,
    ) -> dict[str, Any]:
        # Prove the focal asset is tenant-visible before issuing a bounded graph request.
        await self.asset_context(principal, request_id, asset_id, purpose)
        return await self._request(
            self.settings.downstream_lineage_url,
            "GET",
            f"/api/v1/lineage/internal/mcp/{asset_id}",
            principal,
            request_id,
            params={"direction": direction, "max_depth": depth},
        )
