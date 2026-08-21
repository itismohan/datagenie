# MCP Governed Discovery Beta Operations Dashboard

This dashboard is restricted to the approved internal beta tenant and hosts. It uses bounded labels only: tool/operation, outcome, policy outcome, host and tenant. It must not label metrics with asset identifiers, purposes, bearer tokens, query text, raw result content, or source credentials.

| Panel | Prometheus query | Initial internal-beta target | Operator response |
|---|---|---|---|
| Tool calls by host and tenant | `sum by (operation, outcome, host, tenant) (increase(datagenie_mcp_tool_calls_total[15m]))` | Observe baseline only. | Investigate unexpected host or tenant labels immediately. |
| Denied calls and policy outcomes | `sum by (operation, outcome) (increase(datagenie_mcp_policy_decisions_total[15m]))` | No unexplained increase in denies. | Review signed execution ledger samples and policy rule IDs. |
| p95 read-tool latency | `histogram_quantile(0.95, sum by (le, operation) (rate(datagenie_mcp_tool_duration_seconds_bucket[15m])))` | `≤ 2s` for search/context/quality; `≤ 5s` for lineage. | Check downstream catalog/lineage availability and disable the affected tool if sustained. |
| Tool error rate | `sum(rate(datagenie_mcp_errors_total[15m])) / clamp_min(sum(rate(datagenie_mcp_tool_calls_total[15m])), 0.001)` | `< 1%` across each 15-minute window. | Stop beta traffic above the threshold until the error class is resolved. |
| Result size | `histogram_quantile(0.95, sum by (le, operation) (rate(datagenie_mcp_result_bytes_bucket[15m])))` | Within documented MCP response bounds. | Narrow result/depth caps or investigate a redaction/truncation defect. |
| Ledger failures | `increase(datagenie_mcp_execution_ledger_write_failures_total[5m])` | `0`. | Treat as fail-closed; disable beta traffic and restore durable audit persistence. |
| Rate-limit denials | `sum by (host, tenant) (increase(datagenie_mcp_rate_limit_denials_total[15m]))` | Stable and expected for load testing only. | Investigate host automation, prompt loops, or a configured limit mismatch. |
| Tenant boundary violations | `increase(datagenie_mcp_tenant_boundary_violations_total[15m])` | `0`. | Security incident: preserve ledger evidence and disable the beta. |

## SLO evaluation procedure

The product and security owners must review the dashboard during the internal canary. A release candidate meets the latency gate only when p95 remains within the targets for at least one representative internal test window, while the error-rate, ledger-failure, and tenant-boundary-violation gates remain satisfied. Approval samples must be paired with the corresponding minimized agent execution ledger records.
