# Catalog RBAC and Audit Contract

## Roles

| Role | Intent |
|---|---|
| `platform_admin` | Operates the platform, connector estate, policy, and audit capability |
| `data_steward` | Curates governed metadata and operates approved connector synchronizations |
| `data_owner` | Curates only catalog assets for which their token subject is the assigned owner |
| `analyst` | Discovers and reads catalog metadata without changing it |
| `read_only` | Reads catalog metadata without changing it |

`platform_admin` is an explicit override for every permission. No missing or unknown role is accepted in a bearer token.

## Endpoint authorization matrix

| Resource and action | Platform admin | Data steward | Data owner | Analyst | Read-only |
|---|---:|---:|---:|---:|---:|
| Search or inspect catalog assets | Yes | Yes | Yes | Yes | Yes |
| Curate an asset | Yes | Yes | Assigned assets only | No | No |
| List or inspect business glossary | Yes | Yes | Yes | Yes | Yes |
| Create a glossary term | Yes | Yes | No | No | No |
| Register, list, or inspect connector sources | Yes | Yes | No | No | No |
| Inspect connector capabilities or cursor state | Yes | Yes | No | No | No |
| Validate a connector, start a job, retry, cancel, or inspect jobs | Yes | Yes | No | No | No |
| Inspect audit events | Yes | No | No | No | No |

## Audit requirements

Every successful or denied security-sensitive connector operation records an immutable event. This includes source registration, connector-source list and inspection, capability and cursor-state inspection, credential validation outcome, ingestion start, retry, cancellation, and job-history reads. Catalog asset search, asset reads, metadata curation, glossary changes, and audit-log reads are also tracked.

Each event contains a request ID, actor subject and roles, action, resource type and identifier where applicable, outcome, timestamp, and intentionally limited non-secret metadata. Audit payloads must never include bearer tokens, passwords, secret references, raw connection strings, or decrypted connector credentials.

Authentication failures are logged structurally with a request ID but do not create a database audit event because no trustworthy principal has been established. Authorization denials create a database audit event when a validated principal and database session are available.

## Audit event naming

| Action | Resource type | Typical outcome |
|---|---|---|
| `source.list`, `source.read`, `source.capabilities`, `source.sync_state` | `data_source` | `success` |
| `source.create`, `source.validate` | `data_source` | `success` or `failure` |
| `ingestion_job.list`, `ingestion_job.read`, `ingestion_job.run`, `ingestion_job.retry`, `ingestion_job.cancel` | `ingestion_job` | `success`, `failure`, or `denied` |
| `asset.search`, `asset.read`, `asset.curate` | `asset` | `success` or `denied` |
| `glossary.list`, `glossary.create` | `glossary_term` | `success` |
| `audit_event.list` | `audit_event` | `success` |

The audit store is readable only by `platform_admin`. Pagination and filters make it operable without exposing it to lower-privilege catalog users.
