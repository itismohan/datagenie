# DataGenie MCP Partner Certification

## Purpose

Partner certification verifies that an enterprise host interoperates safely with the documented DataGenie MCP contract. It is **not** an authorization grant, production approval, security attestation, or substitute for tenant-admin onboarding. A successful synthetic preflight validates the harness against representative host profiles; an external partner is certified only when its approved submission, staging result, and named reviews are accepted.

## Certification levels

| Level | What it proves | What it does not prove |
|---|---|---|
| `synthetic_preflight` | The published contract works against the generic Streamable HTTP and enterprise governed-host profiles using deterministic synthetic data. | Live OAuth/OIDC, a customer deployment, browser redirect handling, production data handling, or external-host approval. |
| `partner_test_tenant` | A named partner host completed the test-tenant procedure under approved configuration. | Production enablement or a broad tenant rollout. |
| `approved_partner` | Product, security, governance, and operations accepted the partner evidence and support handoff. | Permission to bypass ongoing compatibility, scope, or data-handling requirements. |

## Required checks

| Category | Required check | Pass condition |
|---|---|---|
| Discovery and authentication | Read protected-resource metadata; initialize with an approved host and tenant-bound token. | Metadata and initialization succeed using a supported protocol version. |
| Scope handling | Call a proposal-intent tool without `governance:propose`. | Safe authorization denial includes a request ID; host does not silently broaden scope. |
| Tool schemas | Submit a request with an unsupported argument. | Safe validation error exposes no governed result payload. |
| Structured results | Call a permitted discovery tool. | Response includes structured policy/provenance/evidence/timestamp/confidence fields and redaction indicators. |
| Proposal-only behavior | Call an unavailable direct mutation/approval/execution name. | Method is rejected; no governed mutation occurs. |
| Confirmation UX | Create a test proposal only when the steward workflow is explicitly in scope. | Host shows it as pending review and does not request/store/submit a confirmation nonce. |
| Correlation and audit | Send a unique request ID through an allowed call. | DataGenie can locate a matching tenant-bound minimized execution-ledger entry. |
| Error handling | Exercise invalid host, invalid scope, malformed schema, and unavailable direct mutation. | Host preserves safe code/request ID and follows documented retry/stop behavior. |
| Data handling | Review host logs and evidence artifact. | No bearer token, client secret, source credential, row data, raw prompt, or unrestricted result is retained in submitted evidence. |

## Synthetic preflight

Run the repository harness from the repository root:

```bash
python3 tools/run_mcp_partner_certification.py
```

The command writes `docs/evidence/mcp-partner-certification-synthetic.json`. It runs two named profiles:

| Profile | Purpose |
|---|---|
| `generic-streamable-http` | Verifies baseline standards-compliant JSON-RPC, protected-resource discovery, headers, and structured responses. |
| `enterprise-governed-host` | Verifies the same endpoint while exercising proposal-intent scope and a stricter request-ID/ledger support workflow. |

The result is a regression artifact only. Do not alter `certification_level` or submit it as proof of a real customer integration.

## External partner submission

A partner submits the following through the approved support/security channel:

1. Host product, deployed version, host ID, operator, business owner, and support contact.
2. Test-tenant approval and data-handling acknowledgement.
3. Requested scope matrix and tool list, with `governance:propose` justified separately if needed.
4. Sanitized certification output with request IDs, timestamps, protocol/helper version, status/error codes, and no sensitive payloads.
5. Staging OAuth/OIDC result, including redirect/origin behavior where applicable.
6. Host-side user experience evidence that proposals are labeled **pending steward review** and no confirmation nonce is requested, displayed, or stored.
7. Support dry-run record showing DataGenie resolved a request ID to the correct tenant-bound ledger entry.

## Review and decision

| Review owner | Decision criteria |
|---|---|
| Product | Demonstrated customer/domain value and defined owner/support model. |
| Governance | Appropriate evidence, steward workflow, and no autonomous decision path. |
| Security | OAuth/tenant/scope/data-handling controls and negative checks accepted. |
| Architecture | Contract compatibility and versioning plan accepted. |
| Operations | Request-ID-to-ledger support handoff, dashboard, and rollback readiness accepted. |

The decision is `approved`, `approved_with_conditions`, `deferred`, or `declined`. Conditions and remediation dates must be recorded. No generic tool is added merely to make an integration pass; candidates enter the domain-pack governance process.

## Failure handling

A failed check stops the certification at the test-tenant stage. The partner must not respond by disabling tenant isolation, using an admin token, broadening scopes, spoofing a host identity, retrying denied calls with a different tenant, or moving to production. The support contact should submit the safe request ID and error code for investigation.

## Related materials

- [Tenant-admin onboarding pack](mcp-tenant-admin-onboarding.md)
- [Versioning and deprecation policy](mcp-versioning-and-deprecation-policy.md)
- [Domain-pack governance](mcp-domain-pack-governance.md)
