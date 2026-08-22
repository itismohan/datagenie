# Public Site Information Architecture

The DataGenie public site is a single-page, static GitHub Pages–ready narrative built for enterprise buyers, platform teams, data stewards, and support owners.

| Section | Reader question | Content outcome |
|---|---|---|
| Hero and platform | What does DataGenie make possible? | A clear proposition: data decisions become traceable through catalog, quality, lineage, and stewardship context. |
| Platform pillars | What capabilities are connected? | Catalog, quality, lineage, and human-governed change are introduced as one operating model. |
| Governance model | How are agents useful without becoming authorities? | The proposal/inbox/confirmation separation is explained as a protected trust boundary. |
| Documentation center | What, why, and how? | A reader can switch between foundational explanatory content without leaving the page. |
| Catalog definition | What does “catalog” mean in this product? | Discovered facts, curated metadata, and usable discovery are distinguished. |
| Staging guide | How does a tenant verify safe enablement? | A numbered OAuth, scope, proposal, confirmation, and request-ID workflow is available. |
| Detailed test plan | What must be tested before customer enablement? | Tenant binding, audience, scope, schemas, proposal separation, rechecks, and correlation have explicit criteria. |

## Governance UX separation statement

The public site must distinguish a **proposal** from a **governed change**. An agent or MCP host may submit structured proposal intent, but it cannot approve, execute, certify, mutate a governed asset, or produce a valid confirmation nonce. The protected steward route evaluates the approver’s current authority and rechecks the proposal hash, expiry, nonce, policy, and resource version before any mutation. A failed recheck blocks execution and preserves audit evidence.

## Local verification criteria

The public site build must succeed. The home page must render the supplied approved DataGenie logo and all four generated visual assets. The governance section must explicitly say that a recommendation is not a governed change. The staging guide must include a test-tenant boundary, least-privilege scope test, proposal-only exercise, steward confirmation recheck, and request-ID-to-ledger dry run. The static site must remain free of OAuth client secrets, bearer tokens, tenant data, source credentials, raw prompts, raw rows, or confirmation nonces.
