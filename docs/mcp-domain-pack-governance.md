# DataGenie MCP Domain-Pack Governance

## Purpose

Domain packs allow DataGenie to address validated customer workflows—such as Finance controls, Risk evidence, or Data Product publishing—without turning MCP into an indiscriminate tool catalog. A domain pack is a bounded combination of governed resources, prompts, evidence templates, search facets, policy obligations, proposal types, documentation, and, only when justified, separately scoped tools.

> **Default design order:** Reuse an existing governed discovery tool; then add a prompt, resource, evidence template, facet, or proposal type; consider a new tool only after the lower-risk designs cannot meet the approved outcome.

## Approved-feedback intake

Feedback is eligible for triage only when the customer has approved its use for product planning and the record contains a named contact, domain owner, problem statement, expected outcome, affected roles, requested evidence, tenant impact, data classifications, and known risks. Raw sales notes, model-generated suggestions, anonymous prompts, unverified support text, and feedback without approved use are not product requirements.

| Intake field | Required decision value |
|---|---|
| Customer approval | Consent/contract basis and permitted product-planning use. |
| Domain and owner | Finance, Risk, Data Product, or another named domain with accountable business owner. |
| Problem and outcome | Decision/support workflow, measurable value, and why existing tools do not suffice. |
| Evidence and policy | Required sources, quality/freshness context, classification, obligations, and human-review need. |
| Scope and tenancy | Requested scope, affected tenants, data-handling expectations, and least-privilege assessment. |
| Safety risks | Prompt injection, sensitive evidence leakage, over-automation, stale facts, or approval bypass. |
| Support model | User audience, support contact, documentation owner, and expected failure handling. |

## Review sequence

1. **Product triage:** accepts, defers, declines, or requests additional evidence. Product records the customer outcome rather than promising a tool.
2. **Governance review:** identifies domain owner, steward controls, authoritative evidence, lifecycle, and human-decision boundary.
3. **Security review:** assesses tenant isolation, OAuth scopes, classifications, evidence minimization, prompt-injection exposure, audit requirements, and misuse paths.
4. **Architecture review:** selects the smallest compatible extension and confirms versioning/deprecation impact.
5. **SDD change:** an accepted proposal receives a new change ID with requirements, design, threat model, contracts, tests, rollout, and evidence.
6. **Pilot:** an approved test tenant and named host validate the pack before any expansion.

## Domain-pack patterns

| Example domain | Prefer first | Human-control boundary |
|---|---|---|
| Finance controls | Certified-asset discovery facets, reconciliation-quality evidence, approved policy prompts, curation proposals. | Financial certification, material metadata edits, and exceptions remain steward/owner decisions. |
| Risk evidence | Lineage impact summaries, quality incidents, retention/classification evidence, policy decision support. | Risk acceptance, regulatory interpretation, and exposure decisions remain accountable human decisions. |
| Data Product publishing | Ownership/completeness evidence, consumer impact, domain glossary mapping, publishing-readiness proposal. | Publication status, SLA commitment, and consumer-facing contract changes require owner/steward confirmation. |

## Prohibited shortcuts

A domain pack must not introduce arbitrary SQL, arbitrary HTTP, secret retrieval, direct asset updates, automatic certification, automatic proposal approval/execution, raw-data export, or an unbounded “agent action” tool. Feedback does not alter policy rules or tenant entitlement by itself. Where a workflow changes governance state, the preferred mechanism is a typed proposal with immutable diff/evidence, steward inbox review, confirmation nonce, and execution-time rechecks.

## Decision record

| Field | Required record |
|---|---|
| Intake ID and approved feedback basis | Links to the consented feedback record without copying sensitive contents. |
| Decision | Accept, defer, decline, or request evidence. |
| Chosen pattern | Existing tool, prompt, resource, facet, evidence template, proposal type, or separately scoped new tool. |
| SDD change ID | Required for any implementation work. |
| Compatibility impact | Additive/behavioral/deprecation/breaking classification. |
| Owners and review dates | Product, governance, security, architecture, operations. |
| Pilot and exit evidence | Test tenant, host, ledger/support evidence, and approval outcome. |

## References

- [MCP partner certification](mcp-partner-certification.md)
- [MCP versioning and deprecation policy](mcp-versioning-and-deprecation-policy.md)
- [Proposal-only governance workflow evidence](../specs/changes/0003-proposal-only-governance-workflows/evidence.md)
