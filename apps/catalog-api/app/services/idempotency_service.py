import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import Principal, get_current_principal
from app.db.session import get_db
from app.models.catalog import IdempotencyRecord


@dataclass(frozen=True)
class IdempotencyContext:
    key: str
    principal_subject: str
    method: str
    path: str
    request_hash: str


async def get_idempotency_context(
    request: Request,
    principal: Principal = Depends(get_current_principal),
) -> IdempotencyContext | None:
    key = request.headers.get("Idempotency-Key")
    if key is None:
        return None
    key = key.strip()
    if not key or len(key) > 255:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_idempotency_key", "message": "Idempotency-Key must contain 1 to 255 characters."},
        )
    body = await request.body()
    request_hash = hashlib.sha256(body).hexdigest()
    return IdempotencyContext(
        key=key,
        principal_subject=principal.subject,
        method=request.method,
        path=request.url.path,
        request_hash=request_hash,
    )


def replay_response(db: Session, context: IdempotencyContext | None) -> Response | None:
    if context is None:
        return None
    record = db.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.principal_subject == context.principal_subject,
            IdempotencyRecord.idempotency_key == context.key,
            IdempotencyRecord.method == context.method,
            IdempotencyRecord.path == context.path,
        )
    )
    if not record:
        return None
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        db.delete(record)
        db.commit()
        return None
    if record.request_hash != context.request_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "idempotency_conflict", "message": "This Idempotency-Key has already been used with a different request body."},
        )
    return JSONResponse(status_code=record.status_code, content=record.response_body, headers={"Idempotent-Replayed": "true"})


def store_response(
    db: Session,
    context: IdempotencyContext | None,
    response_body: dict,
    status_code: int,
    settings: Settings | None = None,
) -> None:
    if context is None:
        # Mutation endpoints record their audit event before this call. Commit it
        # even when the client did not request an idempotent replay record.
        db.commit()
        return
    settings = settings or get_settings()
    db.execute(
        delete(IdempotencyRecord).where(IdempotencyRecord.expires_at < datetime.now(timezone.utc))
    )
    db.add(
        IdempotencyRecord(
            principal_subject=context.principal_subject,
            idempotency_key=context.key,
            method=context.method,
            path=context.path,
            request_hash=context.request_hash,
            status_code=status_code,
            response_body=response_body,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=settings.idempotency_ttl_seconds),
        )
    )
    db.commit()
