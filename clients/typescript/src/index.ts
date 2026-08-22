/**
 * Optional constrained helper for standards-compliant DataGenie MCP hosts.
 *
 * OAuth token acquisition, refresh, secret storage, proxy configuration, and TLS
 * policy remain the enterprise host's responsibility. The helper sends ordinary
 * Streamable HTTP JSON-RPC requests and returns the gateway response unchanged.
 */

export const PROTOCOL_VERSION = "2026-07-28";
export const HELPER_VERSION = "0.1.0";

export const DISCOVERY_TOOLS = [
  "search_governed_assets",
  "get_asset_context",
  "get_quality_evidence",
  "analyze_lineage_impact",
] as const;

export const PROPOSAL_TOOLS = [
  "create_governance_proposal",
  "request_certification_review",
  "schedule_quality_check",
] as const;

export const SUPPORTED_TOOLS = [...DISCOVERY_TOOLS, ...PROPOSAL_TOOLS] as const;
export type SupportedTool = (typeof SUPPORTED_TOOLS)[number];

export type JsonRpcResponse = {
  jsonrpc?: "2.0";
  id?: string | number | null;
  result?: Record<string, unknown>;
  error?: { code: number; message: string; data?: Record<string, unknown> };
};

export type ClientOptions = {
  endpoint: string;
  bearerToken: string;
  hostId: string;
  protocolVersion?: string;
  fetchImpl?: typeof fetch;
};

function assertSupportedTool(name: string, arguments_: Record<string, unknown>): asserts name is SupportedTool {
  if (!SUPPORTED_TOOLS.includes(name as SupportedTool)) {
    throw new Error(
      `${name} is not a published DataGenie MCP discovery or proposal-intent tool. ` +
        "Approval, execution, certification, direct update, and job-dispatch operations are unavailable.",
    );
  }
  if (name !== "search_governed_assets" && typeof arguments_.asset_id !== "string") {
    throw new Error("The selected tool requires a non-empty asset_id string.");
  }
  if (name === "create_governance_proposal") {
    for (const field of ["proposal_type", "title", "proposal_text", "purpose", "technical_version"]) {
      if (!(field in arguments_)) throw new Error(`create_governance_proposal requires ${field}.`);
    }
  } else if (PROPOSAL_TOOLS.includes(name as (typeof PROPOSAL_TOOLS)[number]) && typeof arguments_.purpose !== "string") {
    throw new Error("Proposal-intent tools require a declared purpose.");
  }
}

export class DataGenieMcpClient {
  private readonly endpoint: string;
  private readonly bearerToken: string;
  private readonly hostId: string;
  private readonly protocolVersion: string;
  private readonly fetchImpl: typeof fetch;

  constructor(options: ClientOptions) {
    if (!options.endpoint.startsWith("https://") && !options.endpoint.startsWith("http://localhost")) {
      throw new Error("MCP endpoint must use HTTPS outside local development.");
    }
    this.endpoint = options.endpoint;
    this.bearerToken = options.bearerToken;
    this.hostId = options.hostId;
    this.protocolVersion = options.protocolVersion ?? PROTOCOL_VERSION;
    this.fetchImpl = options.fetchImpl ?? fetch;
  }

  initialize(requestId: string): Promise<JsonRpcResponse> {
    return this.rpc("initialize", {}, requestId);
  }

  callTool(name: string, arguments_: Record<string, unknown>, requestId: string): Promise<JsonRpcResponse> {
    assertSupportedTool(name, arguments_);
    return this.rpc("tools/call", { name, arguments: arguments_ }, requestId);
  }

  private async rpc(method: string, params: Record<string, unknown>, requestId: string): Promise<JsonRpcResponse> {
    if (!requestId.trim()) throw new Error("requestId is required for support correlation.");
    const response = await this.fetchImpl(this.endpoint, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${this.bearerToken}`,
        "Content-Type": "application/json",
        "Mcp-Client-Id": this.hostId,
        "MCP-Protocol-Version": this.protocolVersion,
        "X-Request-ID": requestId,
        "User-Agent": `datagenie-mcp-typescript-helper/${HELPER_VERSION}`,
      },
      body: JSON.stringify({ jsonrpc: "2.0", id: requestId, method, params }),
    });
    const payload: unknown = await response.json();
    if (typeof payload !== "object" || payload === null || Array.isArray(payload)) {
      throw new Error("The MCP endpoint returned an invalid JSON-RPC response.");
    }
    return payload as JsonRpcResponse;
  }
}
