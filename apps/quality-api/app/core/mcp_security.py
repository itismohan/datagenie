import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

from fastapi import HTTPException, Request, status

from app.core.config import get_settings


@dataclass(frozen=True)
class McpActor:
    subject: str
    tenant_id: str
    roles: frozenset[str]
    request_id: str


def require_mcp_gateway_actor(request: Request) -> McpActor:
    settings = get_settings()
    if not settings.mcp_gateway_service_identity_enabled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MCP service delegation is disabled.")
    service_id = request.headers.get("X-DataGenie-Service-Id")
    timestamp = request.headers.get("X-DataGenie-Service-Timestamp")
    actor_b64 = request.headers.get("X-DataGenie-Service-Actor")
    signature = request.headers.get("X-DataGenie-Service-Signature")
    if not all([service_id, timestamp, actor_b64, signature]) or not hmac.compare_digest(service_id or "", settings.mcp_gateway_service_id):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Trusted MCP service identity is required.")
    try:
        if abs(int(time.time()) - int(timestamp)) > settings.mcp_gateway_service_max_skew_seconds:
            raise ValueError("expired")
        expected = hmac.new(
            settings.mcp_gateway_service_secret_value().encode(),
            f"{timestamp}\n{request.method}\n{request.url.path}\n{actor_b64}".encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise ValueError("signature")
        context = json.loads(base64.urlsafe_b64decode((actor_b64 + "=" * (-len(actor_b64) % 4)).encode()))
        subject, tenant_id, roles, request_id = context.get("subject"), context.get("tenant_id"), context.get("roles"), context.get("request_id")
        if not isinstance(subject, str) or not isinstance(tenant_id, str) or not isinstance(request_id, str) or not isinstance(roles, list) or not all(isinstance(role, str) for role in roles):
            raise ValueError("claims")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="The MCP service identity packet is invalid or expired.") from exc
    return McpActor(subject=subject, tenant_id=tenant_id, roles=frozenset(roles), request_id=request_id)
