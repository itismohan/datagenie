# DataGenie Governed Discovery and Operational Lineage Contract

## Governed discovery model

Search is a **decision-support workflow**, not only a text lookup. A session begins with a query and becomes successful when the same session leads to an asset view, a certification request, or an approved usage decision. Results are filtered through the existing Catalog API authorization boundary and ranked using transparent, deterministic signals.

| Ranking signal | Intent |
|---|---|
| Exact and partial name match | Favor direct relevance to the user’s query |
| Business term match | Favor approved glossary concepts mapped to the asset or column |
| Certification | Prioritize certified assets without hiding non-certified evidence |
| Documentation and ownership | Prefer assets with a description and accountable owner |
| Recency | Prefer recently updated technical metadata |
| Quality evidence | Boost assets with a recent explainable technical-quality snapshot; score does not replace certification |

Search supports asset name, business term, owner, domain, tag, classification, quality score, freshness, lifecycle/certification status, and source. Permission filtering is applied before ranking so relevance cannot leak unauthorized records.

## Governance records

| Record | Purpose |
|---|---|
| `governance_domains` | Finance, Sales, Operations, Risk, and customer-defined domains with business owner and data steward |
| `business_glossary_terms` | Proposed, approved, rejected, or deprecated definitions with proposed/reviewed metadata |
| `glossary_asset_mappings` | Approved or pending links between a term and an asset or column |
| `classification_findings` | Human-reviewable sensitive-data detections based on column name/type evidence; never autonomous compliance determinations |
| `discovery_events` | Session-scoped search, asset-view, certification-request, and usage-decision events for outcome metrics |
| `governance_suggestions` | Human-reviewed recommendations such as description drafts, glossary mappings, likely owners, and quality-rule suggestions; source, evidence, and status are immutable |

Sensitive-data classification begins with configurable column-name and technical-type detection for email address, phone number, government identifier, payment data, and health-related data. A finding remains `proposed` until a steward approves or rejects it. Rejecting a finding records reviewer and rationale; it does not delete detection evidence.

## Operational lineage model

Lineage is persisted in Neo4j as typed, directed relationships between asset or column nodes. Every relationship includes `relationship_type`, `event_id`, `source_provenance`, `confidence`, `observed_at`, and `created_at`. Connector or transformation emitters submit idempotent lineage events; users do not need to manually recreate relations after every harvest.

| Relationship type | Meaning |
|---|---|
| `FLOWS_TO` | Source data contributes to a downstream asset |
| `DERIVES_FROM` | A transform derives the target from the source |
| `CONSUMES` | A report, dashboard, or consumer uses an asset |
| `COLUMN_FLOWS_TO` | Column-level source-to-target lineage |

Traversal answers upstream and downstream questions with depth limits and typed edges. Impact analysis follows downstream relationships and returns consumer, owner, domain, business criticality, and confidence where the lineage event provided them. Quality-incident and schema-change impact endpoints use this traversal and return affected downstream assets rather than claiming an unsupported automatic remediation.

## Human-reviewed assistance and enterprise boundary

DataGenie suggestions are not governance actions. Each proposal displays the evidence and generation source, begins in `pending` status, and requires an authorized steward to approve or reject it. An approved suggestion is applied by an explicit endpoint and audited.

The current enterprise integration boundary preserves stable principal, role, external subject, audit, and event interfaces. OIDC/JWKS validation, SAML, SCIM, multi-tenancy, retention configuration, signed webhooks, and export APIs remain explicit follow-on integrations rather than placeholder claims of enterprise compliance.
