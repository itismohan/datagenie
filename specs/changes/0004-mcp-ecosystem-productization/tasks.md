# Tasks: 0004-mcp-ecosystem-productization — MCP Ecosystem Productization

**Change ID:** 0004-mcp-ecosystem-productization

| Task | Outcome | Requirement coverage | Status |
|---|---|---|---|
| 1. Publish tenant-admin onboarding pack | OAuth, scope, host, test-tenant, data-handling, support, and troubleshooting instructions. | DG-MCP-PRODUCT-001, 006 | Complete locally |
| 2. Publish lifecycle policy | MCP compatibility, versioning, deprecation, notice, migration, and retirement process. | DG-MCP-PRODUCT-002 | Complete locally |
| 3. Create constrained helpers | Optional Python and TypeScript standard JSON-RPC helpers with local allowlist guards. | DG-MCP-PRODUCT-003 | Complete locally |
| 4. Implement certification harness | Two-profile synthetic test, auth/scope/schema/proposal/error/request/ledger checks, and sanitized evidence artifact. | DG-MCP-PRODUCT-004, 005, 006 | Complete locally |
| 5. Define domain-pack governance | Approved-feedback intake, decision record, review sequence, and bounded delivery template. | DG-MCP-PRODUCT-007 | Complete locally |
| 6. Refresh existing synthetic canary | Update stale four-tool assumption to the seven-tool proposal-intent surface. | DG-MCP-PRODUCT-004 | Complete locally |
| 7. Validate and publish | Run helper/harness tests, existing gateway regression, SDD validator, documentation check, commit, and push. | All | Validated; publication pending |

## Release gate

Do not enable customer onboarding from this implementation alone. Capture two distinct approved external-host certification submissions, a staging tenant-admin walkthrough, and a request-ID-to-ledger support dry run before promoting beyond the existing internal beta.
