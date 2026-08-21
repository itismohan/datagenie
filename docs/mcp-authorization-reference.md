# MCP Authorization and Streamable HTTP Implementation Reference

This implementation reference records the protocol requirements used for the DataGenie internal MCP beta. It is intentionally limited to the controls implemented or validated by the gateway.

| Area | Applied requirement |
|---|---|
| Protected resource discovery | A protected HTTP MCP server publishes OAuth 2.0 Protected Resource Metadata with at least one `authorization_servers` value, and sends a `WWW-Authenticate` challenge with `resource_metadata` on missing/invalid credentials. |
| Authorization server discovery | The resource server advertises authorization server location; the client discovers OAuth authorization-server metadata or OIDC discovery metadata. |
| Token use | The gateway acts as a resource server, validates the bearer token issuer/signature/expiry/audience/tenant/scopes, and does not forward the host token to downstream services. |
| Streamable HTTP | The MCP endpoint accepts JSON-RPC POSTs; protocol negotiation and request metadata are validated before dispatch. |
| Transport security | Incoming request origin is allowlisted when present; unsupported/mismatched protocol metadata is rejected; the gateway uses structured JSON-RPC errors. |
| Resource indicator | The protected resource identifier is the canonical gateway MCP URL and is advertised in metadata. |

## Sources

[1] Model Context Protocol, **Authorization** (2025-11-25): https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization

[2] Model Context Protocol, **Streamable HTTP** (draft, accessed 2026-08-22): https://modelcontextprotocol.io/specification/draft/basic/transports/streamable-http
