from dataclasses import dataclass
from typing import Callable

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings

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
    raw_roles = payload.get(settings.auth_oidc_role_claim if settings.auth_mode == "oidc" else "roles", [])
    if not isinstance(subject, str) or not subject:
        raise _unauthorized("The access token is missing a subject.")
    if not isinstance(raw_roles, list) or not all(isinstance(role, str) for role in raw_roles):
        raise _unauthorized("The access token contains invalid roles.")
    roles = frozenset(raw_roles)
    if not roles or not roles.issubset(VALID_ROLES):
        raise _unauthorized("The access token contains unsupported roles.")
    return Principal(subject=subject, roles=roles)


def get_current_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> Principal:
    if not settings.auth_enabled:
        # Local development only. Staging and production reject this configuration
        # during application startup through Settings validation.
        return Principal(subject="local-development", roles=frozenset({ROLE_PLATFORM_ADMIN}))
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("A bearer token is required.")
    principal = _decode_principal(credentials.credentials, settings)
    request.state.principal = principal
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
