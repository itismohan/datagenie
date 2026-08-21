import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Callable

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings
from app.core.tenant import set_current_tenant_id

bearer_scheme = HTTPBearer(auto_error=False)

ROLE_PLATFORM_ADMIN = "platform_admin"
ROLE_DATA_STEWARD = "data_steward"
ROLE_DATA_OWNER = "data_owner"
ROLE_ANALYST = "analyst"
ROLE_READ_ONLY = "read_only"
VALID_ROLES = {ROLE_PLATFORM_ADMIN, ROLE_DATA_STEWARD, ROLE_DATA_OWNER, ROLE_ANALYST, ROLE_READ_ONLY}


@dataclass(frozen=True)
class Principal:
    subject: str
    tenant_id: str
    roles: frozenset[str]

    def has_any_role(self, *accepted_roles: str) -> bool:
        return ROLE_PLATFORM_ADMIN in self.roles or bool(self.roles.intersection(accepted_roles))


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "unauthorized", "message": message})


def _forbidden(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "forbidden", "message": message})


def _decode_principal(token: str, settings: Settings) -> Principal:
    try:
        if settings.auth_mode == "oidc":
            if not settings.auth_oidc_jwks_url or not settings.auth_oidc_issuer or not settings.auth_oidc_audience:
                raise _unauthorized("OIDC validation is not fully configured.")
            signing_key = jwt.PyJWKClient(settings.auth_oidc_jwks_url).get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "RS384", "RS512"],
                audience=settings.auth_oidc_audience,
                issuer=settings.auth_oidc_issuer,
            )
        else:
            payload = jwt.decode(token, settings.jwt_secret_value(), algorithms=[settings.auth_jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise _unauthorized("The access token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise _unauthorized("The access token is invalid.") from exc
    except Exception as exc:
        raise _unauthorized("The access token could not be validated.") from exc

    subject = payload.get("sub")
    tenant_id = payload.get(settings.auth_tenant_claim)
    raw_roles = payload.get(settings.auth_oidc_role_claim if settings.auth_mode == "oidc" else "roles", [])
    if not isinstance(subject, str) or not subject:
        raise _unauthorized("The access token is missing a subject.")
    if not isinstance(tenant_id, str) or not tenant_id.strip() or len(tenant_id) > 255:
        if settings.environment == "development":
            tenant_id = settings.tenant_default_id
        else:
            raise _unauthorized(f"The access token is missing a valid {settings.auth_tenant_claim} claim.")
    if not isinstance(raw_roles, list) or not all(isinstance(role, str) for role in raw_roles):
        raise _unauthorized("The access token contains invalid roles.")
    roles = frozenset(raw_roles)
    if not roles or not roles.issubset(VALID_ROLES):
        raise _unauthorized("The access token contains unsupported roles.")
    return Principal(subject=subject, tenant_id=tenant_id.strip(), roles=roles)


def get_mcp_delegated_principal(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> Principal:
    """Verify the gateway-signed actor packet used only by dedicated private MCP routes."""
    if not settings.mcp_gateway_service_identity_enabled:
        raise _unauthorized("MCP service delegation is not enabled.")
    service_id = request.headers.get("X-DataGenie-Service-Id")
    timestamp = request.headers.get("X-DataGenie-Service-Timestamp")
    context_b64 = request.headers.get("X-DataGenie-Service-Actor")
    signature = request.headers.get("X-DataGenie-Service-Signature")
    if not all([service_id, timestamp, context_b64, signature]):
        raise _unauthorized("A complete MCP service identity packet is required.")
    if not hmac.compare_digest(service_id, settings.mcp_gateway_service_id):
        raise _unauthorized("The calling service is not trusted.")
    try:
        timestamp_int = int(timestamp)
        if abs(int(time.time()) - timestamp_int) > settings.mcp_gateway_service_max_skew_seconds:
            raise ValueError("expired")
        signing_input = f"{timestamp}\n{request.method}\n{request.url.path}\n{context_b64}".encode()
        expected = hmac.new(settings.mcp_gateway_service_secret_value().encode(), signing_input, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise ValueError("signature")
        padded = context_b64 + "=" * (-len(context_b64) % 4)
        context = json.loads(base64.urlsafe_b64decode(padded.encode()))
        subject = context.get("subject")
        tenant_id = context.get("tenant_id")
        roles = context.get("roles")
        if not isinstance(subject, str) or not subject or not isinstance(tenant_id, str) or not tenant_id:
            raise ValueError("identity")
        if not isinstance(roles, list) or not all(isinstance(role, str) and role in VALID_ROLES for role in roles):
            raise ValueError("roles")
    except Exception as exc:
        raise _unauthorized("The MCP service identity packet is invalid or expired.") from exc
    principal = Principal(subject=subject, tenant_id=tenant_id, roles=frozenset(roles))
    request.state.principal = principal
    set_current_tenant_id(principal.tenant_id)
    session = getattr(request.state, "db", None)
    if session is not None:
        session.info["tenant_id"] = principal.tenant_id
    return principal


def get_current_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> Principal:
    if not settings.auth_enabled:
        # Local development only. Staging and production reject this configuration
        # during application startup through Settings validation.
        principal = Principal(subject="local-development", tenant_id=settings.tenant_default_id, roles=frozenset({ROLE_PLATFORM_ADMIN}))
        request.state.principal = principal
        set_current_tenant_id(principal.tenant_id)
        session = getattr(request.state, "db", None)
        if session is not None:
            session.info["tenant_id"] = principal.tenant_id
        return principal
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("A bearer token is required.")
    principal = _decode_principal(credentials.credentials, settings)
    request.state.principal = principal
    set_current_tenant_id(principal.tenant_id)
    session = getattr(request.state, "db", None)
    if session is not None:
        session.info["tenant_id"] = principal.tenant_id
    return principal


def _record_authorization_denial(request: Request, principal: Principal, accepted_roles: tuple[str, ...]) -> None:
    """Audit a validated-principal denial without allowing audit failures to bypass RBAC."""
    try:
        from app.db.session import SessionLocal
        from app.services.audit_service import record_audit_event

        db = SessionLocal()
        try:
            record_audit_event(
                db,
                principal=principal,
                action="authorization.denied",
                resource_type="api_route",
                resource_id=request.url.path,
                outcome="denied",
                request_id=getattr(request.state, "request_id", "unknown"),
                metadata={"method": request.method, "accepted_roles": sorted(accepted_roles)},
            )
            db.commit()
        finally:
            db.close()
    except Exception:
        # Authorization takes precedence over telemetry. The request must still
        # be denied even when the audit database is temporarily unavailable.
        return


def require_roles(*accepted_roles: str) -> Callable:
    def dependency(request: Request, principal: Principal = Depends(get_current_principal)) -> Principal:
        if not principal.has_any_role(*accepted_roles):
            _record_authorization_denial(request, principal, accepted_roles)
            raise _forbidden("The current role is not authorized for this operation.")
        return principal

    return dependency


def can_curate_asset(principal: Principal, owner: str | None) -> bool:
    if principal.has_any_role(ROLE_DATA_STEWARD):
        return True
    return ROLE_DATA_OWNER in principal.roles and owner == principal.subject
