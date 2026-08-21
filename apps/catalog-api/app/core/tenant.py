"""Tenant execution context for request, worker, and ORM isolation.

The context is deliberately explicit: production requests receive it from a
validated token claim, while workers receive it from the durable job record.
Local development uses the configured bootstrap tenant only.
"""

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Generator


_current_tenant_id: ContextVar[str | None] = ContextVar("datagenie_current_tenant_id", default=None)


def set_current_tenant_id(tenant_id: str) -> Token[str | None]:
    return _current_tenant_id.set(tenant_id)


def reset_current_tenant_id(token: Token[str | None]) -> None:
    _current_tenant_id.reset(token)


def get_current_tenant_id(default_tenant_id: str = "default") -> str:
    return _current_tenant_id.get() or default_tenant_id


@contextmanager
def tenant_context(tenant_id: str) -> Generator[None, None, None]:
    token = set_current_tenant_id(tenant_id)
    try:
        yield
    finally:
        reset_current_tenant_id(token)
