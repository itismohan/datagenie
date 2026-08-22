# DataGenie Public Site

This is a static Vite site designed for GitHub Pages or any standards-compliant static host. It contains product information and implementation-oriented documentation for DataGenie’s catalog, quality, lineage, proposal-only governance, tenant onboarding, staging validation, and request-ID support workflow.

## Local development

```bash
pnpm install
pnpm dev
```

## GitHub Pages build

For a repository site such as `https://<owner>.github.io/datagenie/`, build with the repository path:

```bash
VITE_BASE_PATH=/datagenie/ pnpm build
```

For a user/organization site or custom domain served at the host root, use the default:

```bash
pnpm build
```

Publish the generated `dist/public` directory using GitHub Pages Actions. The site has no backend dependency and does not handle OAuth tokens, tenant data, source credentials, or governance confirmations.
