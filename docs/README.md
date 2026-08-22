# DataGenie Documentation Index

This directory contains the maintained engineering, operations, integration, and governance guidance for DataGenie. It is organized by the decision a reader needs to make, while completed SDD change records remain in [`../specs/changes/`](../specs/changes/) as implementation and release history.

> **Reading guide:** The current release posture is a controlled multi-tenant staging canary, not general availability. Treat the [launch-readiness assessment](launch-readiness-assessment.md) and [production release architecture](production-release-architecture.md) as the authoritative documents for launch conditions.[1] [2]

## Start with your objective

| Reader and objective | Recommended reading | Outcome |
|---|---|---|
| Product, data steward, or analyst: understand governed discovery and lineage | [Governed discovery guide](governance-discovery-guide.md) | Understand catalog, glossary, classification, certification, quality, lineage, and steward workflow. |
| API consumer: build a REST integration | [API integration guide](api-integration-guide.md) | Use versioning, pagination, tenant auth, request IDs, idempotency, errors, and OpenAPI correctly. |
| Tenant administrator: enable MCP safely | [MCP tenant-admin onboarding](mcp-tenant-admin-onboarding.md) | Register an OAuth/OIDC client, scope it minimally, use a test tenant, and perform the request-ID support dry run. |
| Enterprise host team: certify an MCP integration | [MCP partner certification](mcp-partner-certification.md) | Complete synthetic, test-tenant, and approved-partner evidence requirements. |
| Operator or SRE: run the platform | [Production operations](production-operations.md) · [Operations runbook](operations-runbook.md) | Start the platform, monitor it, investigate incidents, and run backup/restore or rollback procedures. |
| Release owner: assess readiness | [Launch-readiness assessment](launch-readiness-assessment.md) · [Release architecture](production-release-architecture.md) | Separate implemented controls from evidence that must exist before broader enablement. |
| Engineer: plan a material change | [SDD workflow](../specs/README.md) · [Engineering constitution](../specs/constitution.md) | Create an approved, traceable change specification before implementation. |

## Product and platform guides

| Document | Scope |
|---|---|
| [Catalog MVP contract](catalog-mvp-contract.md) | Catalog domain and its durable behaviors. |
| [Catalog MVP implementation guide](catalog-mvp-implementation.md) | Catalog workflows and implementation decisions. |
| [Connector framework contract](connector-framework-contract.md) | PostgreSQL and Snowflake connector contract. |
| [Connector framework guide](connector-framework-guide.md) | Connector configuration, synchronization, failure handling, and job history. |
| [Quality foundation contract](quality-foundation-contract.md) | Explainable quality model and deterministic rules. |
| [Quality operations](quality-operations.md) | Quality incidents, runs, remediation, and operator procedures. |
| [Governance and lineage contract](governance-lineage-contract.md) | Governed discovery, operational lineage, and impact model. |
| [RBAC and audit contract](rbac-audit-contract.md) · [RBAC and audit guide](rbac-audit-guide.md) | Access roles, audit boundaries, and operational use. |

## MCP integration and governance

| Document | Scope |
|---|---|
| [MCP authorization reference](mcp-authorization-reference.md) | OAuth/OIDC resource-server behavior, tenant binding, scopes, transport, and ledger controls. |
| [MCP tenant-admin onboarding](mcp-tenant-admin-onboarding.md) | Safe customer administrator onboarding and support-correlation procedure. |
| [MCP partner certification](mcp-partner-certification.md) | Host certification criteria and evidence expectations. |
| [MCP versioning and deprecation policy](mcp-versioning-and-deprecation-policy.md) | Contract versioning, compatibility, and deprecation lifecycle. |
| [MCP domain-pack governance](mcp-domain-pack-governance.md) | Controlled evolution through approved domain packs. |
| [MCP internal canary runbook](mcp-internal-canary-runbook.md) · [MCP beta operations dashboard](mcp-beta-operations-dashboard.md) | Internal release monitoring and operational control. |

The MCP surface is proposal-only for governed change: agents and hosts can create intent with evidence, but steward review and server-bound confirmation remain the only approval/execution route.[3] [4]

## Operations, release, and customer trust

| Document | Scope |
|---|---|
| [Production hardening contract](production-hardening-contract.md) | Required platform hardening baseline. |
| [Production operations](production-operations.md) | Environment model, local startup, auth, probes, backups, and promotion sequence. |
| [Operations runbook](operations-runbook.md) | Incident response and recovery procedures. |
| [Production release architecture](production-release-architecture.md) | Tenant, worker, search, ingress, and rollout controls plus evidence gates. |
| [Launch-readiness assessment](launch-readiness-assessment.md) | Current implementation assessment and remaining launch conditions. |

## Research and historical context

The [`research/`](research/) notes record directional investigation. They are not current product commitments. Completed SDD artifacts under [`../specs/changes/`](../specs/changes/) remain valuable for traceability; consult their durable domain and platform specifications before treating an older decision as current policy.

## Documentation maintenance

Treat a document as a maintained contract when it guides integration, security, operations, release, or governance decisions. Update it in the same change as the affected behavior. For material changes, use the templates and traceability requirements in [`../specs/`](../specs/README.md); for a text-only correction, apply the SDD exemption process described there.[5]

## References

[1]: launch-readiness-assessment.md "DataGenie Launch-Readiness Assessment"
[2]: production-release-architecture.md "DataGenie Production Release Architecture"
[3]: mcp-authorization-reference.md "MCP Authorization and Streamable HTTP Implementation Reference"
[4]: mcp-tenant-admin-onboarding.md "DataGenie MCP Tenant-Admin Onboarding Pack"
[5]: ../specs/README.md "DataGenie Specification-Driven Development"
