# Change Proposal: 0004-mcp-ecosystem-productization — MCP Ecosystem Productization

**Status:** Draft
**Owner:** DataGenie platform, product, security, and developer experience teams
**Related changes:** `0001-mcp-read-only-governed-discovery`, `0002-internal-policy-decision-interface`, `0003-proposal-only-governance-workflows`

## Problem

The governed MCP gateway has a controlled internal-beta surface, but a tenant administrator cannot yet self-onboard a compatible host using a complete published pack. Host integrators also lack a stable lifecycle commitment, constrained reference helpers, and a repeatable certification result that support can correlate to gateway evidence. Adding generic MCP tools would increase the bypass and support surface rather than improving product readiness.

## Proposed outcome

Publish a tenant-admin onboarding pack, an MCP versioning and deprecation policy, constrained Python and TypeScript helpers, and a local partner-certification harness. The deliverables preserve standard Streamable HTTP JSON-RPC interoperability: helpers are optional convenience layers, not a proprietary transport or authorization path.

The certification harness validates protected-resource discovery, authentication, tenant and scope handling, tool schema conformance, proposal-only confirmation boundaries, structured error behavior, request-ID propagation, and durable execution-ledger correlation. It operates only against synthetic test data and a named test tenant configuration.

## Scope

| Included | Explicitly excluded |
|---|---|
| Tenant-admin onboarding, OAuth registration checklist, scope matrix, host compatibility matrix, test-tenant controls, data-handling expectations, and support workflow | Customer production enablement, automatic partner approval, or replacement of the existing authorization server |
| Formal MCP compatibility, versioning, and deprecation policy aligned with the repository OpenAPI practice | A proprietary MCP protocol fork or a generic write-tool marketplace |
| Optional constrained Python and TypeScript helpers for the documented tool surface | Credential storage, token minting, arbitrary JSON-RPC dispatch, automatic proposal approval, or proposal execution |
| Synthetic partner certification harness with machine-readable evidence and two host profiles | A claim that two external customer hosts are certified before their approved results are submitted |
| Governance process for approved customer feedback and bounded domain-pack intake | Unreviewed generic domain tools or automatic product changes from raw feedback |

## Success criteria

A tenant administrator can use the onboarding pack to register an OAuth application, choose least-privilege scopes, verify host compatibility, use a test tenant safely, and open a support case with a request ID. A partner can run the certification harness with either supported synthetic host profile and receive evidence that links a request ID to an execution-ledger record. The helper surface cannot invoke direct governance mutation, approval, or execution operations.

## Release decision

This change is documentation and developer-experience infrastructure for the internal MCP beta. Customer onboarding remains disabled until the staging rehearsal, two approved distinct-host certification submissions, tenant-admin walkthrough, support dry run, and named product, security, and operations approvals are recorded in `evidence.md`.
