from contextvars import ContextVar, Token

from app.schemas import Principal

_current_principal: ContextVar[Principal | None] = ContextVar("mcp_current_principal", default=None)


def bind_principal(principal: Principal) -> Token[Principal | None]:
    return _current_principal.set(principal)


def reset_principal(token: Token[Principal | None]) -> None:
    _current_principal.reset(token)


def current_principal() -> Principal:
    principal = _current_principal.get()
    if principal is None:
        raise RuntimeError("MCP tenant context is not bound.")
    return principal


def current_tenant_id() -> str:
    return current_principal().tenant_id
