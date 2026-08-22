# DataGenie MCP Reference Helpers

The reference helpers are optional convenience layers for enterprise hosts. They use the standard MCP Streamable HTTP JSON-RPC transport and preserve the gateway’s original JSON-RPC response. They are **not** a replacement for a standard MCP SDK and do not define a proprietary protocol.

| Helper | Entry point | Intended use |
|---|---|---|
| Python | `clients/python/datagenie_mcp.py` | Python hosts that want a small, allowlisted request builder. |
| TypeScript | `clients/typescript/src/index.ts` | TypeScript hosts that want the same constrained surface. |

The hosting application owns OAuth/OIDC authorization, token refresh, secret storage, TLS policy, proxy configuration, retries, user experience, and audit retention. The helpers do not persist tokens or create an execution authority.

## Constrained surface

Both helpers allow the four governed discovery tools and three proposal-intent tools advertised by the gateway. They reject unknown names and direct governance mutation, approval, execution, certification, or job-dispatch names before network dispatch. The gateway remains the authority and enforces the same rule independently.

## Python example

```python
from datagenie_mcp import DataGenieMcpClient

client = DataGenieMcpClient(
    endpoint="https://mcp.example.com/mcp",
    bearer_token=access_token,  # acquired and stored by the host
    host_id="approved-enterprise-host",
)
response = client.call_tool(
    "get_asset_context",
    {"asset_id": "asset-123", "purpose": "financial reporting analysis"},
    request_id="host-2026-08-22-00017",
)
```

## TypeScript example

```ts
import { DataGenieMcpClient } from "@datagenie/mcp-helper";

const client = new DataGenieMcpClient({
  endpoint: "https://mcp.example.com/mcp",
  bearerToken: accessToken, // acquired and stored by the host
  hostId: "approved-enterprise-host",
});
const response = await client.callTool(
  "get_asset_context",
  { asset_id: "asset-123", purpose: "financial reporting analysis" },
  "host-2026-08-22-00017",
);
```

Use a caller-generated `X-Request-ID` for every user-visible operation and retain it with the host audit event. For full OAuth registration, scope selection, test-tenant use, and support investigation, follow the [tenant-admin onboarding pack](../docs/mcp-tenant-admin-onboarding.md).
