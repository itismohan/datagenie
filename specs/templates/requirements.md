# Requirements: {{CHANGE_ID}} — {{TITLE}}

**Status:** Draft | Approved
**Source proposal:** [proposal.md](proposal.md)
**Domain specification:** {{DOMAIN_SPEC}}

## Requirement-writing rules

Use stable identifiers in the form `DG-{{DOMAIN}}-###`. Each requirement SHALL describe externally observable behavior, SHALL be testable, and SHALL include at least one acceptance scenario. Mark uncertainty explicitly; do not hide assumptions in implementation language.

## User stories

### User story: {{STORY_TITLE}}

As a {{ACTOR}}, I want {{CAPABILITY}} so that {{OUTCOME}}.

### Functional requirements

#### Requirement: DG-{{DOMAIN}}-001 — {{REQUIREMENT_NAME}}

The system SHALL {{TESTABLE_BEHAVIOR}}.

**Rationale:** {{WHY_THIS_MATTERS}}

**Authorization and tenant boundary:** {{WHO_IS_ALLOWED_AND_HOW_TENANT_IS_BOUND}}

**Evidence and audit expectation:** {{WHAT_EVIDENCE_MUST_BE_RETAINED}}

##### Acceptance scenario: {{SCENARIO_NAME}}

- **GIVEN** {{PRECONDITION}}
- **WHEN** {{ACTION}}
- **THEN** {{OBSERVABLE_OUTCOME}}
- **AND** {{EVIDENCE_OR_AUDIT_OUTCOME}}

##### Negative scenario: {{DENIAL_OR_FAILURE_NAME}}

- **GIVEN** {{UNAUTHORIZED_OR_INVALID_PRECONDITION}}
- **WHEN** {{ACTION}}
- **THEN** {{SAFE_DENIAL_OR_FAILURE}}
- **AND** no cross-tenant data or secret is disclosed.

## Non-functional requirements

| ID | Requirement | Acceptance measure |
|---|---|---|
| DG-NFR-001 | Security and tenancy | {{MEASURE}} |
| DG-NFR-002 | Reliability and recovery | {{MEASURE}} |
| DG-NFR-003 | Performance and bounds | {{MEASURE}} |
| DG-NFR-004 | Observability and supportability | {{MEASURE}} |
| DG-NFR-005 | Compatibility and documentation | {{MEASURE}} |

## Explicit non-goals

List behavior that this change SHALL NOT provide. These are guardrails against accidental scope growth.

## Requirement traceability

Each requirement ID must appear in `traceability.yaml`, with implementation, contract, test, and evidence mappings before the change can be complete.
