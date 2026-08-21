# Design: {{CHANGE_ID}} — {{TITLE}}

**Status:** Draft | Approved
**Requirements:** [requirements.md](requirements.md)
**Constitution review:** Pass | Approved exception recorded

## Architecture summary

Describe the selected approach, the key decision, alternatives considered, and why the design satisfies the approved requirements with minimum complexity.

## Components and responsibilities

| Component | Responsibility | Inputs/outputs | Tenant and authorization boundary |
|---|---|---|---|
| {{COMPONENT}} | {{RESPONSIBILITY}} | {{IO}} | {{BOUNDARY}} |

## Data flow and sequence

```mermaid
sequenceDiagram
    participant Actor
    participant Edge as API / MCP Gateway
    participant Policy as Policy Decision
    participant Domain as Domain Service
    participant Store as Tenant-Scoped Store
    Actor->>Edge: Authenticated request
    Edge->>Policy: Evaluate subject, tenant, action, resource, purpose
    Policy-->>Edge: Decision and obligations
    Edge->>Domain: Tenant-bound operation
    Domain->>Store: Scoped read/write
    Store-->>Domain: Result
    Domain-->>Edge: Evidence-bearing response
    Edge-->>Actor: Correlated response
```

## Data model and state transitions

Document new or changed entities, ownership, tenant keys, lifecycle state machine, indexes, constraints, migrations, and retention expectations. Link detailed entities in `data-model.md` when needed.

## API, event, and MCP contracts

| Contract | Version | Added / changed / removed behavior | Compatibility decision |
|---|---|---|---|
| {{CONTRACT}} | {{VERSION}} | {{CHANGE}} | {{DECISION}} |

Link formal schemas in `contracts/`. For MCP, define resource URI/version, prompt arguments, tool input/output, scopes, side effects, confirmation, idempotency, timeout, result bounds, and audit event.

## Failure, recovery, and operational behavior

| Condition | Expected behavior | Retry/cancel/dead-letter handling | Operator signal |
|---|---|---|---|
| {{FAILURE_MODE}} | {{BEHAVIOR}} | {{RECOVERY}} | {{METRIC_ALERT_RUNBOOK}} |

## Security and privacy design

Describe identity, tenant context propagation, roles/scopes, classification/redaction, secrets, egress, rate limits, threat-model controls, logging exclusions, and audit evidence. Link `threat-model.md`.

## Test strategy

State the unit, contract, integration, tenant-negative, authorization, migration, failure, adversarial, performance, and rollout tests needed to prove every requirement.

## Architecture decisions and exceptions

Record important alternatives, trade-offs, approved constitution exceptions, owner, expiry, and removal task.
