from prometheus_client import Counter, Histogram

MCP_TOOL_CALLS = Counter(
    "datagenie_mcp_tool_calls_total",
    "MCP operations by kind, operation name, outcome, host, and tenant.",
    ["kind", "operation", "outcome", "host", "tenant"],
)
MCP_POLICY_DECISIONS = Counter(
    "datagenie_mcp_policy_decisions_total",
    "Policy outcomes observed by MCP tool operations.",
    ["operation", "outcome"],
)
MCP_RESULT_BYTES = Histogram(
    "datagenie_mcp_result_bytes",
    "Serialized structured MCP result sizes.",
    ["operation"],
    buckets=(256, 1024, 4096, 16384, 65536, 262144),
)
MCP_TOOL_LATENCY = Histogram(
    "datagenie_mcp_tool_duration_seconds",
    "MCP operation latency.",
    ["operation"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)
MCP_ERRORS = Counter(
    "datagenie_mcp_errors_total",
    "MCP errors by safe code and operation.",
    ["operation", "code"],
)
MCP_LEDGER_FAILURES = Counter(
    "datagenie_mcp_execution_ledger_write_failures_total",
    "MCP execution ledger persistence failures.",
    ["operation"],
)
MCP_RATE_LIMIT_DENIALS = Counter(
    "datagenie_mcp_rate_limit_denials_total",
    "MCP requests denied by the gateway rate limiter.",
    ["host", "tenant"],
)
MCP_TENANT_BOUNDARY_VIOLATIONS = Counter(
    "datagenie_mcp_tenant_boundary_violations_total",
    "Caller-controlled tenant override or non-visible resource attempts.",
    ["operation"],
)
