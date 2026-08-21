# DataGenie Engineering Constitution

**Status:** Active
**Version:** 1.0.0
**Applies to:** Every material product, platform, API, data-model, connector, MCP, operational, and AI-assistance change in this repository.

## Purpose

This constitution makes DataGenie’s product promises enforceable engineering constraints. Specifications are the primary record of intended behavior; code, infrastructure, tests, contracts, and operational evidence are the implementations of those specifications. A change may not claim completion until its requirements, evidence, and release effects can be traced.

> When an implementation conflicts with this constitution, the implementation changes unless an approved, time-bounded exception explicitly records why the constitution cannot yet be met.

## Article I — Tenant isolation by design

Every request, job, persistence operation, cache entry, search result, export, audit event, webhook, and MCP invocation SHALL be bound to a tenant identity derived from validated authentication or trusted service context. Callers SHALL NOT select or override a tenant by request argument. Cross-tenant reads, writes, inference, cache reuse, and identifier lookup are prohibited and require negative regression coverage.

## Article II — Human authority for governance

AI systems and automation MAY draft, classify, recommend, summarize, or create proposals. They SHALL NOT autonomously apply governance-impacting changes, including ownership, classification, glossary approval, certification, retention, policy, or data-use decisions. A qualified human approval, revalidated at execution time, is required before state changes occur.

## Article III — Evidence before authority

Any quality, classification, certification, lineage, policy, trust, or recommendation result presented as decision support SHALL identify its evidence, provenance, version, timestamp, confidence where applicable, and responsible owner. Opaque scores and ungrounded conclusions SHALL be labeled as non-authoritative and SHALL NOT trigger governance mutations.

## Article IV — Contract-first compatibility

Public REST, event, data, database migration, and MCP interfaces SHALL be specified before implementation. Specifications SHALL include schemas, authorization, errors, idempotency, pagination or bounds, versioning, and compatibility behavior. Breaking changes require a new major contract or an approved migration and deprecation plan.

## Article V — Least capability and least privilege

Every role, connector, worker, service, API endpoint, MCP resource, prompt, and tool SHALL have an explicit minimum capability. MCP tools require a declared side-effect class, scopes, input/output schema, data classification, timeout, rate limit, idempotency behavior, audit event, and confirmation requirement. Generic unrestricted database, HTTP, secret, or administrative execution interfaces are prohibited.

## Article VI — Durable, recoverable operations

Any work that can outlive a request or fail independently of a caller SHALL use a durable job model with identity, tenant context, idempotency, deadline, cancellation, retry policy, dead-letter behavior, replay controls, history, and operator visibility. API processes SHALL NOT be the sole execution boundary for harvesting, profiling, reindexing, exports, webhook delivery, or material graph work.

## Article VII — Secure composition

Raw credentials SHALL NOT be persisted or exposed through product APIs. External secret references, TLS, authenticated service boundaries, scoped tokens, audience validation, dependency scanning, input validation, egress controls, and explicit trust boundaries are mandatory for production paths. Tokens SHALL NOT be forwarded to downstream services unless they are explicitly issued for that service and the design documents the validation boundary.

## Article VIII — Observable decisions and operations

Every externally meaningful action SHALL be traceable using a correlation identifier. Logs, metrics, audit events, policy decisions, job state transitions, approval events, tool invocations, and outbound effects SHALL be sufficient to explain who or what initiated an outcome, within which tenant, under which authorization/policy decision, using which versioned evidence.

## Article IX — Specification traceability and release evidence

Every material change SHALL have a change identifier and versioned artifacts for requirements, design, threat model, contracts, test plan, rollout/rollback plan, and evidence. Each accepted requirement SHALL map to implementation, automated test coverage, and release evidence. Production incidents, security findings, and operational failures SHALL update either a domain specification, a non-functional requirement, or a regression scenario.

## Compliance and exceptions

A pull request that changes behavior, public contracts, security, data models, migrations, workflow state, infrastructure, or operations SHALL reference an active change specification. Small documentation-only and mechanical dependency updates may use the documented exemption path in `specs/README.md`.

Exceptions require an entry in the affected change’s `evidence.md` with: the violated article, scope, owner, risk, compensating control, expiry date, and a removal task. Expired exceptions are release blockers.
