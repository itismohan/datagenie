# Evidence: {{CHANGE_ID}} — {{TITLE}}

**Status:** In progress | Complete
**Release revision:** {{GIT_SHA}}
**Evidence owner:** {{OWNER}}

## Requirement completion

| Requirement ID | Implementation reference | Test evidence | Contract evidence | Reviewer | Status |
|---|---|---|---|---|---|
| DG-{{DOMAIN}}-001 | {{PATH_OR_COMMIT}} | {{CI_JOB_OR_TEST}} | {{ARTIFACT}} | {{NAME}} | Pass / exception |

## Security and tenant evidence

Record security scan, dependency scan, secret scan, RBAC/policy matrix, tenant-negative tests, threat-model review, and any exceptions.

## Operational evidence

Record migration validation, backup/restore or recovery drill, worker failure/replay behavior, observability/alert checks, performance evidence, staging/canary outcome, and on-call handoff.

## Contract and compatibility evidence

Record OpenAPI/MCP/event/schema diffs, consumer compatibility review, documentation publication, and deprecation notices if relevant.

## Constitution exceptions

| Article | Scope | Risk | Compensating control | Owner | Expiry | Removal task |
|---|---|---|---|---|---|---|
| {{ARTICLE}} | {{SCOPE}} | {{RISK}} | {{CONTROL}} | {{OWNER}} | {{DATE}} | {{TASK}} |

## Final approval

| Decision | Approver | Date | Notes |
|---|---|---|---|
| Product | {{NAME}} | {{DATE}} | {{NOTES}} |
| Architecture | {{NAME}} | {{DATE}} | {{NOTES}} |
| Security | {{NAME}} | {{DATE}} | {{NOTES}} |
| Operations | {{NAME}} | {{DATE}} | {{NOTES}} |
