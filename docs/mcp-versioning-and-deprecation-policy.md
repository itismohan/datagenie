# DataGenie MCP Versioning and Deprecation Policy

## Purpose and scope

This policy governs the published DataGenie MCP gateway contract: protected-resource metadata, supported MCP protocol versions, tool/resource/prompt names and schemas, structured result fields, safe error codes, authorization semantics, response bounds, and helper compatibility. It complements the versioned OpenAPI practice for REST APIs; it does not replace MCP protocol negotiation or the organization’s OAuth/OIDC lifecycle policy.

> **Contract rule:** A host must negotiate a gateway-supported MCP protocol version and must treat `tool_version`, structured fields, policy obligations, redactions, and safe error codes as contract-bearing data. A host must tolerate additive unknown fields and new enum values safely.

## Version signals

| Signal | Location | Meaning |
|---|---|---|
| MCP protocol version | `MCP-Protocol-Version` request/response header and `initialize` result | Transport/capability compatibility negotiated with the gateway. |
| Gateway release version | `serverInfo.version` in `initialize` | Deployed gateway release identifier. |
| Tool result version | `structuredContent.tool_version` | Schema/behavior release identifier for an individual result family. |
| REST API version | `/api/v1` and `docs/openapi/catalog-api-v1.json` | REST contract version governed by the existing OpenAPI policy. |
| Certification profile version | Partner certification evidence | Harness assertion set and supported host-profile revision. |

## Change classification

| Change class | Examples | Host expectation | DataGenie process |
|---|---|---|---|
| Additive compatible | Optional response field, new evidence type, new separately scoped tool, optional input, supported protocol version added. | Ignore unknown fields safely; request new scope/tool explicitly. | Document in release notes, update tool definitions/helper map/certification fixture, and review result bounds. |
| Behavioral review required | Ranking adjustment, new policy obligation, default bound change within documented limit, enhanced redaction. | Preserve new obligations/redactions; test behavior in the test tenant. | Publish migration guidance and require certified-host compatibility review before broad rollout. |
| Deprecation | Tool, resource, prompt, field, protocol version, or safe error code has a supported replacement. | Adopt replacement before retirement date; retain request-ID evidence during migration. | Mark deprecated in documentation/catalog, publish replacement and date, notify certified-host contacts, and monitor usage. |
| Breaking | Tool removal/rename, required input added, optional input becomes required, output semantic/type change, authorization or redaction change, response bound reduction beyond contract, safe error-code removal. | Migrate to new documented contract major or compatibility path. | Introduce a compatibility path or new major contract, retain prior behavior through notice window, and obtain certified-host review. |
| Emergency security change | Active exploit, tenant-isolation risk, credential exposure, unsafe tool behavior. | Follow emergency notice and disable impacted feature rather than bypass controls. | Use existing kill switch/allowlists, preserve evidence, issue direct notice, and record a time-bound exception. |

## Deprecation lifecycle

1. **Announce:** Publish the affected interface, replacement, rationale, first affected release, retirement date, and support contact in release notes and this policy’s change record.
2. **Support:** Keep the deprecated behavior available for at least **90 days** in the internal/customer beta unless a security exception is approved. Preserve existing tenant, scope, policy, and redaction controls during the window.
3. **Migrate:** Provide a test-tenant path, helper update where applicable, compatibility examples, and partner certification re-run instructions.
4. **Review usage:** Contact named certified-host owners and review sanitized usage/ledger evidence; do not infer tenant-specific details from broad telemetry.
5. **Retire:** Remove only after the published date, required compatibility evidence, and product/security/operations approval. Update documentation, certification matrix, and support knowledge base.

A shorter notice period requires a named security owner, scope, risk, compensating controls, expiry, and removal task in the SDD evidence record.

## Compatibility promises

DataGenie will not silently change the meaning of an approved tool, transform a read or proposal-intent operation into a direct write, remove a structured evidence/policy boundary, or make a host token more powerful through a helper update. New domain capabilities should first appear as documented resources, prompts, evidence packs, facets, or proposal types. A direct governance mutation requires a separately reviewed product, policy, and human-control design.

## Change record and notice

Each contract-affecting release must record the following:

| Field | Required content |
|---|---|
| Release and contract versions | Gateway, protocol, tool-result, helper, and certification-profile versions. |
| Classification | Additive, behavioral review, deprecation, breaking, or emergency security change. |
| Affected tenants/hosts | Named approved host contacts; no sensitive tenant metadata in public notes. |
| Migration steps | Test-tenant procedure, replacement mapping, and certification re-run expectation. |
| Retirement date | Required for every deprecation. |
| Evidence | Contract diff, certification result, support readiness, and approval record. |

## Support commitment

A host support case must include a request ID, tenant, host ID, tool, timestamp, protocol/helper version, and safe error code. DataGenie support correlates these values with minimized tenant-scoped ledger evidence. Support will never ask for bearer tokens, client secrets, source credentials, raw rows, or unrestricted prompts as a compatibility prerequisite.

## Related materials

- [Tenant-admin onboarding pack](mcp-tenant-admin-onboarding.md)
- [Partner certification guide](mcp-partner-certification.md)
- [API integration and OpenAPI versioning practice](api-integration-guide.md)
- [MCP authorization reference](mcp-authorization-reference.md)
