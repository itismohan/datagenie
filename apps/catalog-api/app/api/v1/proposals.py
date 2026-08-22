from __future__ import annotations

from html import escape
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.core.security import ROLE_ANALYST, ROLE_DATA_OWNER, ROLE_DATA_STEWARD, ROLE_PLATFORM_ADMIN, ROLE_READ_ONLY, Principal, require_roles
from app.db.session import get_db
from app.models.catalog import GovernanceProposalStatus
from app.schemas.proposals import GovernanceProposalCreate, ProposalApproval, ProposalCreated, ProposalExecution, ProposalExecutionRead, ProposalRead, ProposalReview
from app.services.idempotency_service import IdempotencyContext, get_idempotency_context, replay_response, store_response
from app.services.proposal_service import approve_proposal, cancel_proposal, create_proposal, execute_proposal, list_proposals, proposal_or_404, reject_proposal


router = APIRouter(prefix="/governance", tags=["Governance proposals"])
proposal_creator = require_roles(ROLE_PLATFORM_ADMIN, ROLE_DATA_STEWARD, ROLE_DATA_OWNER, ROLE_ANALYST, ROLE_READ_ONLY)
steward = require_roles(ROLE_PLATFORM_ADMIN, ROLE_DATA_STEWARD)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def _inbox_uri(proposal_id: str) -> str:
    return f"/api/v1/governance/inbox?proposal_id={proposal_id}"


def _created(proposal) -> dict:
    return {**ProposalRead.model_validate(proposal).model_dump(mode="json"), "inbox_uri": _inbox_uri(proposal.id)}


@router.post("/proposals", response_model=ProposalCreated, status_code=status.HTTP_201_CREATED)
def create_governance_proposal(
    payload: GovernanceProposalCreate,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(proposal_creator),
    idempotency: IdempotencyContext | None = Depends(get_idempotency_context),
):
    replay = replay_response(db, idempotency)
    if replay is not None:
        return replay
    if payload.source.channel == "mcp":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "mcp_delegation_required", "message": "MCP-originated proposals must be created through the signed internal delegation endpoint."},
        )
    proposal = create_proposal(db, principal, payload, request_id=_request_id(request), host_id=None)
    body = _created(proposal)
    store_response(db, idempotency, body, status.HTTP_201_CREATED)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=body)


@router.get("/proposals", response_model=list[ProposalRead])
def get_governance_proposals(
    status_filter: GovernanceProposalStatus | None = None,
    db: Session = Depends(get_db),
    principal: Principal = Depends(proposal_creator),
):
    return list_proposals(db, principal, status_filter)


@router.get("/proposals/{proposal_id}", response_model=ProposalRead)
def get_governance_proposal(proposal_id: str, db: Session = Depends(get_db), principal: Principal = Depends(proposal_creator)):
    return proposal_or_404(db, principal, proposal_id)


@router.post("/proposals/{proposal_id}/approve", response_model=ProposalApproval)
def approve_governance_proposal(proposal_id: str, payload: ProposalReview, request: Request, db: Session = Depends(get_db), principal: Principal = Depends(steward)):
    proposal, nonce = approve_proposal(db, principal, proposal_id, payload.review_note, request_id=_request_id(request))
    return {**ProposalRead.model_validate(proposal).model_dump(mode="json"), "confirmation_nonce": nonce}


@router.post("/proposals/{proposal_id}/reject", response_model=ProposalRead)
def reject_governance_proposal(proposal_id: str, payload: ProposalReview, request: Request, db: Session = Depends(get_db), principal: Principal = Depends(steward)):
    return reject_proposal(db, principal, proposal_id, payload.review_note, request_id=_request_id(request))


@router.post("/proposals/{proposal_id}/cancel", response_model=ProposalRead)
def cancel_governance_proposal(proposal_id: str, request: Request, db: Session = Depends(get_db), principal: Principal = Depends(proposal_creator)):
    return cancel_proposal(db, principal, proposal_id, request_id=_request_id(request))


@router.post("/proposals/{proposal_id}/execute", response_model=ProposalExecutionRead)
def execute_governance_proposal(proposal_id: str, payload: ProposalExecution, request: Request, db: Session = Depends(get_db), principal: Principal = Depends(steward)):
    proposal, result = execute_proposal(
        db,
        principal,
        proposal_id,
        proposal_hash=payload.proposal_hash,
        confirmation_nonce=payload.confirmation_nonce,
        request_id=_request_id(request),
    )
    return {**ProposalRead.model_validate(proposal).model_dump(mode="json"), "execution_result": result}


@router.get("/inbox", response_class=HTMLResponse)
def governance_inbox(proposal_id: str | None = None, db: Session = Depends(get_db), principal: Principal = Depends(steward)):
    proposals = list_proposals(db, principal)
    focused = next((proposal for proposal in proposals if proposal.id == proposal_id), proposals[0] if proposals else None)
    rows = "".join(
        f'<li><a href="/api/v1/governance/inbox?proposal_id={escape(proposal.id)}">{escape(proposal.title)} — {escape(proposal.status.value)}</a></li>'
        for proposal in proposals
    ) or "<li>No proposals are awaiting review.</li>"
    if focused is None:
        detail = "<p>No proposal selected.</p>"
    else:
        detail = (
            f"<h2>{escape(focused.title)}</h2>"
            f"<p><strong>Status:</strong> {escape(focused.status.value)} &nbsp; <strong>Expires:</strong> {escape(focused.expires_at.isoformat())}</p>"
            f"<p>{escape(focused.proposal_text)}</p>"
            f"<h3>Structured diff</h3><pre>{escape(str(focused.change_diff))}</pre>"
            f"<h3>Evidence</h3><pre>{escape(str(focused.source_evidence))}</pre>"
            f"<h3>Impact and preconditions</h3><pre>{escape(str({'impact': focused.impact, 'versions': focused.version_preconditions}))}</pre>"
            f"<h3>Initiator and policy</h3><pre>{escape(str({'subject': focused.initiating_subject, 'agent': focused.initiating_agent_id, 'model': focused.initiating_model_id, 'host': focused.initiating_host_id, 'policy': focused.policy_snapshot}))}</pre>"
            f"<p><strong>Approve:</strong> POST <code>/api/v1/governance/proposals/{escape(focused.id)}/approve</code> with a review note. "
            f"<strong>Reject:</strong> POST <code>/api/v1/governance/proposals/{escape(focused.id)}/reject</code> with a review note.</p>"
        )
    return HTMLResponse(f"<!doctype html><html><head><title>DataGenie Approval Inbox</title></head><body><h1>DataGenie Approval Inbox</h1><aside><h2>Tenant proposals</h2><ul>{rows}</ul></aside><main>{detail}</main></body></html>")
