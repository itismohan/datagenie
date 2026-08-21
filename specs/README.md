# DataGenie Specification-Driven Development

## Purpose

This directory is the version-controlled source of truth for DataGenie product intent, architecture decisions, contracts, test expectations, rollout planning, and release evidence. The [engineering constitution](constitution.md) is mandatory for all material changes.

## Directory structure

| Path | Purpose |
|---|---|
| `constitution.md` | Non-negotiable engineering and governance invariants. |
| `platform/` | Cross-cutting specifications, such as tenancy and governance approval. |
| `domains/` | Durable domain specifications for catalog, quality, lineage, discovery, and customer operations. |
| `contracts/` | Canonical OpenAPI, event, MCP, and data-contract artifacts. |
| `changes/` | Active, scoped change specifications. |
| `archive/` | Completed change specifications retained as decision and release history. |
| `templates/` | Required starting templates for change artifacts. |
| `schemas/` | Machine-readable schemas used by CI validation. |

## Required workflow

1. **Explore:** Inspect the affected domain specification and current implementation before deciding scope.
2. **Propose:** Create `specs/changes/NNNN-slug/` from the templates. Write the customer/problem proposal and explicit non-goals.
3. **Specify:** Add testable requirements, design, threat model, contracts, test plan, rollout plan, `traceability.yaml`, and evidence skeleton.
4. **Review:** Product, architecture, security, governance, and operations owners approve the artifacts appropriate to the change risk.
5. **Implement:** Code only against an approved change specification. Update the traceability manifest as paths/tests/contracts become concrete.
6. **Verify:** Run the defined tests, compatibility checks, tenant-negative tests, migration checks, and operational validation. Record results in `evidence.md`.
7. **Release and archive:** Complete rollout evidence, update durable domain specifications, and archive the completed change when the release is stable.

## Material change rule

A change specification is required for new or modified user-visible behavior, API/event/MCP contracts, data models/migrations, authorization or tenant logic, governance workflow, AI assistance, workers/jobs, connector behavior, infrastructure, observability, retention/export/webhook behavior, or security controls.

The following may use the exemption path: spelling/format-only changes, non-behavioral documentation corrections, test-fixture-only corrections, and mechanical dependency updates that do not alter resolved runtime behavior. The pull request must state `SDD-EXEMPT` and explain why no material behavior changes.

## Change identifiers

Use `NNNN-lowercase-kebab-case`, beginning at `0001`. Requirement IDs use `DG-DOMAIN-###`, for example `DG-MCP-READ-001`. A pull request, commit series, release note, and evidence artifact must all reference the relevant change ID.

## Definition of done

A change is complete only when every requirement in `traceability.yaml` maps to implementation, one or more tests, and release evidence. Required contracts and documentation must be synchronized, constitution exceptions must be explicit and unexpired, and the approved rollout evidence must be recorded.
