"""Optional constrained helper for standard DataGenie MCP Streamable HTTP hosts.

The caller owns OAuth/OIDC acquisition, token refresh, secret storage, TLS policy, and
host lifecycle. This module serializes ordinary JSON-RPC requests and intentionally
exposes only DataGenie's published discovery and proposal-intent tool names.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

PROTOCOL_VERSION = "2026-07-28"
HELPER_VERSION = "0.1.0"

DISCOVERY_TOOLS = frozenset(
    {
        "search_governed_assets",
        "get_asset_context",
        "get_quality_evidence",
        "analyze_lineage_impact",
    }
)
PROPOSAL_TOOLS = frozenset(
    {
        "create_governance_proposal",
        "request_certification_review",
        "schedule_quality_check",
    }
)
SUPPORTED_TOOLS = DISCOVERY_TOOLS | PROPOSAL_TOOLS


class UnsupportedToolError(ValueError):
    """Raised before network dispatch for any non-published tool name."""


class TransportError(RuntimeError):
    """Raised only when no safe JSON-RPC response can be decoded."""


JsonRpcTransport = Callable[[str, Mapping[str, str], dict[str, Any]], dict[str, Any]]


def _validate_tool(name: str, arguments: Mapping[str, Any]) -> None:
    if name not in SUPPORTED_TOOLS:
        raise UnsupportedToolError(
            f"{name!r} is not a published DataGenie MCP discovery or proposal-intent tool. "
            "Approval, execution, certification, direct update, and job-dispatch operations are unavailable."
        )
    if not isinstance(arguments, Mapping):
        raise ValueError("Tool arguments must be an object.")
    if name != "search_governed_assets" and not isinstance(arguments.get("asset_id"), str):
        raise ValueError("The selected tool requires a non-empty asset_id string.")
    if name == "create_governance_proposal":
        for field in ("proposal_type", "title", "proposal_text", "purpose", "technical_version"):
            if field not in arguments:
                raise ValueError(f"create_governance_proposal requires {field!r}.")
    elif name in PROPOSAL_TOOLS and not isinstance(arguments.get("purpose"), str):
        raise ValueError("Proposal-intent tools require a declared purpose.")


def _default_transport(endpoint: str, headers: Mapping[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    request = Request(
        endpoint,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={**headers, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:  # nosec B310: endpoint is caller-controlled enterprise config
            body = response.read()
    except HTTPError as exc:
        body = exc.read()
    try:
        decoded = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TransportError("The MCP endpoint returned no decodable JSON-RPC response.") from exc
    if not isinstance(decoded, dict):
        raise TransportError("The MCP endpoint returned an invalid JSON-RPC response.")
    return decoded


@dataclass(frozen=True)
class DataGenieMcpClient:
    """Minimal helper that returns the gateway's original JSON-RPC response unchanged."""

    endpoint: str
    bearer_token: str
    host_id: str
    protocol_version: str = PROTOCOL_VERSION
    transport: JsonRpcTransport = _default_transport

    def initialize(self, request_id: str) -> dict[str, Any]:
        return self._rpc("initialize", {}, request_id)

    def call_tool(self, name: str, arguments: Mapping[str, Any], request_id: str) -> dict[str, Any]:
        _validate_tool(name, arguments)
        return self._rpc("tools/call", {"name": name, "arguments": dict(arguments)}, request_id)

    def _rpc(self, method: str, params: Mapping[str, Any], request_id: str) -> dict[str, Any]:
        if not self.endpoint.startswith("https://") and not self.endpoint.startswith("http://localhost"):
            raise ValueError("MCP endpoint must use HTTPS outside local development.")
        if not request_id.strip():
            raise ValueError("request_id is required for support correlation.")
        payload = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": dict(params)}
        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Mcp-Client-Id": self.host_id,
            "MCP-Protocol-Version": self.protocol_version,
            "X-Request-ID": request_id,
            "User-Agent": f"datagenie-mcp-python-helper/{HELPER_VERSION}",
        }
        return self.transport(self.endpoint, headers, payload)
