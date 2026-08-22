# Evidence: 0004-mcp-ecosystem-productization — MCP Ecosystem Productization

**Status:** Implementation validated locally; staging and external-host approvals pending.
**Release revision:** Pending commit
**Evidence owner:** Platform developer experience owner (TBD)

## Requirement completion

| Requirement ID | Implementation reference | Test evidence | Contract evidence | Reviewer | Status |
|---|---|---|---|---|---|
| DG-MCP-PRODUCT-001 | `docs/mcp-tenant-admin-onboarding.md` | `pytest -q tools/tests/test_mcp_productization.py` | Onboarding pack | 2026-08-22 | Passed locally |
| DG-MCP-PRODUCT-002 | `docs/mcp-versioning-and-deprecation-policy.md` | `pytest -q tools/tests/test_mcp_productization.py` | Lifecycle policy | 2026-08-22 | Passed locally |
| DG-MCP-PRODUCT-003 | `clients/python/`, `clients/typescript/` | Python contract test and `npx --no-install tsc --project tsconfig.json` | Helper request contract | 2026-08-22 | Passed locally |
| DG-MCP-PRODUCT-004 | `tools/run_mcp_partner_certification.py` | Synthetic certification harness | Certification artifact contract | 2026-08-22 | Passed locally |
| DG-MCP-PRODUCT-005 | Certification host profiles | `generic-streamable-http` and `enterprise-governed-host` synthetic profiles | Certification guide | 2026-08-22 | Passed locally; external-host evidence pending |
| DG-MCP-PRODUCT-006 | Onboarding support procedure and ledger check | Harness request-to-ledger assertion | Support workflow | 2026-08-22 | Passed locally; support dry run pending |
| DG-MCP-PRODUCT-007 | `docs/mcp-domain-pack-governance.md` | `pytest -q tools/tests/test_mcp_productization.py` | Domain-pack intake contract | 2026-08-22 | Passed locally |

## Security and tenant evidence

Synthetic preflight must verify the constrained helper allowlist, scope denial, malformed input rejection, direct-mutation rejection, no sensitive values in evidence, request-ID correlation, and tenant-bound ledger entries. Live OIDC, customer tenants, customer hosts, and production feedback are not permitted in local evidence.

## Operational evidence

Local evidence recorded: productization contract tests passed; catalog suite passed (50 tests); MCP gateway suite passed (17 tests); synthetic partner certification and refreshed synthetic canary passed; TypeScript static compilation passed; SDD validation passed. Before customer onboarding, record the staging OIDC walkthrough, tenant-admin walkthrough, support investigation dry run, two external-host certification submissions, dashboard result, ledger durability check, and on-call handoff.

## Contract and compatibility evidence

The published lifecycle policy, onboarding pack, helper source, tool catalog, and synthetic artifact must be reviewed together. Any contract change after a host is certified follows the deprecation process; no compatibility exception is active at this time.

## Constitution exceptions

| Article | Scope | Risk | Compensating control | Owner | Expiry | Removal task |
|---|---|---|---|---|---|---|
| None | N/A | N/A | N/A | N/A | N/A | N/A |

## Final approval

| Decision | Approver | Date | Notes |
|---|---|---|---|
| Product | TBD | TBD | Pending customer onboarding owner |
| Architecture | TBD | TBD | Pending implementation review |
| Security | TBD | TBD | Pending staging and external-host evidence |
| Operations | TBD | TBD | Pending support dry run and on-call handoff |
