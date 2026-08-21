# Domain Specification: API Compatibility

**Status:** Backfilled baseline
**Owner:** Platform API
**Authoritative platform control:** [`specs/platform/api-compatibility.md`](../platform/api-compatibility.md)
**Constitution articles:** I, IV, V, VII, VIII, IX

## Intent

This domain defines the customer and integration compatibility boundary for DataGenie. It applies to the existing versioned REST/OpenAPI surfaces, webhooks/events and the planned MCP governed-discovery contract. It establishes that security, tenancy, error semantics and auditability are contract behavior, not optional client conventions.

## Mandatory controls

| Control | Domain rule | Current authoritative implementation/evidence |
|---|---|---|
| REST versioning | Public business endpoints remain under an explicit `/api/v1` contract until a reviewed major version transition. | `apps/catalog-api/app/main.py`, `docs/openapi/catalog-api-v1.json` |
| Machine-readable contract | OpenAPI exposes bearer authentication, reusable safe errors, request ID correlation and stable responses. | `apps/catalog-api/app/core/openapi.py`, `/api/openapi.json` |
| Contract-drift prevention | A generated, committed OpenAPI artifact must remain synchronized with executable behavior in CI. | Export/check scripts and catalog contract tests |
| Tenant-aware access | Documentation and every protected contract must reflect mandatory tenant-bound authorization and safe denial. | `apps/catalog-api/app/core/security.py`, `apps/catalog-api/app/db/session.py` |
| Evolving agent contract | MCP tools/resources/prompts have explicit schema, scopes, redaction, bounded outputs, compatibility versions and internal-host validation. | `specs/changes/0001-mcp-read-only-governed-discovery/contracts.md` |
| Event/webhook safety | Webhook payloads, delivery signing and schema/deprecation changes are versioned, auditable and replay-safe. | Catalog webhook worker and operations documentation |

## Compatibility decisions

Additive optional fields, operations and capability declarations may be introduced only when clients can safely ignore them. Changed authorization, altered field semantics/types, renamed/removed fields, error-envelope changes, altered ranking/pagination guarantees, changed event meaning or weakened redaction are breaking changes. A breaking change requires a new version or approved deprecation/migration plan, consumer communication, updated artifacts and release evidence.

MCP pilot schemas remain pre-stable (`0.x`) and limited to approved internal hosts. The pilot must not be presented as a general client contract until tenant-negative, security, interoperability and canary evidence meet the change exit criteria.

## Failure behavior

A response that cannot be safely authorized, correlated, bounded or evidenced must fail with a documented safe error rather than returning uncertain, stale or cross-tenant content. New consumers must never depend on undocumented framework defaults or use direct data-store access to avoid governed contract controls.

## Change governance

Any material REST, event/webhook or MCP contract change requires an SDD change ID, a contracts artifact, traceability to tests and release evidence. The authoritative controls and implementation references are maintained in the companion platform specification to avoid duplicate low-level policy definitions.
