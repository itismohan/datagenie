# Threat Model: 0004-mcp-ecosystem-productization — MCP Ecosystem Productization

## Assets and trust boundaries

Protected assets are tenant-scoped governed metadata, policy evidence, approval workflows, request-correlation records, execution-ledger records, OAuth tokens, and customer feedback. Trust boundaries exist between the tenant administrator and authorization server, the enterprise host and gateway, helper libraries and host-owned credential stores, the certification harness and synthetic test environment, and approved feedback governance and product delivery.

| Threat | Mitigation | Verification |
|---|---|---|
| A tenant administrator over-requests scopes or configures an unapproved host. | Onboarding scope matrix uses least privilege; gateway tenant/host allowlists and token audience validation remain mandatory. | Certification validates a missing-scope denial; onboarding checklist requires documented host approval. |
| A helper becomes a proprietary bypass or arbitrary-write client. | Helpers use standard JSON-RPC `tools/call`, an allowlisted tool map, no token management, and local direct-mutation rejection. Gateway remains authoritative. | Unit tests reject direct-write names and assert standard request envelope construction. |
| Certification evidence leaks tokens, prompts, tenant data, or source credentials. | Harness uses deterministic synthetic identities/data and emits only assertions, statuses, tool names, request IDs, and ledger correlation facts. | Artifact content test rejects sensitive marker strings and requires synthetic tenant markers. |
| A host claims compatibility while ignoring scope, schema, or confirmation behavior. | Harness includes scope-denial, schema-rejection, proposal-only, and error-envelope checks. External certification requires approved evidence review. | Two synthetic profiles pass in CI; external submissions remain a release gate. |
| Support cannot investigate an agent result or asks for unsafe logs. | Onboarding pack defines request-ID-ledger workflow and safe intake fields. | Harness verifies a request ID maps to a tenant-bound ledger entry; documentation review checks prohibited data list. |
| Version changes break a certified host silently. | Versioning policy defines change classes, compatibility requirements, notice windows, deprecation markers, and retirement criteria. | Contract-policy test checks required published policy sections and semantic-version/tool-version references. |
| Raw customer feedback creates generic tools or policy changes. | Domain-pack policy requires consented, approved feedback and product/governance/security/architecture review under a new SDD change. | Documentation contract test asserts no automatic feedback or direct-write path is permitted. |
| A synthetic pass is misrepresented as a customer-host certification. | Evidence includes `certification_level: synthetic_preflight`; policy states external approval is separate. | Harness output test and release evidence distinguish synthetic and external certification. |

## Residual risk

Synthetic harness coverage cannot prove live OIDC interoperability, browser redirect behavior, enterprise network proxy compatibility, customer consent, or external-host user experience. These remain named staging and customer onboarding gates, with a kill switch and existing host/tenant allowlists available until the evidence is accepted.
