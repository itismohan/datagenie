from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import ROLE_DATA_STEWARD, ROLE_PLATFORM_ADMIN, Principal
from app.models.catalog import (
    Asset,
    AssetMetadataVersion,
    CertificationRequest,
    ChangeSource,
    GovernanceProposal,
    GovernanceProposalStatus,
    GovernanceProposalType,
    QualityCheckScheduleRequest,
)
from app.schemas.proposals import GovernanceProposalCreate
from app.services.audit_service import record_audit_event
from app.services.policy_service import PolicyDecision, PolicyOutcome, evaluate_rest_policy


class ProposalWorkflowError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(status_code=status_code, detail={"code": code, "message": message})


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_hash(payload: dict[str, Any]) -> str:
    return _hash(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True))


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _policy_snapshot(decision: PolicyDecision) -> dict[str, Any]:
    return {
        "outcome": decision.outcome.value,
        "decision_version": "1.0.0",
        "rule_ids": list(decision.rule_ids),
        "evidence": [item.model_dump() for item in decision.evidence],
        "obligations": list(decision.obligations),
        "evaluated_at": decision.evaluated_at.isoformat(),
        "expires_at": decision.expires_at.isoformat(),
        "request_id": decision.request_id,
    }


def _proposal_metadata(proposal: GovernanceProposal) -> dict[str, Any]:
    return {
        "proposal_type": proposal.proposal_type.value,
        "proposal_hash": proposal.proposal_hash,
        "status": proposal.status.value,
        "source_channel": proposal.source_channel,
        "initiating_host_id": proposal.initiating_host_id,
        "initiating_model_id": proposal.initiating_model_id,
        "policy_outcome": proposal.policy_snapshot.get("outcome"),
        "policy_rule_ids": proposal.policy_snapshot.get("rule_ids", []),
        "precondition_keys": sorted(proposal.version_preconditions),
    }


def _record_transition(
    db: Session,
    principal: Principal,
    proposal: GovernanceProposal,
    *,
    action: str,
    outcome: str,
    request_id: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    event = record_audit_event(
        db,
        principal=principal,
        action=action,
        resource_type="governance_proposal",
        resource_id=proposal.id,
        outcome=outcome,
        request_id=request_id,
        metadata={**_proposal_metadata(proposal), **(metadata or {})},
    )
    db.flush()
    proposal.audit_event_id = event.id


def _asset_or_error(db: Session, asset_id: str) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise ProposalWorkflowError(status.HTTP_404_NOT_FOUND, "proposal_resource_not_found", "The governed asset was not found.")
    return asset


def _check_type_and_diff(payload: GovernanceProposalCreate, asset: Asset) -> None:
    diff = payload.diff
    if payload.proposal_type == GovernanceProposalType.ASSET_CURATION:
        allowed = {"description", "tags", "owner", "domain_id"}
        if not diff or not set(diff).issubset(allowed):
            raise ProposalWorkflowError(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_proposal_diff", "Asset curation allows only description, tags, owner, and domain_id.")
        if "description" in diff and (not isinstance(diff["description"], str) or len(diff["description"]) > 10_000):
            raise ProposalWorkflowError(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_proposal_diff", "Description must be a bounded string.")
        if "tags" in diff and (not isinstance(diff["tags"], list) or not all(isinstance(tag, str) and 1 <= len(tag) <= 100 for tag in diff["tags"])):
            raise ProposalWorkflowError(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_proposal_diff", "Tags must be a bounded string list.")
    elif payload.proposal_type == GovernanceProposalType.CERTIFICATION_REVIEW_REQUEST:
        if not set(diff).issubset({"note"}) or ("note" in diff and (not isinstance(diff["note"], str) or len(diff["note"]) > 5_000)):
            raise ProposalWorkflowError(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_proposal_diff", "Certification requests allow an optional bounded note only.")
    elif payload.proposal_type == GovernanceProposalType.QUALITY_CHECK_SCHEDULE:
        schedule = diff.get("schedule")
        if set(diff) != {"schedule"} or not isinstance(schedule, dict) or set(schedule) - {"frequency", "rule_types"}:
            raise ProposalWorkflowError(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_proposal_diff", "Quality schedule requires a bounded schedule object.")
        if schedule.get("frequency") not in {"daily", "weekly", "manual"}:
            raise ProposalWorkflowError(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_proposal_diff", "Quality schedule frequency must be daily, weekly, or manual.")
        if "rule_types" in schedule and (not isinstance(schedule["rule_types"], list) or not all(isinstance(item, str) and item for item in schedule["rule_types"])):
            raise ProposalWorkflowError(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_proposal_diff", "Quality rule types must be a string list.")
    else:
        raise ProposalWorkflowError(status.HTTP_422_UNPROCESSABLE_ENTITY, "unsupported_proposal_type", "The proposal type is not supported.")

    expected = payload.version_preconditions.get("technical_version")
    if not isinstance(expected, int) or expected < 1:
        raise ProposalWorkflowError(status.HTTP_422_UNPROCESSABLE_ENTITY, "missing_version_precondition", "A positive asset technical_version precondition is required.")
    if expected != asset.technical_version:
        raise ProposalWorkflowError(status.HTTP_409_CONFLICT, "proposal_precondition_failed", "The asset version has changed; refresh before proposing.")


def _assert_tenant(principal: Principal, proposal: GovernanceProposal) -> None:
    if proposal.tenant_id != principal.tenant_id:
        raise ProposalWorkflowError(status.HTTP_404_NOT_FOUND, "proposal_not_found", "The proposal was not found.")


def _expire_if_due(proposal: GovernanceProposal) -> bool:
    if proposal.status in {GovernanceProposalStatus.PENDING_REVIEW, GovernanceProposalStatus.APPROVED} and _as_utc(proposal.expires_at) <= utc_now():
        proposal.status = GovernanceProposalStatus.EXPIRED
        proposal.confirmation_nonce_digest = None
        proposal.confirmation_expires_at = None
        return True
    return False


def _require_steward(principal: Principal) -> None:
    if not principal.has_any_role(ROLE_DATA_STEWARD, ROLE_PLATFORM_ADMIN):
        raise ProposalWorkflowError(status.HTTP_403_FORBIDDEN, "proposal_steward_required", "A current data steward or platform administrator is required.")


def _allow_proposal_decision(decision: PolicyDecision, code: str) -> None:
    if decision.outcome in {PolicyOutcome.ALLOW, PolicyOutcome.ALLOW_WITH_OBLIGATIONS, PolicyOutcome.REQUIRES_HUMAN_APPROVAL}:
        return
    raise ProposalWorkflowError(status.HTTP_403_FORBIDDEN, code, "The current policy decision does not permit this proposal workflow action.")


def proposal_or_404(db: Session, principal: Principal, proposal_id: str, *, lock: bool = False) -> GovernanceProposal:
    statement = select(GovernanceProposal).where(GovernanceProposal.id == proposal_id)
    if lock:
        statement = statement.with_for_update()
    proposal = db.scalar(statement)
    if proposal is None:
        raise ProposalWorkflowError(status.HTTP_404_NOT_FOUND, "proposal_not_found", "The proposal was not found.")
    _assert_tenant(principal, proposal)
    return proposal


def create_proposal(
    db: Session,
    principal: Principal,
    payload: GovernanceProposalCreate,
    *,
    request_id: str,
    host_id: str | None = None,
) -> GovernanceProposal:
    asset = _asset_or_error(db, payload.resource.resource_id)
    _check_type_and_diff(payload, asset)
    decision = evaluate_rest_policy(
        db,
        principal=principal,
        action="governance.proposal.create",
        resource_type="asset",
        resource_id=asset.id,
        purpose=payload.purpose,
        request_id=request_id,
    )
    _allow_proposal_decision(decision, "proposal_creation_denied")
    immutable = {
        "proposal_type": payload.proposal_type.value,
        "resource": payload.resource.model_dump(),
        "title": payload.title,
        "proposal_text": payload.proposal_text,
        "diff": payload.diff,
        "evidence": payload.evidence,
        "impact": payload.impact,
        "version_preconditions": payload.version_preconditions,
        "initiating_subject": principal.subject,
        "source_channel": payload.source.channel,
        "initiating_agent_id": payload.source.agent_id,
        "initiating_model_id": payload.source.model_id,
        "initiating_host_id": host_id,
    }
    proposal = GovernanceProposal(
        proposal_type=payload.proposal_type,
        resource_type=payload.resource.resource_type,
        resource_id=asset.id,
        title=payload.title,
        proposal_text=payload.proposal_text,
        change_diff=payload.diff,
        source_evidence=payload.evidence,
        impact=payload.impact,
        source_channel=payload.source.channel,
        initiating_subject=principal.subject,
        initiating_agent_id=payload.source.agent_id,
        initiating_model_id=payload.source.model_id,
        initiating_host_id=host_id,
        source_request_id=request_id,
        policy_snapshot=_policy_snapshot(decision),
        version_preconditions=payload.version_preconditions,
        proposal_hash=_canonical_hash(immutable),
        expires_at=utc_now() + timedelta(seconds=payload.expires_in_seconds),
    )
    db.add(proposal)
    try:
        db.flush()
        _record_transition(db, principal, proposal, action="governance_proposal.create", outcome="success", request_id=request_id)
        db.commit()
        db.refresh(proposal)
        return proposal
    except Exception:
        db.rollback()
        raise ProposalWorkflowError(status.HTTP_503_SERVICE_UNAVAILABLE, "proposal_audit_unavailable", "Proposal creation could not be audited safely.")


def list_proposals(db: Session, principal: Principal, status_filter: GovernanceProposalStatus | None = None) -> list[GovernanceProposal]:
    statement = select(GovernanceProposal).order_by(GovernanceProposal.created_at.desc())
    if status_filter:
        statement = statement.where(GovernanceProposal.status == status_filter)
    proposals = list(db.scalars(statement))
    return [proposal for proposal in proposals if proposal.tenant_id == principal.tenant_id]


def approve_proposal(db: Session, principal: Principal, proposal_id: str, review_note: str, *, request_id: str) -> tuple[GovernanceProposal, str]:
    _require_steward(principal)
    proposal = proposal_or_404(db, principal, proposal_id, lock=True)
    if _expire_if_due(proposal):
        db.commit()
        raise ProposalWorkflowError(status.HTTP_409_CONFLICT, "proposal_expired", "The proposal has expired.")
    if proposal.status != GovernanceProposalStatus.PENDING_REVIEW:
        raise ProposalWorkflowError(status.HTTP_409_CONFLICT, "proposal_not_pending", "Only pending proposals can be approved.")
    decision = evaluate_rest_policy(
        db, principal=principal, action="governance.proposal.approve", resource_type="asset", resource_id=proposal.resource_id,
        purpose="governance proposal approval", request_id=request_id, workflow_id=proposal.id,
    )
    _allow_proposal_decision(decision, "proposal_approval_denied")
    nonce = secrets.token_urlsafe(32)
    proposal.status = GovernanceProposalStatus.APPROVED
    proposal.approved_by = principal.subject
    proposal.approved_at = utc_now()
    proposal.review_note = review_note
    proposal.approval_version += 1
    proposal.confirmation_nonce_digest = _hash(nonce)
    proposal.confirmation_expires_at = utc_now() + timedelta(minutes=15)
    proposal.policy_snapshot["approval_recheck"] = _policy_snapshot(decision)
    try:
        _record_transition(db, principal, proposal, action="governance_proposal.approve", outcome="success", request_id=request_id)
        db.commit()
        db.refresh(proposal)
        return proposal, nonce
    except Exception:
        db.rollback()
        raise ProposalWorkflowError(status.HTTP_503_SERVICE_UNAVAILABLE, "proposal_audit_unavailable", "Proposal approval could not be audited safely.")


def reject_proposal(db: Session, principal: Principal, proposal_id: str, review_note: str, *, request_id: str) -> GovernanceProposal:
    _require_steward(principal)
    proposal = proposal_or_404(db, principal, proposal_id, lock=True)
    if _expire_if_due(proposal):
        db.commit()
        raise ProposalWorkflowError(status.HTTP_409_CONFLICT, "proposal_expired", "The proposal has expired.")
    if proposal.status != GovernanceProposalStatus.PENDING_REVIEW:
        raise ProposalWorkflowError(status.HTTP_409_CONFLICT, "proposal_not_pending", "Only pending proposals can be rejected.")
    proposal.status = GovernanceProposalStatus.REJECTED
    proposal.rejected_by = principal.subject
    proposal.rejected_at = utc_now()
    proposal.review_note = review_note
    try:
        _record_transition(db, principal, proposal, action="governance_proposal.reject", outcome="success", request_id=request_id)
        db.commit()
        db.refresh(proposal)
        return proposal
    except Exception:
        db.rollback()
        raise ProposalWorkflowError(status.HTTP_503_SERVICE_UNAVAILABLE, "proposal_audit_unavailable", "Proposal rejection could not be audited safely.")


def cancel_proposal(db: Session, principal: Principal, proposal_id: str, *, request_id: str) -> GovernanceProposal:
    proposal = proposal_or_404(db, principal, proposal_id, lock=True)
    if proposal.initiating_subject != principal.subject:
        _require_steward(principal)
    if proposal.status not in {GovernanceProposalStatus.PENDING_REVIEW, GovernanceProposalStatus.APPROVED}:
        raise ProposalWorkflowError(status.HTTP_409_CONFLICT, "proposal_not_cancellable", "Only pending or approved proposals can be cancelled.")
    proposal.status = GovernanceProposalStatus.CANCELLED
    proposal.cancelled_by = principal.subject
    proposal.cancelled_at = utc_now()
    proposal.confirmation_nonce_digest = None
    proposal.confirmation_expires_at = None
    try:
        _record_transition(db, principal, proposal, action="governance_proposal.cancel", outcome="success", request_id=request_id)
        db.commit()
        db.refresh(proposal)
        return proposal
    except Exception:
        db.rollback()
        raise ProposalWorkflowError(status.HTTP_503_SERVICE_UNAVAILABLE, "proposal_audit_unavailable", "Proposal cancellation could not be audited safely.")


def _assert_execution_preconditions(db: Session, proposal: GovernanceProposal) -> Asset:
    asset = _asset_or_error(db, proposal.resource_id)
    expected_version = proposal.version_preconditions.get("technical_version")
    if asset.technical_version != expected_version:
        raise ProposalWorkflowError(status.HTTP_409_CONFLICT, "proposal_precondition_failed", "The governed asset changed after approval.")
    return asset


def _apply_typed_change(db: Session, proposal: GovernanceProposal, asset: Asset, principal: Principal) -> dict[str, Any]:
    if proposal.proposal_type == GovernanceProposalType.ASSET_CURATION:
        previous = {key: getattr(asset, key) for key in proposal.change_diff}
        for field, value in proposal.change_diff.items():
            setattr(asset, field, value)
        asset.curated_at = utc_now()
        db.add(AssetMetadataVersion(asset_id=asset.id, change_source=ChangeSource.CURATION, actor=principal.subject, changed_fields={"before": previous, "after": proposal.change_diff, "proposal_id": proposal.id}))
        return {"resource_type": "asset", "resource_id": asset.id, "changed_fields": sorted(proposal.change_diff)}
    if proposal.proposal_type == GovernanceProposalType.CERTIFICATION_REVIEW_REQUEST:
        request = CertificationRequest(asset_id=asset.id, requested_by=proposal.initiating_subject, decision_note=proposal.change_diff.get("note"))
        db.add(request)
        db.flush()
        return {"resource_type": "certification_request", "resource_id": request.id, "status": request.status.value}
    if proposal.proposal_type == GovernanceProposalType.QUALITY_CHECK_SCHEDULE:
        request = QualityCheckScheduleRequest(proposal_id=proposal.id, asset_id=asset.id, requested_by=proposal.initiating_subject, schedule=proposal.change_diff["schedule"])
        db.add(request)
        db.flush()
        return {"resource_type": "quality_check_schedule_request", "resource_id": request.id, "status": request.status.value}
    raise ProposalWorkflowError(status.HTTP_422_UNPROCESSABLE_ENTITY, "unsupported_proposal_type", "The proposal type has no execution handler.")


def _block_execution(db: Session, principal: Principal, proposal: GovernanceProposal, *, reason: str, request_id: str) -> None:
    proposal.status = GovernanceProposalStatus.BLOCKED
    proposal.execution_outcome = "blocked"
    proposal.blocked_reason = reason
    proposal.confirmation_nonce_digest = None
    proposal.confirmation_expires_at = None
    _record_transition(db, principal, proposal, action="governance_proposal.execute", outcome="blocked", request_id=request_id, metadata={"blocked_reason": reason})
    db.commit()


def execute_proposal(
    db: Session,
    principal: Principal,
    proposal_id: str,
    *,
    proposal_hash: str,
    confirmation_nonce: str,
    request_id: str,
) -> tuple[GovernanceProposal, dict[str, Any]]:
    _require_steward(principal)
    proposal = proposal_or_404(db, principal, proposal_id, lock=True)
    proposal.execution_attempts += 1
    try:
        if _expire_if_due(proposal):
            _block_execution(db, principal, proposal, reason="proposal_expired", request_id=request_id)
            raise ProposalWorkflowError(status.HTTP_409_CONFLICT, "proposal_expired", "The proposal has expired.")
        if proposal.status != GovernanceProposalStatus.APPROVED:
            raise ProposalWorkflowError(status.HTTP_409_CONFLICT, "proposal_not_approved", "Only an approved proposal can execute.")
        if proposal.approved_by != principal.subject:
            raise ProposalWorkflowError(status.HTTP_403_FORBIDDEN, "proposal_approver_mismatch", "Only the approving steward may confirm execution.")
        if not hmac.compare_digest(proposal.proposal_hash, proposal_hash):
            raise ProposalWorkflowError(status.HTTP_409_CONFLICT, "proposal_hash_mismatch", "The proposal hash does not match the approved proposal.")
        if proposal.confirmation_nonce_digest is None or not hmac.compare_digest(proposal.confirmation_nonce_digest, _hash(confirmation_nonce)):
            raise ProposalWorkflowError(status.HTTP_409_CONFLICT, "confirmation_nonce_invalid", "The confirmation nonce is invalid.")
        if proposal.confirmation_expires_at is None or _as_utc(proposal.confirmation_expires_at) <= utc_now():
            _block_execution(db, principal, proposal, reason="confirmation_nonce_expired", request_id=request_id)
            raise ProposalWorkflowError(status.HTTP_409_CONFLICT, "confirmation_nonce_expired", "The confirmation nonce has expired.")
        asset = _assert_execution_preconditions(db, proposal)
        decision = evaluate_rest_policy(
            db, principal=principal, action="governance.proposal.execute", resource_type="asset", resource_id=asset.id,
            purpose="governance proposal confirmation execution", request_id=request_id, workflow_id=proposal.id,
        )
        if decision.outcome != PolicyOutcome.ALLOW:
            _block_execution(db, principal, proposal, reason="proposal_reauthorization_denied", request_id=request_id)
            raise ProposalWorkflowError(status.HTTP_403_FORBIDDEN, "proposal_reauthorization_denied", "Current policy does not permit proposal execution.")
        result = _apply_typed_change(db, proposal, asset, principal)
        proposal.status = GovernanceProposalStatus.EXECUTED
        proposal.execution_outcome = "executed"
        proposal.executed_by = principal.subject
        proposal.executed_at = utc_now()
        proposal.confirmation_nonce_digest = None
        proposal.confirmation_expires_at = None
        proposal.policy_snapshot["execution_recheck"] = _policy_snapshot(decision)
        _record_transition(db, principal, proposal, action="governance_proposal.execute", outcome="success", request_id=request_id, metadata={"execution_result": result})
        db.commit()
        db.refresh(proposal)
        return proposal, result
    except ProposalWorkflowError as exc:
        # Any failed confirmation recheck must leave a durable non-executable
        # state; it may not remain silently approved for a later retry.
        if proposal.status == GovernanceProposalStatus.APPROVED:
            try:
                code = exc.detail.get("code", "proposal_execution_blocked") if isinstance(exc.detail, dict) else "proposal_execution_blocked"
                _block_execution(db, principal, proposal, reason=str(code), request_id=request_id)
            except Exception:
                if db.in_transaction():
                    db.rollback()
        elif db.in_transaction():
            db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise ProposalWorkflowError(status.HTTP_503_SERVICE_UNAVAILABLE, "proposal_execution_blocked", "Proposal execution could not complete safely.") from exc
