from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from time import perf_counter
from typing import Callable

from sqlalchemy.orm import Session

from app.core.observability import (
    POLICY_AUDIT_WRITE_FAILURES,
    POLICY_DECISION_LATENCY,
    POLICY_DECISIONS,
    POLICY_TENANT_BOUNDARY_VIOLATIONS,
)
from app.core.security import (
    ROLE_ANALYST,
    ROLE_DATA_OWNER,
    ROLE_DATA_STEWARD,
    ROLE_PLATFORM_ADMIN,
    ROLE_READ_ONLY,
    Principal,
)
from app.db.session import session_tenant_id
from app.models.catalog import (
    Asset,
    CertificationRequest,
    ClassificationFinding,
    GovernanceDomain,
    LifecycleStatus,
)
from app.schemas.policy import (
    PolicyContext,
    PolicyDecisionRead,
    PolicyEvidenceReference,
    PolicyOutcome,
    PolicyResource,
)
from app.services.audit_service import record_audit_event


POLICY_DECISION_VERSION = "1.0.0"
QUALITY_FRESHNESS_MAX_AGE = timedelta(days=7)
SENSITIVE_CLASSIFICATIONS = {
    "email_address",
    "phone_number",
    "government_identifier",
    "payment_data",
    "health_information",
}
SENSITIVE_PURPOSE_KEYWORDS = {
    "analysis",
    "analytics",
    "audit",
    "compliance",
    "financial",
    "reporting",
    "risk",
    "security",
}


class PolicyEvaluationError(RuntimeError):
    """Raised when a protected policy decision cannot be safely evaluated or audited."""


@dataclass(frozen=True)
class ResolvedPolicyResource:
    resource: PolicyResource
    asset: Asset | None
    visible: bool
    classification: str | None
    lifecycle_status: LifecycleStatus | None
    owner: str | None
    domain: GovernanceDomain | None
    certification: CertificationRequest | None


@dataclass(frozen=True)
class PolicyDecision:
    outcome: PolicyOutcome
    rule_ids: tuple[str, ...]
    evidence: tuple[PolicyEvidenceReference, ...]
    obligations: tuple[str, ...]
    evaluated_at: datetime
    expires_at: datetime
    request_id: str
    resource_visible: bool

    def to_read(self) -> PolicyDecisionRead:
        return PolicyDecisionRead(
            outcome=self.outcome,
            decision_version=POLICY_DECISION_VERSION,
            rule_ids=list(self.rule_ids),
            evidence=list(self.evidence),
            obligations=list(self.obligations),
            evaluated_at=self.evaluated_at,
            expires_at=self.expires_at,
            request_id=self.request_id,
            resource_visible=self.resource_visible,
        )


SUPPORTED_ACTIONS: dict[str, tuple[str, bool]] = {
    "asset.read": ("asset", True),
    "asset.curate": ("asset", False),
    "quality_evidence.update": ("asset", False),
    "classification.review": ("classification_finding", False),
    "certification.decide": ("certification_request", False),
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _purpose_digest(purpose: str | None) -> str | None:
    if purpose is None:
        return None
    return sha256(purpose.encode("utf-8")).hexdigest()


def _evidence(type_: str, reference: str) -> PolicyEvidenceReference:
    return PolicyEvidenceReference(type=type_, reference=reference)


def _decision(
    outcome: PolicyOutcome,
    rule_ids: list[str],
    evidence: list[PolicyEvidenceReference],
    obligations: list[str],
    evaluated_at: datetime,
    request_id: str,
    resource_visible: bool,
    ttl: timedelta = timedelta(minutes=5),
) -> PolicyDecision:
    return PolicyDecision(
        outcome=outcome,
        rule_ids=tuple(rule_ids),
        evidence=tuple(evidence),
        obligations=tuple(sorted(set(obligations))),
        evaluated_at=evaluated_at,
        expires_at=evaluated_at + ttl,
        request_id=request_id,
        resource_visible=resource_visible,
    )


def _role_allows(principal: Principal, action: str) -> bool:
    if ROLE_PLATFORM_ADMIN in principal.roles:
        return True
    readers = {ROLE_DATA_STEWARD, ROLE_DATA_OWNER, ROLE_ANALYST, ROLE_READ_ONLY}
    if action == "asset.read":
        return bool(principal.roles.intersection(readers))
    if action == "asset.curate":
        return bool(principal.roles.intersection({ROLE_DATA_STEWARD, ROLE_DATA_OWNER}))
    if action in {"quality_evidence.update", "classification.review", "certification.decide"}:
        return ROLE_DATA_STEWARD in principal.roles
    return False


def _has_sensitive_classification(classification: str | None) -> bool:
    if not classification:
        return False
    values = {value.strip().lower() for value in classification.split(",") if value.strip()}
    return bool(values.intersection(SENSITIVE_CLASSIFICATIONS))


def _purpose_is_permitted(purpose: str | None) -> bool:
    if purpose is None:
        return False
    normalized = purpose.lower()
    return any(keyword in normalized for keyword in SENSITIVE_PURPOSE_KEYWORDS)


def _quality_is_fresh(asset: Asset, now: datetime) -> bool:
    return asset.quality_explainable_at is not None and asset.quality_explainable_at >= now - QUALITY_FRESHNESS_MAX_AGE


def _resolve_resource(db: Session, resource: PolicyResource) -> ResolvedPolicyResource:
    if resource.resource_type == "asset":
        asset = db.get(Asset, resource.resource_id)
        if asset is None:
            return ResolvedPolicyResource(resource, None, False, None, None, None, None, None)
        return ResolvedPolicyResource(
            resource,
            asset,
            True,
            asset.classification,
            asset.lifecycle_status,
            asset.owner,
            asset.domain,
            None,
        )

    if resource.resource_type == "classification_finding":
        finding = db.get(ClassificationFinding, resource.resource_id)
        if finding is None:
            return ResolvedPolicyResource(resource, None, False, None, None, None, None, None)
        asset = db.get(Asset, finding.asset_id)
        if asset is None:
            return ResolvedPolicyResource(resource, None, False, None, None, None, None, None)
        return ResolvedPolicyResource(
            resource,
            asset,
            True,
            asset.classification,
            asset.lifecycle_status,
            asset.owner,
            asset.domain,
            None,
        )

    if resource.resource_type == "certification_request":
        certification = db.get(CertificationRequest, resource.resource_id)
        if certification is None:
            return ResolvedPolicyResource(resource, None, False, None, None, None, None, None)
        asset = db.get(Asset, certification.asset_id)
        if asset is None:
            return ResolvedPolicyResource(resource, None, False, None, None, None, None, None)
        return ResolvedPolicyResource(
            resource,
            asset,
            True,
            asset.classification,
            asset.lifecycle_status,
            asset.owner,
            asset.domain,
            certification,
        )

    return ResolvedPolicyResource(resource, None, False, None, None, None, None, None)


def _resource_evidence(resource: ResolvedPolicyResource) -> list[PolicyEvidenceReference]:
    if not resource.visible or resource.asset is None:
        return [_evidence("resource", "not-visible")]
    evidence = [
        _evidence("tenant", "active-tenant"),
        _evidence("asset", f"asset:metadata-version:{resource.asset.technical_version}"),
        _evidence("lifecycle", resource.asset.lifecycle_status.value),
    ]
    if resource.asset.classification:
        evidence.append(_evidence("classification", f"classification:{resource.asset.classification}"))
    if resource.asset.owner:
        evidence.append(_evidence("owner_assignment", "asset-owner-assigned"))
    if resource.domain and resource.domain.data_steward:
        evidence.append(_evidence("steward_assignment", "domain-steward-assigned"))
    if resource.asset.quality_explainable_at:
        evidence.append(_evidence("quality", f"explainable-at:{resource.asset.quality_explainable_at.isoformat()}"))
    else:
        evidence.append(_evidence("quality", "explainable-quality-missing"))
    return evidence


def _evaluate_rules(
    principal: Principal,
    action: str,
    resolved: ResolvedPolicyResource,
    purpose: str | None,
    request_id: str,
    now: datetime,
) -> PolicyDecision:
    evidence = _resource_evidence(resolved)
    if not resolved.visible or resolved.asset is None:
        return _decision(
            PolicyOutcome.DENY,
            ["DG-POLICY-TENANT-NONVISIBLE"],
            evidence,
            [],
            now,
            request_id,
            False,
        )

    if not _role_allows(principal, action):
        return _decision(
            PolicyOutcome.DENY,
            ["DG-POLICY-RBAC-DENY"],
            evidence + [_evidence("rbac", "role-not-eligible")],
            [],
            now,
            request_id,
            True,
        )

    rule_ids = ["DG-POLICY-TENANT-ALLOW", "DG-POLICY-RBAC-ALLOW"]
    evidence.append(_evidence("rbac", "validated-role-eligible"))

    if action == "asset.curate":
        is_steward = ROLE_DATA_STEWARD in principal.roles or ROLE_PLATFORM_ADMIN in principal.roles
        is_owner = ROLE_DATA_OWNER in principal.roles and resolved.owner == principal.subject
        if not is_steward and not is_owner:
            return _decision(
                PolicyOutcome.DENY,
                rule_ids + ["DG-POLICY-OWNERSHIP-DENY"],
                evidence + [_evidence("owner_assignment", "subject-not-asset-owner")],
                [],
                now,
                request_id,
                True,
            )
        rule_ids.append("DG-POLICY-OWNERSHIP-ALLOW" if is_owner else "DG-POLICY-STEWARDSHIP-ALLOW")

    if resolved.lifecycle_status == LifecycleStatus.DEPRECATED and action == "asset.read":
        return _decision(
            PolicyOutcome.DENY,
            rule_ids + ["DG-POLICY-LIFECYCLE-DEPRECATED-DENY"],
            evidence,
            [],
            now,
            request_id,
            True,
        )

    if action == "asset.read":
        if _has_sensitive_classification(resolved.classification):
            if not _purpose_is_permitted(purpose):
                return _decision(
                    PolicyOutcome.DENY,
                    rule_ids + ["DG-POLICY-CLASSIFICATION-PURPOSE-DENY"],
                    evidence + [_evidence("purpose", "not-permitted-for-sensitive-classification")],
                    [],
                    now,
                    request_id,
                    True,
                )
            rule_ids.append("DG-POLICY-CLASSIFICATION-OBLIGATION")
            return _decision(
                PolicyOutcome.ALLOW_WITH_OBLIGATIONS,
                rule_ids,
                evidence + [_evidence("purpose", "declared-permitted")],
                ["cite_governance_evidence", "handle_sensitive_data"],
                now,
                request_id,
                True,
            )
        if resolved.lifecycle_status == LifecycleStatus.CERTIFIED and not _quality_is_fresh(resolved.asset, now):
            return _decision(
                PolicyOutcome.ALLOW_WITH_OBLIGATIONS,
                rule_ids + ["DG-POLICY-QUALITY-FRESHNESS-OBLIGATION"],
                evidence,
                ["review_quality_evidence"],
                now,
                request_id,
                True,
            )

    if action == "certification.decide" and not _quality_is_fresh(resolved.asset, now):
        return _decision(
            PolicyOutcome.REQUIRES_HUMAN_APPROVAL,
            rule_ids + ["DG-POLICY-QUALITY-FRESHNESS-APPROVAL"],
            evidence,
            ["obtain_current_explainable_quality_evidence", "eligible_steward_approval"],
            now,
            request_id,
            True,
        )

    return _decision(
        PolicyOutcome.ALLOW,
        rule_ids + ["DG-POLICY-ACTION-ALLOW"],
        evidence,
        [],
        now,
        request_id,
        True,
    )


def _rule_family(rule_ids: tuple[str, ...]) -> str:
    if not rule_ids:
        return "unknown"
    parts = rule_ids[-1].split("-")
    return parts[2].lower() if len(parts) > 2 else "unknown"


def _record_policy_decision(
    db: Session,
    principal: Principal,
    action: str,
    resource: PolicyResource,
    purpose: str | None,
    decision: PolicyDecision,
    duration_ms: float,
) -> None:
    metadata = {
        "policy_action": action,
        "decision_version": POLICY_DECISION_VERSION,
        "rule_ids": list(decision.rule_ids),
        "evidence_references": [item.model_dump() for item in decision.evidence],
        "obligations": list(decision.obligations),
        "expires_at": decision.expires_at.isoformat(),
        "purpose_digest": _purpose_digest(purpose),
        "purpose_category": "declared" if purpose else "missing",
        "resource_visible": decision.resource_visible,
        "duration_ms": round(duration_ms, 2),
    }
    try:
        record_audit_event(
            db,
            principal=principal,
            action="policy.decision",
            resource_type=resource.resource_type,
            resource_id=resource.resource_id if decision.resource_visible else None,
            outcome=decision.outcome.value,
            request_id=decision.request_id,
            metadata=metadata,
        )
        db.flush()
    except Exception as exc:
        POLICY_AUDIT_WRITE_FAILURES.labels(action=action).inc()
        raise PolicyEvaluationError("Policy decision audit evidence could not be persisted.") from exc


def evaluate_access(
    db: Session,
    *,
    subject: Principal,
    tenant: str,
    action: str,
    resource: PolicyResource,
    purpose: str | None,
    context: PolicyContext,
) -> PolicyDecision:
    """Evaluate deterministic tenant-aware access and persist safe decision evidence.

    The explicit tenant argument exists for transport adapters but must match the
    validated principal and the active tenant-scoped database session.
    """
    started = perf_counter()
    now = _now()
    if action not in SUPPORTED_ACTIONS or SUPPORTED_ACTIONS[action][0] != resource.resource_type:
        decision = _decision(
            PolicyOutcome.DENY,
            ["DG-POLICY-CONTRACT-UNSUPPORTED"],
            [_evidence("contract", "unsupported-action-or-resource")],
            [],
            now,
            context.request_id or "unknown",
            False,
        )
    elif tenant != subject.tenant_id or tenant != session_tenant_id(db):
        POLICY_TENANT_BOUNDARY_VIOLATIONS.labels(action=action).inc()
        decision = _decision(
            PolicyOutcome.DENY,
            ["DG-POLICY-TENANT-MISMATCH"],
            [_evidence("tenant", "tenant-context-mismatch")],
            [],
            now,
            context.request_id or "unknown",
            False,
        )
    else:
        resolved = _resolve_resource(db, resource)
        purpose_required = SUPPORTED_ACTIONS[action][1]
        effective_purpose = purpose if purpose_required else purpose
        decision = _evaluate_rules(subject, action, resolved, effective_purpose, context.request_id or "unknown", now)

    duration = perf_counter() - started
    _record_policy_decision(db, subject, action, resource, purpose, decision, duration * 1000)
    POLICY_DECISIONS.labels(action=action, outcome=decision.outcome.value, rule_family=_rule_family(decision.rule_ids)).inc()
    POLICY_DECISION_LATENCY.labels(action=action).observe(duration)
    return decision


def evaluate_rest_policy(
    db: Session,
    *,
    principal: Principal,
    action: str,
    resource_type: str,
    resource_id: str,
    purpose: str | None,
    request_id: str,
    workflow_id: str | None = None,
) -> PolicyDecision:
    """REST/UI adapter. Future MCP transport must call this semantic boundary too."""
    return evaluate_access(
        db,
        subject=principal,
        tenant=principal.tenant_id,
        action=action,
        resource=PolicyResource(resource_type=resource_type, resource_id=resource_id),
        purpose=purpose,
        context=PolicyContext(request_id=request_id, workflow_id=workflow_id),
    )


def require_allowed(decision: PolicyDecision) -> None:
    """Raise a policy error for any non-allow route execution outcome."""
    if decision.outcome == PolicyOutcome.ALLOW:
        return
    if decision.outcome == PolicyOutcome.ALLOW_WITH_OBLIGATIONS:
        raise PermissionError("Policy obligations must be explicitly fulfilled by the calling channel.")
    if decision.outcome == PolicyOutcome.REQUIRES_HUMAN_APPROVAL:
        raise RuntimeError("The requested action requires an eligible human approval workflow.")
    raise PermissionError("The policy decision denied this action.")
