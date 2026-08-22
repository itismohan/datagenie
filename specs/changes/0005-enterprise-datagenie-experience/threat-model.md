# Threat Model: 0005-enterprise-datagenie-experience — Enterprise DataGenie Experience

| Threat | Mitigation | Verification |
|---|---|---|
| The UI displays a tenant label that is mistaken for authorization. | Label is explicitly non-authoritative; API token and backend RLS/policy remain authoritative. | Review source for no tenant override in request body/query; exercise API fallback state. |
| A user interprets a proposal as already applied or can bypass stewardship. | Proposal cards use pending/review language and link to the authorized inbox only. No approval/execute/nonce controls exist. | Static/source test rejects direct workflow verbs and checks proposal-only copy. |
| Local synthetic fallback is mistaken for customer data. | Connection notice labels the view “demonstration data” whenever API loading fails or tokenless local mode is used. | Component test verifies demo-state banner. |
| Frontend logs or stores bearer tokens, source secrets, approval nonces, or sensitive raw data. | Runtime token is read only for request header; no persistence/logging; admin/support panels show only safe fields. | Source scan and code review. |
| A quality score is presented without explainability or freshness. | Quality cards include evidence, rule coverage, freshness, and incident context. | UI copy/render test checks contextual labels. |
| Lineage graph is presented as comprehensive when it is bounded. | Lineage panels label direction, depth, confidence, and bounds. | UI copy/render test checks boundary labels. |
| Keyboard or narrow-view users cannot operate critical workspace controls. | Semantic controls, visible focus treatment, responsive breakpoints, and reflowed navigation. | Build review plus keyboard/responsive walkthrough. |
| Error handling encourages unsafe retry or requests secrets from users. | Error banner preserves safe request ID and directs support workflow; it never asks for tokens/secrets. | Source test verifies safe support language. |

The frontend adds presentation and local orchestration only. It does not alter backend tenant isolation, role evaluation, policy decisions, service-to-service identity, or governance execution protections.
