# SDD Adoption Notes for DataGenie

## Authoritative and practical findings

A practical SDD workflow uses three core artifacts: a requirements document with user stories and acceptance criteria, a technical design covering architecture/data flow/error handling/testing, and discrete implementation tasks. This structure supports tracking, review, and execution in dependency-aware waves.[1]

GitHub's Spec Kit frames SDD as a shift from code-led work to specifications as the source of intent. Its workflow emphasizes iterative clarification, requirements-to-design traceability, technical research, contract and test derivation, continuous consistency checks, and production feedback returning to the specifications.[2]

OpenSpec is explicitly designed for brownfield adoption. Its lightweight change model separates proposal, requirement deltas, design, and tasks; it supports exploration before commitment, iterative edits to artifacts, and archive/reconciliation after implementation.[3]

## Implications for DataGenie

1. Do **not** retrofit a single large, static PRD. Start with an architecture baseline and adopt a change-spec workflow for all material behavior changes.
2. Use repository-native Markdown and machine-checkable YAML/JSON contracts. Keep the specification alongside the code and require change IDs in pull requests, commits, and audit releases.
3. Make DataGenie-specific non-negotiables part of a project constitution: tenant isolation, human approval for governance changes, external secret references, explainable quality, durable operations, OpenAPI/MCP contract compatibility, and evidence retention.
4. Treat tests, OpenAPI/MCP schemas, migration plans, observability requirements, and rollout/rollback evidence as specification deliverables, not after-the-fact implementation details.
5. Use MCP only after the SDD controls exist: MCP converts verified specifications into discoverable tools, resources, prompts, and approval-gated actions without exposing undocumented REST endpoints.

## References

[1]: https://kiro.dev/docs/specs/
[2]: https://github.com/github/spec-kit/blob/main/spec-driven.md
[3]: https://github.com/Fission-AI/OpenSpec
