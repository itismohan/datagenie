# DataGenie Production Operations Guide

## Environment model

DataGenie uses one configuration namespace, `DATAGENIE_`, and every environment receives its own database, signing secret, and service credentials. Never commit `.env`, database URLs containing passwords, JWT signing keys, or source passwords. The tracked [`.env.example`](../.env.example) file is a shape-only template.

| Environment | Purpose | Required controls |
|---|---|---|
| Development | Local feature work | Isolated local credentials; application may use SQLite only when launched outside Compose |
| Staging | Deployment and integration verification | PostgreSQL, authentication enabled, unique signing key, migrations applied automatically, test data only |
| Production | Customer workloads | PostgreSQL, authentication enabled, unique managed secrets, restricted network access, tested backup recovery, and monitored service objectives |

The Catalog API rejects a staging or production configuration that uses SQLite, disables authentication, or provides a JWT signing secret shorter than 32 characters.

## Local platform startup

First create a local environment file and replace all placeholder values.

```bash
cp .env.example .env
# Edit .env with local-only passwords and a unique JWT signing secret.

docker compose --env-file .env -f infra/docker-compose.yml up --build
```

The stack starts PostgreSQL, Redis, Neo4j, a migration container, and the Catalog, Connector, Lineage, Quality, and Search API boundaries. Only the Catalog API is exposed on the host at `http://localhost:8000`; the other prototype services are intentionally limited to the internal network until they adopt the Catalog API's authorization, audit, and observability conventions.

The migration container must complete successfully before the Catalog API starts. This turns schema migration into a deployment gate rather than an implicit side effect of serving customer traffic.

## Service probes and observability

| Endpoint | Purpose |
|---|---|
| `GET /health/live` | Process liveness probe |
| `GET /health/ready` | Readiness probe; confirms a database query succeeds |
| `GET /metrics` | Prometheus metrics for request count, latency, and unhandled errors |
| `GET /docs` | Versioned API documentation |
| `GET /api/v1/audit-events` | Restricted platform-administrator audit history |

Requests accept or generate `X-Request-ID`. The value is returned to clients and written to JSON request logs, error bodies, and audit events. The Catalog API does not log authorization headers, raw passwords, or source-secret values.

To start Prometheus locally, add the observability profile:

```bash
docker compose --env-file .env -f infra/docker-compose.yml --profile observability up --build
```

Prometheus is then available at `http://localhost:9090` and scrapes the Catalog API internally.

## Authentication and authorization

Outside development, `DATAGENIE_AUTH_ENABLED=true` is mandatory. The initial implementation verifies signed HS256 bearer tokens containing `sub`, `roles`, and `exp` claims. The permitted roles are `platform_admin`, `data_steward`, `data_owner`, `analyst`, and `read_only`.

| Operation | Permitted roles |
|---|---|
| Search or inspect catalog assets and glossary terms | Any defined role |
| Register, validate, or ingest a source | Platform administrator or data steward |
| Curate an asset | Platform administrator, data steward, or the assigned data owner |
| View ingestion jobs | Platform administrator or data steward |
| View audit history | Platform administrator only |

The HS256 implementation provides a self-contained local and staging baseline. Before broad enterprise release, replace shared-secret token issuance with an OIDC identity provider and JWKS-based verification without changing the principal and role interfaces.

## Backups and restore testing

Backups are custom-format PostgreSQL dumps with a SHA-256 checksum. Run them only after the local Compose stack is healthy.

```bash
infra/scripts/backup-postgres.sh
infra/scripts/verify-postgres-restore.sh backups/datagenie-YYYYMMDDTHHMMSSZ.dump
```

The restore procedure creates a separate temporary database, restores the dump, verifies the critical catalog, audit, and glossary tables, and removes the temporary database even if verification fails. Production operations should schedule this backup procedure through the deployment platform and perform restore verification at least quarterly before declaring a recovery objective met.

## Deployment and promotion checklist

CI validates the Catalog test suite, applies the complete migration chain against PostgreSQL, verifies the Compose topology, and syntax-checks operational scripts. A promotion to staging or production should additionally use immutable image tags, a deployment-specific secret store, a migration backup, readiness-gated rollout, monitored error and latency dashboards, and a documented rollback decision.

A safe sequence is: build and test an immutable image, back up the target database, apply migrations, deploy to staging, run authenticated smoke tests, promote the same image to production, and monitor the request, error, and readiness signals. Roll back application code only when the migration is backward-compatible; otherwise follow a prepared forward-fix or restore plan.
