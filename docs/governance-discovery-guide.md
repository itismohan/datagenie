# Governed Discovery and Operational Lineage Guide

## Purpose and operating model

DataGenie’s catalog is a **decision-support** system rather than a passive inventory. Governed discovery helps an authorized user find appropriate data through technical and business context, while operational lineage records evidence-backed relationships between assets, columns, dashboards, and reports. The behavior and governance boundaries described here implement the platform’s formal contract.[1]

All examples assume a catalog base URL of `http://localhost:8000` and a separately deployed lineage base URL of `http://localhost:8002`. The optional search service remains a routing boundary at `http://localhost:8001/api/v1/search/`; it forwards the caller’s query parameters, `Authorization` header, and request identifier to catalog discovery. It does not hold a second result store or bypass catalog authorization.[2]

Every catalog request requires a bearer token when `DATAGENIE_AUTH_ENABLED=true`. The following role boundaries are enforced by the API.

| Activity | Minimum role |
|---|---|
| Search assets, read governance records, propose terms and mappings, request certification | Read-only user, analyst, data owner, data steward, or platform administrator |
| Create a domain, review a term or mapping, run/review classifications, decide certification, update quality evidence, create/review suggestions | Data steward or platform administrator |
| Read audit history | Platform administrator |

> **Important:** Sensitive-data detections are heuristic classification aids. They are not autonomous compliance decisions. Likewise, governance suggestions are drafts with evidence, not applied changes. A data steward or platform administrator must explicitly review each record before it can affect governance context.

## Governed discovery

### Create and steward a governance domain

A domain owns a bounded business area and identifies the accountable business owner and data steward. Create domains before associating them with glossary terms and assets.

```bash
curl -X POST http://localhost:8000/api/v1/governance/domains \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Finance",
    "description": "Financial reporting and planning data.",
    "business_owner": "finance-lead@example.com",
    "data_steward": "finance-steward@example.com"
  }'
```

Use `GET /api/v1/governance/domains` to list domains available to the caller.

### Propose, review, and map a glossary term

Terms start in a proposed state. An authorized steward may transition them through the review workflow using supported statuses, including `approved`, `rejected`, and `deprecated`. Mapping a term to an asset or column is a separate reviewable record.

```bash
# Propose a term
curl -X POST http://localhost:8000/api/v1/governance/glossary/terms \
  -H 'Authorization: Bearer <token>' -H 'Content-Type: application/json' \
  -d '{
    "name": "Net Revenue",
    "definition": "Revenue after contractual allowances and refunds.",
    "owner": "finance-owner@example.com",
    "domain_id": "<finance-domain-id>"
  }'

# Approve its definition
curl -X POST http://localhost:8000/api/v1/governance/glossary/terms/<term-id>/review \
  -H 'Authorization: Bearer <steward-token>' -H 'Content-Type: application/json' \
  -d '{"status":"approved","review_note":"Definition aligned to the reporting policy."}'

# Propose a mapping to an asset column, then approve it
curl -X POST http://localhost:8000/api/v1/governance/glossary/terms/<term-id>/mappings \
  -H 'Authorization: Bearer <token>' -H 'Content-Type: application/json' \
  -d '{"asset_id":"<asset-id>","column_name":"net_revenue"}'

curl -X POST http://localhost:8000/api/v1/governance/glossary/mappings/<mapping-id>/review \
  -H 'Authorization: Bearer <steward-token>' -H 'Content-Type: application/json' \
  -d '{"status":"approved"}'
```

### Search with transparent governance filters

`GET /api/v1/assets` supports filtering by asset name, source, asset type, lifecycle/certification status, owner, classification, tag, freshness, domain, business term, and technical quality. `quality_min` is constrained to `0–100`; `explainable_quality_only=true` excludes scores that lack an explainable evidence timestamp. Clients that require a search-service endpoint can call `GET /api/v1/search/` with the identical query string; it delegates to this catalog endpoint and preserves the caller’s identity and correlation header.[2]

```bash
SESSION_ID="discovery-$(uuidgen)"
curl -G http://localhost:8000/api/v1/assets \
  -H 'Authorization: Bearer <token>' \
  --data-urlencode 'q=revenue' \
  --data-urlencode 'business_term=Net Revenue' \
  --data-urlencode 'domain=Finance' \
  --data-urlencode 'lifecycle_status=certified' \
  --data-urlencode 'quality_min=85' \
  --data-urlencode 'explainable_quality_only=true' \
  --data-urlencode "discovery_session_id=${SESSION_ID}"
```

Ranking is intentionally explainable. Exact and partial technical matches, approved business-term mappings, certified lifecycle state, descriptions, owners, explainable quality, and recency each contribute to `discovery_score`. Authorization still applies before results are returned.

To count an asset view toward the same discovery session, pass the identical session identifier when retrieving the selected asset.

```bash
curl -G http://localhost:8000/api/v1/assets/<asset-id> \
  -H 'Authorization: Bearer <token>' \
  --data-urlencode "discovery_session_id=${SESSION_ID}"
```

The north-star measurement is available to stewards and administrators at `GET /api/v1/governance/metrics/discovery-success`. A successful session contains a search followed by an asset view, certification request, or approved usage decision.

### Classification detection and steward review

Run detections only on a known asset. Findings record the column, proposed category, confidence, detection evidence, detector identity, and review status. Review every finding before treating it as a governed classification.

```bash
# Create reviewable heuristic findings
curl -X POST http://localhost:8000/api/v1/governance/assets/<asset-id>/classification-detections \
  -H 'Authorization: Bearer <steward-token>'

# Inspect the evidence and review a single finding
curl http://localhost:8000/api/v1/governance/assets/<asset-id>/classification-findings \
  -H 'Authorization: Bearer <token>'

curl -X POST http://localhost:8000/api/v1/governance/classification-findings/<finding-id>/review \
  -H 'Authorization: Bearer <steward-token>' -H 'Content-Type: application/json' \
  -d '{
    "status":"approved",
    "review_note":"Confirmed against the governed data dictionary."
  }'
```

Current deterministic patterns target common categories, including email addresses, phone numbers, government identifiers, payment data, and health-related information. A false positive must be rejected or otherwise corrected through this review workflow rather than silently accepted.

### Certification and explainable quality evidence

Certification is distinct from technical quality and business criticality. Analysts and other authorized readers may request certification; a steward decides it after reviewing evidence. A quality score may be published to discovery only with an associated explainability timestamp and quality-run identifier.

```bash
curl -X POST http://localhost:8000/api/v1/governance/assets/<asset-id>/certification-requests \
  -H 'Authorization: Bearer <token>' -H 'Content-Type: application/json' \
  -d '{"note":"Required for the monthly management report."}'

curl -X POST http://localhost:8000/api/v1/governance/certification-requests/<request-id>/decision \
  -H 'Authorization: Bearer <steward-token>' -H 'Content-Type: application/json' \
  -d '{"status":"approved","decision_note":"Quality evidence and owner confirmed."}'

curl -X PUT http://localhost:8000/api/v1/governance/assets/<asset-id>/quality-evidence \
  -H 'Authorization: Bearer <steward-token>' -H 'Content-Type: application/json' \
  -d '{
    "technical_score": 92,
    "explainable_at": "2026-08-21T09:30:00Z",
    "quality_run_id": "quality-run-20260821-001"
  }'
```

### Assistance suggestions are never auto-applied

A description draft, owner candidate, glossary mapping, lineage summary, metadata-gap observation, or quality-rule recommendation must be stored as a governance suggestion with its evidence. The accepted suggestion types are `description`, `glossary_mapping`, `owner`, `lineage_summary`, `metadata_gap`, and `quality_rule`.[3] The review action records an accountable human decision but does **not** silently mutate the target asset.

```bash
curl -X POST http://localhost:8000/api/v1/governance/suggestions \
  -H 'Authorization: Bearer <steward-token>' -H 'Content-Type: application/json' \
  -d '{
    "asset_id":"<asset-id>",
    "suggestion_type":"description",
    "proposed_value":{"description":"Draft description for finance payment records."},
    "evidence":{"column_names":["payment_id","amount"],"source":"catalog metadata"},
    "generated_by":"governance-assistant-v1"
  }'

curl -X POST http://localhost:8000/api/v1/governance/suggestions/<suggestion-id>/review \
  -H 'Authorization: Bearer <steward-token>' -H 'Content-Type: application/json' \
  -d '{"status":"approved","review_note":"Validated against the source system owner."}'
```

## Operational lineage and impact analysis

Lineage is held in Neo4j as durable, typed graph edges. Supported relationship types are `FLOWS_TO`, `DERIVES_FROM`, `CONSUMES`, and `COLUMN_FLOWS_TO`. Each event includes an idempotency key (`event_id`), source provenance, confidence, observation time, and arbitrary metadata. Ingest it from connectors or transformation tools rather than asking users to construct relationships manually.

```bash
curl -X POST http://localhost:8002/api/v1/lineage/events \
  -H 'Content-Type: application/json' \
  -d '{
    "event_id":"dbt-run-112:model.finance.revenue",
    "source":{"id":"warehouse.finance.payments","node_type":"asset","owner":"finance-owner@example.com","business_criticality":"critical"},
    "target":{"id":"warehouse.finance.revenue","node_type":"asset","owner":"finance-owner@example.com","domain":"Finance","business_criticality":"critical"},
    "relationship_type":"DERIVES_FROM",
    "source_provenance":"dbt-manifest",
    "confidence":95,
    "observed_at":"2026-08-21T09:30:00Z",
    "metadata":{"run_id":"dbt-run-112","model":"finance.revenue"}
  }'
```

Column-level lineage uses `node_type: "column"` and the `COLUMN_FLOWS_TO` relationship. Preserve durable column identifiers in node IDs, such as `warehouse.finance.payments.amount`.

Retrieve a graph around an asset using an explicit direction and bounded depth.

```bash
curl -G http://localhost:8002/api/v1/lineage/warehouse.finance.payments \
  --data-urlencode 'direction=downstream' \
  --data-urlencode 'max_depth=4'
```

A quality incident links an operational event to its affected source, then returns downstream assets, dashboards, or reports ordered with criticality and distance. The result identifies owners, domains, and minimum path confidence for escalation.

```bash
curl -X POST http://localhost:8002/api/v1/lineage/impact/quality-incidents \
  -H 'Content-Type: application/json' \
  -d '{
    "asset_id":"warehouse.finance.payments",
    "max_depth":5,
    "incident_id":"quality-incident-331",
    "severity":"critical",
    "evidence":{"failed_rule":"completeness","failed_column":"amount","score":72}
  }'
```

Use the schema-change endpoint before deploying a breaking alteration. The response provides an accountable impact list for owner and consumer communication.

```bash
curl -X POST http://localhost:8002/api/v1/lineage/impact/schema-changes \
  -H 'Content-Type: application/json' \
  -d '{
    "asset_id":"warehouse.finance.payments",
    "max_depth":5,
    "change_id":"migration-20260821-drop-legacy-code",
    "change_summary":"Remove deprecated legacy_payment_code column.",
    "changed_columns":["legacy_payment_code"]
  }'
```

## Deployment and operational checks

Apply catalog migrations before serving catalog traffic. The governed-discovery and assistance-taxonomy migration head is `20260821_05`.

```bash
cd apps/catalog-api
DATAGENIE_DATABASE_URL='postgresql+psycopg://<user>:<password>@<host>:5432/<database>' alembic upgrade head
alembic current
```

The catalog exposes `/health`, `/health/live`, `/health/ready`, and `/metrics`. The lineage service exposes `/health`, `/health/live`, and `/health/ready`; readiness runs `RETURN 1` against Neo4j and returns HTTP 503 if the graph store is unavailable. Docker Compose health checks use these readiness endpoints, so an unhealthy lineage graph is visible to local orchestration.

Capture `X-Request-ID` from catalog responses when investigating an operation. Governance writes and reads are audited, including actor, action, resource, result, and request correlation metadata. Retain audit exports and operational lineage event provenance according to the organization’s approved retention policy; multi-tenancy, SCIM, formal retention enforcement, exports, webhooks, and usage analytics remain explicit enterprise-boundary work rather than implied behavior in this release.

## References

1. [DataGenie governance and lineage contract][1]
2. [Catalog-backed search delegation implementation][2]
3. [Governance suggestion taxonomy][3]

[1]: governance-lineage-contract.md
[2]: ../apps/search-api/app/services/search_service.py
[3]: ../apps/catalog-api/app/models/catalog.py
