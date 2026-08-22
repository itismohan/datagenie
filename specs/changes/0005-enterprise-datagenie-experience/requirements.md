# Requirements: 0005-enterprise-datagenie-experience — Enterprise DataGenie Experience

## Functional requirements

| ID | Requirement | Acceptance criteria |
|---|---|---|
| DG-UI-ENTERPRISE-001 | The frontend SHALL provide a persistent enterprise product shell with tenant/environment context, global search entry, navigation, alerts, and user context. | Every primary screen renders the shell; narrow views expose navigation without loss of current context. |
| DG-UI-ENTERPRISE-002 | The catalog workspace SHALL present governed assets with business, technical, ownership, classification, certification, quality, and freshness context. | A user can search/filter, select an asset, and see safe metadata plus clear evidence/status labels. |
| DG-UI-ENTERPRISE-003 | The dashboard SHALL present decision-oriented coverage, quality, stewardship, lineage, and operational signals without implying that an AI suggestion is an approved governance action. | KPI cards distinguish evidence, review state, and pending actions; labels never claim autonomous approval. |
| DG-UI-ENTERPRISE-004 | The governance experience SHALL represent agent/MCP-originated changes as proposals pending human steward review and SHALL not expose browser-only direct approval or execution controls. | Proposal cards show source/evidence/policy/impact/status and link to the governed inbox workflow. |
| DG-UI-ENTERPRISE-005 | The interface SHALL provide quality and lineage context with explainability, freshness, incidents, bounded impact, and confidence indicators. | Quality and lineage screens identify evidence/freshness/bounds and do not present a score as authoritative without context. |
| DG-UI-ENTERPRISE-006 | The interface SHALL support safe API loading with an explicit loading/error/demo state and preserve request-ID information for support. | Missing/unavailable API renders a safe fallback/notice; request ID is visible without exposing a token or secret. |
| DG-UI-ENTERPRISE-007 | The interface SHALL be keyboard-operable and responsive across desktop, tablet, and narrow mobile viewports. | Controls have focus states/labels; navigation and content columns reflow without horizontal clipping. |

## Constraints

The UI may call only documented API endpoints using caller-provided runtime configuration and bearer token. It must not hardcode database URLs, credentials, tenant overrides, source secrets, approval nonces, or policy decisions. The UI must make clear that local demonstration data is not an authenticated tenant result.
