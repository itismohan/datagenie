# DataGenie Pull Request

## SDD declaration

Use exactly one declaration for material work. CI validates the change identifier against `specs/changes/`.

<!-- SDD_CHANGE_ID: 0001-example-change -->
<!-- SDD-EXEMPT: Documentation-only correction; no product, contract, security, data, or operational behavior changes. -->

**Declaration used:** `SDD_CHANGE_ID: ` or `SDD-EXEMPT: `

## Change summary

Describe the customer or operational outcome and link the approved proposal/requirements.

## Contract and compatibility impact

| Surface | Added / changed / removed | Contract version | Compatibility or deprecation plan |
|---|---|---|---|
| REST / OpenAPI | | | |
| Event / webhook | | | |
| MCP | | | |
| Data model / migration | | | |

## Tenant, security, and governance impact

| Concern | Assessment | Evidence |
|---|---|---|
| Tenant isolation | | |
| Authorization and policy | | |
| Secrets, privacy, and egress | | |
| Governance approval / AI assistance | | |
| Threat model reviewed | | |

## Delivery and operations

| Concern | Plan or evidence |
|---|---|
| Migration and rollback | |
| Feature flag / tenant rollout | |
| Metrics, alerts, and runbook | |
| Timeouts, retries, dead-letter, cancellation | |
| Support/on-call ownership | |

## Verification

List executed tests and validation evidence. Ensure the referenced change’s `traceability.yaml` maps each requirement to implementation, tests, contracts, and evidence.

- [ ] Requirements and non-goals reviewed.
- [ ] Relevant contracts and generated artifacts updated.
- [ ] Tenant-negative and authorization tests added or assessed.
- [ ] Migration and rollback behavior validated, if applicable.
- [ ] Security/dependency/secret checks pass.
- [ ] Documentation, rollout plan, and evidence updated.
