# Test Plan: 0005-enterprise-datagenie-experience — Enterprise DataGenie Experience

| Area | Scenario | Expected result |
|---|---|---|
| Shell/navigation | Switch each workspace and open narrow-view navigation. | Active context is visible; all workspaces remain reachable. |
| Catalog loading | API returns assets, returns an error, or is unavailable. | Assets load safely; error/demo state is explicit and includes request ID. |
| Asset context | Select a catalog row. | Detail card shows ownership, classification, certification, quality/freshness, and evidence context. |
| Proposal safety | Open proposal workspace and action links. | UI presents pending review and steward inbox route only; no approval/execute/nonce control is rendered. |
| Quality/lineage | Review quality and lineage cards. | Evidence/freshness/rules/incidents and direction/depth/confidence/bounds are visible. |
| Sensitive data | Inspect frontend source/runtime configuration. | No token persistence, secret literals, tenant override, source credential, or approval nonce exists. |
| Keyboard/accessibility | Tab through navigation, search, filters, buttons, and notices. | Controls are semantic, labeled, and visibly focusable. |
| Responsive | Evaluate desktop, 980px tablet, and 720px narrow layouts. | Navigation and grids reflow without losing task context. |
| Build | Install dependencies and run production build. | Build succeeds without warnings that block deployment. |

## Test environment

Use local synthetic fallback data for visual regression and a tokenless API endpoint only when backend discovery is unavailable. Use an approved staging tenant for authenticated workflow walkthroughs. Never capture production tokens, source credentials, raw rows, or approval nonces in UI test artifacts.

## Acceptance evidence

Record build output, source/contract test output, viewport walkthrough notes, request IDs from staging, steward review confirmation, and known limitations in `evidence.md`.
