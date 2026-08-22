# MCP Specification Notes for DataGenie Architecture

## Authoritative findings

The Model Context Protocol is a JSON-RPC protocol that connects an LLM host, an isolated client connection, and a capability-providing server. Its server primitives are **resources**, **prompts**, and **tools**; its optional extensions include long-running tasks, skills, and interactive MCP Apps.[1]

The host—not an MCP server—is responsible for coordinating client connections, enforcing security policy and consent, and keeping one server from reading another server's context. Servers should be focused and composable, with capabilities negotiated explicitly during initialization.[2]

For HTTP transports, MCP authorization guidance positions a protected MCP server as an OAuth 2.1 resource server. The guidance requires protected-resource metadata and authorization-server discovery where the authorization extension is implemented, recommends least-privilege scope selection, and requires tokens to be validated for the server's intended audience. Tokens must not be passed through to downstream services.[3]

The security guidance emphasizes explicit user consent, clear action visibility, prevention of confused-deputy behavior, exact redirect URI validation, per-client consent where a proxy uses third-party authorization, SSRF controls for URL discovery, egress restrictions, and binding state handles to the authenticated principal instead of treating possession as authentication.[4]

## Implications for DataGenie

1. The MCP server should be a **separate adapter/control plane**, not a direct exposure of every REST endpoint. It should call existing tenant-scoped domain services and preserve their authorization and audit controls.
2. Tools must be designed as small, task-oriented, evidence-bearing actions. Every mutating tool needs a dry-run/preflight mode, structured change preview, explicit confirmation token, idempotency key, and audit event.
3. Read-only information should be offered first as resources and searchable tools, while governance-impacting actions remain approval-gated workflows.
4. A remote DataGenie MCP endpoint requires OAuth/OIDC scopes, audience validation, resource metadata, TLS, rate limits, egress controls, and per-tenant operational isolation before external-client enablement.

## References

[1]: https://modelcontextprotocol.io/specification/2026-07-28
[2]: https://modelcontextprotocol.io/specification/2025-11-25/architecture
[3]: https://modelcontextprotocol.io/specification/draft/basic/authorization
[4]: https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices
