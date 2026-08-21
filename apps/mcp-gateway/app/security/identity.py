from functools import lru_cache
from typing import Any

import jwt
from fastapi import HTTPException, Request, status
from jwt import InvalidTokenError, PyJWKClient

from app.core.config import Settings, get_settings
from app.schemas import Principal


class AuthenticationError(RuntimeError):
    pass


def _bearer_token(value: str | None) -> str:
    if not value or not value.lower().startswith("bearer "):
        raise AuthenticationError("A bearer token is required.")
    token = value[7:].strip()
    if not token:
        raise AuthenticationError("A bearer token is required.")
    return token


def _scopes(payload: dict[str, Any], claim: str) -> frozenset[str]:
    raw = payload.get(claim, payload.get("scp", ""))
    if isinstance(raw, str):
        return frozenset(item for item in raw.split(" ") if item)
    if isinstance(raw, list) and all(isinstance(item, str) for item in raw):
        return frozenset(raw)
    raise AuthenticationError("The token scope claim is invalid.")


@lru_cache
def _jwks_client(url: str) -> PyJWKClient:
    return PyJWKClient(url, cache_keys=True, lifespan=300)


def decode_access_token(token: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    options = {"require": ["sub", settings.auth_tenant_claim, "exp"]}
    try:
        if settings.auth_mode == "hs256":
            return jwt.decode(
                token,
                settings.jwt_secret_value(),
                algorithms=[settings.auth_jwt_algorithm],
                audience=settings.mcp_required_audience,
                options=options,
            )
        signing_key = _jwks_client(str(settings.auth_oidc_jwks_url)).get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            signing_key,
            algorithms=["RS256", "ES256"],
            audience=settings.mcp_required_audience,
            issuer=settings.auth_oidc_issuer,
            options=options,
        )
    except (InvalidTokenError, ValueError) as exc:
        raise AuthenticationError("The MCP bearer token is invalid for this protected resource.") from exc


def validated_principal(
    authorization: str | None,
    host_id: str | None,
    settings: Settings | None = None,
) -> Principal:
    settings = settings or get_settings()
    if not settings.auth_enabled:
        raise AuthenticationError("MCP authentication cannot be disabled.")
    token = _bearer_token(authorization)
    payload = decode_access_token(token, settings)
    tenant = payload.get(settings.auth_tenant_claim)
    subject = payload.get("sub")
    roles_raw = payload.get(settings.auth_oidc_role_claim, [])
    if not isinstance(tenant, str) or not tenant.strip() or not isinstance(subject, str) or not subject.strip():
        raise AuthenticationError("The token does not include a usable subject and tenant claim.")
    if isinstance(roles_raw, str):
        roles = frozenset(item for item in roles_raw.split(" ") if item)
    elif isinstance(roles_raw, list) and all(isinstance(item, str) for item in roles_raw):
        roles = frozenset(roles_raw)
    else:
        raise AuthenticationError("The token role claim is invalid.")
    normalized_host = (host_id or "").strip()
    if not normalized_host or normalized_host not in settings.csv(settings.mcp_allowed_hosts):
        raise AuthenticationError("The MCP client host is not approved for this internal beta.")
    if tenant not in settings.csv(settings.mcp_allowed_tenants):
        raise AuthenticationError("The tenant is not enabled for this internal MCP beta.")
    return Principal(
        subject=subject,
        tenant_id=tenant,
        roles=roles,
        scopes=_scopes(payload, settings.auth_scope_claim),
        host_id=normalized_host,
        issuer=payload.get("iss") if isinstance(payload.get("iss"), str) else None,
    )


def get_principal(request: Request) -> Principal:
    try:
        return validated_principal(request.headers.get("Authorization"), request.headers.get("Mcp-Client-Id"))
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "mcp_unauthorized", "message": str(exc)},
            headers={"WWW-Authenticate": 'Bearer scope="catalog:read quality:read lineage:read"'},
        ) from exc


def require_scope(principal: Principal, *required: str) -> None:
    if not set(required).issubset(principal.scopes):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "mcp_forbidden", "message": "The MCP token does not contain the required scope."},
        )
