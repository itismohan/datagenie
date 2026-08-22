# Change Proposal: 0005-enterprise-datagenie-experience — Enterprise DataGenie Experience

**Status:** Draft
**Owner:** DataGenie product, design, platform, and governance teams
**Related changes:** `0002-internal-policy-decision-interface`, `0003-proposal-only-governance-workflows`, `0004-mcp-ecosystem-productization`

## Problem

The current frontend is a prototype catalog list without enterprise navigation, hierarchy, operational context, stewardship workflows, responsive layout, or a safe distinction between discovery and governance action. It does not make DataGenie’s governed discovery, explainable quality, lineage impact, proposal-only workflows, tenant context, or support correlation legible to a business user.

## Proposed outcome

Deliver a responsive enterprise workspace with a unified product shell, clear tenant/environment context, decision-oriented dashboard, governed catalog discovery, asset context, quality and lineage views, proposal inbox preview, activity/support correlation, and administration posture. The design shall present AI and governance outcomes as evidence-bearing, reviewable states rather than autonomous authority.

## Scope

| Included | Explicitly excluded |
|---|---|
| Enterprise design system, responsive navigation, dashboard, asset workspace, proposal inbox, quality/lineage panels, and administration posture | A new authentication system, SSO implementation, production tenant provisioning, or policy logic in the browser |
| API-aware catalog loading with synthetic fallback and clear connection state | Client-side bypass of RBAC, tenant isolation, or governance proposal confirmation controls |
| Clear proposal-only user experience that links to human steward review | Direct asset mutation, proposal approval/execution from untrusted frontend state, or a model-driven approval flow |
| Visual accessibility, keyboard focus, loading/error/empty states, and support request-ID presentation | Full mobile-native implementation or replacement of existing backend APIs |

## Success criteria

A user can understand where they are, which tenant/environment is active, find governed assets, inspect ownership/classification/quality/freshness/lineage context, recognize whether a change is only a pending proposal, and locate the request ID needed for support. An administrator can understand integration posture without exposing secrets. The interface remains usable on desktop, tablet, and narrow mobile views.

## Release decision

This is a frontend experience enhancement. It may use synthetic fallback data only to preserve the product shell in local development; a staging walkthrough with authenticated tenant data, a steward review, accessibility review, and product approval is required before customer-facing rollout.
