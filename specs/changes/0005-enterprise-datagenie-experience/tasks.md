# Tasks: 0005-enterprise-datagenie-experience — Enterprise DataGenie Experience

**Change ID:** 0005-enterprise-datagenie-experience

| Task | Outcome | Requirement coverage | Status |
|---|---|---|---|
| 1. Establish buildable frontend baseline | Add Vite entry, scripts, and dependency definitions around the existing React app. | DG-UI-ENTERPRISE-001, 007 | Complete locally |
| 2. Implement enterprise shell and visual system | Responsive navigation, tenant context, alerts, search, focus styles, design tokens. | DG-UI-ENTERPRISE-001, 007 | Complete locally |
| 3. Implement control center and catalog | Decision KPIs, API-aware governed asset search, selected asset context, safe fallback. | DG-UI-ENTERPRISE-002, 003, 006 | Complete locally |
| 4. Implement quality, lineage, proposals, and admin workspaces | Explainable/bounded evidence context and proposal-only review UX. | DG-UI-ENTERPRISE-004, 005 | Complete locally |
| 5. Validate safe content and responsive behaviors | Build, static/source checks, desktop/tablet/narrow walkthrough. | All | Desktop validation complete; narrow walkthrough pending |
| 6. Publish release evidence | SDD validation, commit, and staging approval checklist. | All | Local validation complete; publication pending |

## Release gate

Customer rollout requires authenticated staging validation with a named tenant, steward review that confirms proposal-only presentation, request-ID support dry run, keyboard/responsive walkthrough, and named product, governance, security, and operations approval.
