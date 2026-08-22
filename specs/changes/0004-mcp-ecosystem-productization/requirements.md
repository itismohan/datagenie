# Requirements: 0004-mcp-ecosystem-productization — MCP Ecosystem Productization

## Functional requirements

| ID | Requirement | Acceptance criteria |
|---|---|---|
| DG-MCP-PRODUCT-001 | The platform SHALL publish a tenant-admin onboarding pack that explains OAuth registration, least-privilege scope selection, compatible hosts, test-tenant configuration, data handling, and support escalation. | A new administrator can complete the documented preflight without relying on unpublished configuration or a production credential. |
| DG-MCP-PRODUCT-002 | The platform SHALL publish an MCP versioning and deprecation policy that classifies additive, behavioral, deprecated, and breaking changes and defines communication, compatibility, and retirement expectations. | The policy identifies the protocol/version fields, tool-schema compatibility rules, notice channels, and support window owner. |
| DG-MCP-PRODUCT-003 | The platform SHALL provide optional constrained Python and TypeScript reference helpers that use standard Streamable HTTP JSON-RPC and expose only the documented discovery and proposal-intent tools. | The helpers preserve caller-controlled OAuth bearer-token acquisition, reject unknown/direct-mutation tool names locally, preserve request IDs, and have no approval or execution operation. |
| DG-MCP-PRODUCT-004 | The platform SHALL provide a partner certification harness that checks protected-resource discovery, authentication, scope denial, schema rejection, structured results, proposal-only confirmation boundaries, error envelopes, request correlation, and ledger correlation. | The harness emits a machine-readable pass/fail artifact containing no credentials, raw prompts, raw results, or source secrets. |
| DG-MCP-PRODUCT-005 | The certification harness SHALL exercise at least two named interoperable host profiles against the same standards-compliant MCP endpoint. | Both profiles complete initialization and allowed tool calls; the artifact distinguishes synthetic profile validation from external-partner certification. |
| DG-MCP-PRODUCT-006 | Support SHALL be able to investigate a certified tool result from its request ID through a minimized tenant-scoped execution-ledger entry and published troubleshooting procedure. | The onboarding pack documents request-ID capture, safe evidence collection, and escalation fields; the harness asserts request-ID-to-ledger correlation. |
| DG-MCP-PRODUCT-007 | New domain packs SHALL enter the product only through approved customer feedback, evidence review, security review, SDD change control, and bounded tool/proposal design. | The domain-pack policy prohibits automatic feedback ingestion and generic direct-write tools. |

## Safety and compatibility constraints

The helper and certification surface shall not mint, persist, log, or transmit bearer tokens except as the caller supplies them to the configured TLS endpoint. Test evidence shall use synthetic tenant IDs, host IDs, assets, and evidence references only. No helper, harness, onboarding instruction, or domain pack may bypass DataGenie’s tenant binding, shared policy evaluator, steward inbox, confirmation nonce, or execution-time rechecks.

## Exit gate

Two approved distinct external host certification submissions, a tenant-admin self-onboarding walkthrough, and a support request-ID-to-ledger investigation dry run must pass before enabling customer onboarding. Synthetic two-profile results are necessary preflight evidence but do not satisfy the external-host portion of this gate.
