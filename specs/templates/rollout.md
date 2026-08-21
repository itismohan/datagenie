# Rollout Plan: {{CHANGE_ID}} — {{TITLE}}

**Status:** Draft | Approved | Executed
**Release owner:** {{RELEASE_OWNER}}
**On-call owner:** {{ONCALL_OWNER}}

## Release strategy

Describe feature flags, tenant/host allowlist, migration order, deployment stages, compatibility window, customer communication, and go/no-go owners.

| Stage | Audience | Enablement control | Entry criteria | Exit criteria |
|---|---|---|---|---|
| Local/CI | Engineering | Test configuration | Contract and test plan approved | Automated checks pass |
| Staging | Internal | Environment flag | Migration and operational checks pass | Canary evidence complete |
| Canary | Named tenant/host | Tenant/tool flag | Security and support sign-off | SLOs and audit sample pass |
| General availability | Eligible customers | Default enabled | Canary exit criteria pass | Steady-state SLOs held |

## Migration and compatibility

Document forward migration, data backfill, idempotency, schema/version compatibility, rollback safety, and customer-visible changes. Database migrations must be forward-safe; application rollback assumptions must be explicit.

## Observability and success criteria

| Signal | Expected range | Alert threshold | Dashboard/runbook |
|---|---|---|---|
| {{METRIC}} | {{EXPECTED}} | {{ALERT}} | {{LINK}} |

## Rollback and kill switch

| Trigger | Immediate action | Data remediation | Communication owner |
|---|---|---|---|
| Security/tenant breach suspicion | Disable tenant/tool/feature flag; preserve evidence | {{ACTION}} | {{OWNER}} |
| Error/SLO breach | {{ACTION}} | {{ACTION}} | {{OWNER}} |
| Migration failure | {{ACTION}} | {{ACTION}} | {{OWNER}} |

## Release evidence

Link staging validation, canary metrics, audit samples, support readiness, approval records, final release revision, and post-release verification.
