# Contracts: 0003-proposal-only-governance-workflows

## REST endpoints

| Endpoint | Caller | Contract |
|---|---|---|
| `POST /api/v1/governance/proposals` | UI/API | Creates an idempotent API-originated proposal. Requires `Idempotency-Key`; derives actor and tenant from validated identity. Rejects `source.channel=mcp`. |
| `POST /api/v1/internal/mcp/proposals` | Signed MCP gateway only | Creates an MCP-originated proposal after validating the HMAC actor packet. Derives tenant, actor, and host from that packet; no public header may supply host identity. |
| `GET /api/v1/governance/proposals` | Steward or initiator | Returns tenant-scoped inbox rows, filterable by status/type. |
| `GET /api/v1/governance/proposals/{id}` | Authorized tenant user | Returns complete safe review record without nonce digest. |
| `POST /api/v1/governance/proposals/{id}/approve` | Data steward/platform administrator | Approves a pending proposal and returns one confirmation nonce, approval version, proposal hash, and nonce expiry. |
| `POST /api/v1/governance/proposals/{id}/reject` | Data steward/platform administrator | Rejects a pending proposal with a required review note. |
| `POST /api/v1/governance/proposals/{id}/cancel` | Initiator or eligible steward | Cancels a nonterminal proposal. |
| `POST /api/v1/governance/proposals/{id}/execute` | The approving steward | Requires exact `proposal_hash` and `confirmation_nonce`; re-checks all authorization and versions before typed execution. |
| `GET /api/v1/governance/inbox` | Steward | Returns the HTML approval inbox page. |

## Proposal creation body

```json
{
  "proposal_type": "asset_curation",
  "title": "Add approved business description to payments table",
  "proposal_text": "Proposed curation based on approved glossary evidence.",
  "resource": {"resource_type": "asset", "resource_id": "asset-123"},
  "purpose": "metadata stewardship",
  "diff": {"description": "Daily payment settlement facts", "tags": ["finance", "payments"]},
  "evidence": [{"type": "glossary_term", "reference": "term:payments-settlement"}],
  "impact": {"summary": "Improves discovery metadata only", "risk_level": "low"},
  "version_preconditions": {"technical_version": 7},
  "source": {"channel": "mcp", "model_id": "approved-model", "agent_id": "agent-session"}
}
```

The public endpoint accepts only `source.channel=api`. The signed private MCP endpoint requires `source.channel=mcp` and binds the initiating host from its verified actor packet. Both endpoints ignore caller-supplied tenant, actor, policy outcome, approval status, nonce, execution state, or audit relation. Unsupported fields are rejected.

## Response shape

```json
{
  "id": "proposal-uuid",
  "status": "pending_review",
  "proposal_hash": "sha256-hex",
  "expires_at": "2026-08-22T12:00:00Z",
  "policy_snapshot": {"outcome": "allow", "decision_version": "1.0.0", "rule_ids": ["DG-POLICY-..."], "evidence": [], "obligations": []},
  "source_channel": "mcp",
  "initiating_subject": "agent-user@example.com",
  "initiating_host_id": "approved-host",
  "initiating_model_id": "approved-model",
  "inbox_uri": "/api/v1/governance/inbox?proposal_id=proposal-uuid"
}
```

## Approval and execution body

```json
// approve
{"review_note": "Evidence and impact reviewed; approved for execution."}

// execute
{"proposal_hash": "sha256-hex", "confirmation_nonce": "single-use-secret"}
```

`approve` returns the nonce once. All later proposal reads omit it. The execute caller must be the current approving human steward; an MCP host cannot execute a proposal.

## MCP tools

| Tool | Required scope | Result |
|---|---|---|
| `create_governance_proposal` | `governance:propose` | Structured proposal ID/hash/status/expiry, policy/evidence, impact, source identity, and inbox URI. |
| `request_certification_review` | `governance:propose` | Creates a `certification_review_request` proposal only. |
| `schedule_quality_check` | `governance:propose` | Creates a `quality_check_schedule` proposal only. |

Every MCP tool returns a structured result containing provenance, evidence, timestamp, policy, obligations, confidence, proposal status, proposal hash, expiry, and inbox URI. No tool returns an approval nonce or executes a proposal.

## Error contract

Errors use the existing `error.code`, `error.message`, and request ID shape. Safe proposal-specific codes include `proposal_not_found`, `proposal_not_pending`, `proposal_expired`, `proposal_cancelled`, `proposal_hash_mismatch`, `confirmation_nonce_invalid`, `confirmation_nonce_expired`, `proposal_precondition_failed`, `proposal_reauthorization_denied`, `proposal_execution_blocked`, `idempotency_conflict`, and `proposal_audit_unavailable`.
