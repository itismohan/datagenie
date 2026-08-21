from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    ROLE_ANALYST,
    ROLE_DATA_OWNER,
    ROLE_DATA_STEWARD,
    ROLE_PLATFORM_ADMIN,
    ROLE_READ_ONLY,
    Principal,
    require_roles,
)
from app.db.session import get_db
from app.models.catalog import (
    BusinessGlossaryTerm,
    DiscoveryEventType,
    CertificationRequest,
    ClassificationFinding,
    GlossaryAssetMapping,
    GovernanceSuggestion,
)
from app.schemas.governance import (
    CertificationRequestCreate,
    CertificationRequestDecision,
    CertificationRequestRead,
    AssetQualityEvidenceUpdate,
    ClassificationFindingRead,
    ClassificationReview,
    DiscoveryEventCreate,
    DiscoveryMetricRead,
    DomainCreate,
    DomainRead,
    GlossaryAssetMappingCreate,
    GlossaryAssetMappingRead,
    GlossaryAssetMappingReview,
    GlossaryTermCreate,
    GlossaryTermRead,
    GlossaryTermReview,
    GovernanceSuggestionCreate,
    GovernanceSuggestionRead,
    GovernanceSuggestionReview,
)
from app.services.audit_service import record_audit_event
from app.services.governance_service import (
    create_certification_request,
    create_domain,
    create_glossary_term,
    create_mapping,
    create_suggestion,
    decide_certification_request,
    detect_classifications,
    discovery_metric,
    get_asset_or_404,
    get_certification_request_or_404,
    get_finding_or_404,
    get_suggestion_or_404,
    get_term_or_404,
    list_domains,
    record_discovery_event,
    review_finding,
    review_mapping,
    review_suggestion,
    review_term,
)

router = APIRouter()
asset_reader = require_roles(ROLE_PLATFORM_ADMIN, ROLE_DATA_STEWARD, ROLE_DATA_OWNER, ROLE_ANALYST, ROLE_READ_ONLY)
governance_editor = require_roles(ROLE_PLATFORM_ADMIN, ROLE_DATA_STEWARD)


def request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def audit(db: Session, principal: Principal, request: Request, action: str, resource_type: str, resource_id: str | None, metadata: dict | None = None) -> None:
    record_audit_event(
        db,
        principal=principal,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome="success",
        request_id=request_id(request),
        metadata=metadata or {},
    )
    db.commit()


@router.post("/domains", response_model=DomainRead, status_code=status.HTTP_201_CREATED)
def create_governance_domain(payload: DomainCreate, request: Request, db: Session = Depends(get_db), principal: Principal = Depends(governance_editor)):
    domain = create_domain(db, payload)
    audit(db, principal, request, "domain.create", "governance_domain", domain.id)
    return domain


@router.get("/domains", response_model=list[DomainRead])
def get_governance_domains(request: Request, db: Session = Depends(get_db), principal: Principal = Depends(asset_reader)):
    domains = list_domains(db)
    audit(db, principal, request, "domain.list", "governance_domain", None, {"result_count": len(domains)})
    return domains


@router.post("/glossary/terms", response_model=GlossaryTermRead, status_code=status.HTTP_201_CREATED)
def propose_glossary_term(payload: GlossaryTermCreate, request: Request, db: Session = Depends(get_db), principal: Principal = Depends(asset_reader)):
    term = create_glossary_term(db, payload.name, payload.definition, payload.owner, payload.domain_id, principal.subject)
    audit(db, principal, request, "glossary.propose", "glossary_term", term.id)
    return term


@router.get("/glossary/terms", response_model=list[GlossaryTermRead])
def get_governed_glossary(request: Request, status_filter: str | None = None, db: Session = Depends(get_db), principal: Principal = Depends(asset_reader)):
    statement = select(BusinessGlossaryTerm)
    if status_filter:
        statement = statement.where(BusinessGlossaryTerm.status == status_filter)
    terms = list(db.scalars(statement.order_by(BusinessGlossaryTerm.name.asc())))
    audit(db, principal, request, "glossary.list_governed", "glossary_term", None, {"result_count": len(terms)})
    return terms


@router.post("/glossary/terms/{term_id}/review", response_model=GlossaryTermRead)
def review_glossary_term(term_id: str, payload: GlossaryTermReview, request: Request, db: Session = Depends(get_db), principal: Principal = Depends(governance_editor)):
    term = review_term(db, get_term_or_404(db, term_id), payload.status, payload.review_note, principal.subject)
    audit(db, principal, request, "glossary.review", "glossary_term", term.id, {"status": term.status.value})
    return term


@router.post("/glossary/terms/{term_id}/mappings", response_model=GlossaryAssetMappingRead, status_code=status.HTTP_201_CREATED)
def propose_glossary_mapping(term_id: str, payload: GlossaryAssetMappingCreate, request: Request, db: Session = Depends(get_db), principal: Principal = Depends(asset_reader)):
    mapping = create_mapping(db, get_term_or_404(db, term_id), payload.asset_id, payload.column_name, principal.subject)
    audit(db, principal, request, "glossary_mapping.propose", "glossary_asset_mapping", mapping.id)
    return mapping


@router.post("/glossary/mappings/{mapping_id}/review", response_model=GlossaryAssetMappingRead)
def review_glossary_mapping(mapping_id: str, payload: GlossaryAssetMappingReview, request: Request, db: Session = Depends(get_db), principal: Principal = Depends(governance_editor)):
    mapping = db.get(GlossaryAssetMapping, mapping_id)
    if mapping is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Glossary mapping not found.")
    mapping = review_mapping(db, mapping, payload.status, principal.subject)
    audit(db, principal, request, "glossary_mapping.review", "glossary_asset_mapping", mapping.id, {"status": mapping.status.value})
    return mapping


@router.post("/assets/{asset_id}/classification-detections", response_model=list[ClassificationFindingRead])
def detect_sensitive_classification(asset_id: str, request: Request, db: Session = Depends(get_db), principal: Principal = Depends(governance_editor)):
    findings = detect_classifications(db, get_asset_or_404(db, asset_id), "deterministic-classifier")
    audit(db, principal, request, "classification.detect", "asset", asset_id, {"finding_count": len(findings)})
    return findings


@router.get("/assets/{asset_id}/classification-findings", response_model=list[ClassificationFindingRead])
def get_classification_findings(asset_id: str, request: Request, db: Session = Depends(get_db), principal: Principal = Depends(asset_reader)):
    get_asset_or_404(db, asset_id)
    findings = list(db.scalars(select(ClassificationFinding).where(ClassificationFinding.asset_id == asset_id)))
    audit(db, principal, request, "classification.list", "asset", asset_id, {"result_count": len(findings)})
    return findings


@router.post("/classification-findings/{finding_id}/review", response_model=ClassificationFindingRead)
def review_classification(finding_id: str, payload: ClassificationReview, request: Request, db: Session = Depends(get_db), principal: Principal = Depends(governance_editor)):
    finding = review_finding(db, get_finding_or_404(db, finding_id), payload.status, payload.review_note, principal.subject)
    audit(db, principal, request, "classification.review", "classification_finding", finding.id, {"status": finding.status.value})
    return finding


@router.put("/assets/{asset_id}/quality-evidence")
def put_asset_quality_evidence(asset_id: str, payload: AssetQualityEvidenceUpdate, request: Request, db: Session = Depends(get_db), principal: Principal = Depends(governance_editor)):
    asset = get_asset_or_404(db, asset_id)
    asset.quality_score = payload.technical_score
    asset.quality_explainable_at = payload.explainable_at
    db.commit()
    audit(db, principal, request, "quality_evidence.update", "asset", asset.id, {"quality_run_id": payload.quality_run_id, "technical_score": payload.technical_score})
    return {"asset_id": asset.id, "technical_score": asset.quality_score, "explainable_at": asset.quality_explainable_at, "quality_run_id": payload.quality_run_id}


@router.post("/assets/{asset_id}/certification-requests", response_model=CertificationRequestRead, status_code=status.HTTP_201_CREATED)
def request_certification(asset_id: str, payload: CertificationRequestCreate, request: Request, db: Session = Depends(get_db), principal: Principal = Depends(asset_reader)):
    certification = create_certification_request(db, asset_id, principal.subject, payload.note)
    record_discovery_event(db, request_id(request), principal.subject, DiscoveryEventType.CERTIFICATION_REQUEST, asset_id, None, {"request_id": certification.id})
    audit(db, principal, request, "certification.request", "certification_request", certification.id)
    return certification


@router.post("/certification-requests/{certification_id}/decision", response_model=CertificationRequestRead)
def decide_certification(certification_id: str, payload: CertificationRequestDecision, request: Request, db: Session = Depends(get_db), principal: Principal = Depends(governance_editor)):
    certification = decide_certification_request(db, get_certification_request_or_404(db, certification_id), payload.status, payload.decision_note, principal.subject)
    record_discovery_event(db, request_id(request), principal.subject, DiscoveryEventType.USAGE_DECISION, certification.asset_id, None, {"status": certification.status.value})
    audit(db, principal, request, "certification.decide", "certification_request", certification.id, {"status": certification.status.value})
    return certification


@router.post("/discovery-events", status_code=status.HTTP_201_CREATED)
def create_discovery_event(payload: DiscoveryEventCreate, request: Request, db: Session = Depends(get_db), principal: Principal = Depends(asset_reader)):
    event = record_discovery_event(db, payload.session_id, principal.subject, payload.event_type, payload.asset_id, payload.query_text, payload.metadata_json)
    audit(db, principal, request, "discovery_event.create", "discovery_event", event.id, {"event_type": event.event_type.value})
    return {"id": event.id}


@router.get("/metrics/discovery-success", response_model=DiscoveryMetricRead)
def get_discovery_success_metric(request: Request, db: Session = Depends(get_db), principal: Principal = Depends(governance_editor)):
    sessions, successful_sessions, outcomes = discovery_metric(db)
    audit(db, principal, request, "discovery_metric.read", "discovery_metric", None)
    return DiscoveryMetricRead(sessions=sessions, successful_sessions=successful_sessions, percentage=round((successful_sessions / sessions) * 100, 2) if sessions else 0.0, successful_by_outcome=outcomes)


@router.post("/suggestions", response_model=GovernanceSuggestionRead, status_code=status.HTTP_201_CREATED)
def create_governance_suggestion(payload: GovernanceSuggestionCreate, request: Request, db: Session = Depends(get_db), principal: Principal = Depends(governance_editor)):
    suggestion = create_suggestion(db, payload.asset_id, payload.suggestion_type, payload.proposed_value, payload.evidence, payload.generated_by)
    audit(db, principal, request, "suggestion.create", "governance_suggestion", suggestion.id)
    return suggestion


@router.post("/suggestions/{suggestion_id}/review", response_model=GovernanceSuggestionRead)
def review_governance_suggestion(suggestion_id: str, payload: GovernanceSuggestionReview, request: Request, db: Session = Depends(get_db), principal: Principal = Depends(governance_editor)):
    suggestion = review_suggestion(db, get_suggestion_or_404(db, suggestion_id), payload.status, payload.review_note, principal.subject)
    audit(db, principal, request, "suggestion.review", "governance_suggestion", suggestion.id, {"status": suggestion.status.value})
    return suggestion
