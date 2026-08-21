# DataGenie Quality Operations Guide

## Operating model

DataGenie quality results are **deterministic assessments of a persisted profile snapshot**. A run does not invent a score. It records the source profile, effective rule versions, observed values, thresholds, sample-row evidence, rule explanations, and the final weighted technical score. A run with missing profile evidence is retained but marked `explainable: false`; its score is `null` rather than being treated as authoritative.

Technical quality is intentionally separate from business criticality and certification. A steward or owner should configure the quality context for each important asset before interpreting the score.

```bash
curl -X PUT http://localhost:8000/api/v1/quality/assets/ASSET_ID/context \
  -H 'Content-Type: application/json' \
  -d '{
    "business_criticality": "critical",
    "certification_status": "under_review",
    "accountable_owner": "data-owner@example.com"
  }'
```

## Publish a source-derived profile

A connector, profiler, or controlled profiling job publishes the exact evidence used by rules. The initial profile schema is intentionally simple and declarative. Asset-level rules read fields at the top level. Column-level rules read the corresponding object beneath `columns`.

```bash
curl -X PUT http://localhost:8000/api/v1/quality/assets/ASSET_ID/profile \
  -H 'Content-Type: application/json' \
  -d '{
    "observed_at": "2026-08-21T09:00:00Z",
    "profiled_by": "postgresql-profiler",
    "snapshot": {
      "row_count": 10000,
      "latest_record_at": "2026-08-21T08:45:00Z",
      "columns": {
        "customer_id": {
          "row_count": 10000,
          "null_count": 3,
          "distinct_count": 9990,
          "invalid_count": 0,
          "orphan_count": 2,
          "related_asset_id": "CUSTOMERS_ASSET_ID",
          "sample_rows": [{"customer_id": "C-0001"}]
        }
      }
    }
  }'
```

The profile must be sourced through controlled queries or a connector account with least privilege. Sample rows should contain only the minimum evidence needed to investigate a failure and must follow the organization’s classification and privacy policies.

## Define and version rules

Rules are asset- or column-scoped, owner-assigned, versioned, enabled or disabled, and optionally scheduled. Updating a semantic rule field creates a new version; every result retains the exact version it evaluated.

```bash
curl -X POST http://localhost:8000/api/v1/quality/rules \
  -H 'Content-Type: application/json' \
  -H 'X-Quality-Actor: data-steward@example.com' \
  -d '{
    "asset_id": "ASSET_ID",
    "column_name": "customer_id",
    "name": "Customer identifier completeness",
    "rule_type": "completeness",
    "severity": "high",
    "owner": "data-owner@example.com",
    "parameters": {"minimum_ratio": 0.995},
    "schedule_cron": "0 * * * *",
    "next_run_at": "2026-08-21T10:00:00Z"
  }'
```

| Rule type | Required profile fields | Example parameter |
|---|---|---|
| Completeness | `row_count`, `null_count` | `minimum_ratio: 0.995` |
| Uniqueness | `row_count`, `distinct_count` | `minimum_ratio: 0.999` |
| Validity | `row_count`, `invalid_count` | `minimum_ratio: 0.99` |
| Freshness | `latest_record_at` | `maximum_age_minutes: 60` |
| Referential integrity | `row_count`, `orphan_count` | `maximum_orphan_ratio: 0.001` |
| Distribution anomaly | `current_value`, `baseline_mean`, `baseline_stddev` | `maximum_z_score: 3` |

## Run, inspect, and resolve quality work

Manual execution returns a durable queued run and a `Location` response header. The worker executes it asynchronously; clients should poll the run endpoint. Scheduled runs use the same queue and worker path. The local platform includes a worker and scheduler process; the scheduler checks due rules every minute and creates runs from the latest profile snapshot.

```bash
curl -X POST http://localhost:8000/api/v1/quality/assets/ASSET_ID/runs \
  -H 'Content-Type: application/json' \
  -H 'X-Quality-Actor: data-steward@example.com' \
  -d '{}'

curl http://localhost:8000/api/v1/quality/runs/RUN_ID
curl 'http://localhost:8000/api/v1/quality/incidents?asset_id=ASSET_ID'
```

High- and critical-severity failures create or update an unresolved incident. The incident retains its latest evidence and supports assignee, status, and append-only investigation comments.

```bash
curl -X PATCH http://localhost:8000/api/v1/quality/incidents/INCIDENT_ID \
  -H 'Content-Type: application/json' \
  -d '{"status":"acknowledged", "assignee":"data-owner@example.com"}'

curl -X POST http://localhost:8000/api/v1/quality/incidents/INCIDENT_ID/comments \
  -H 'Content-Type: application/json' \
  -d '{"author":"data-owner@example.com", "body":"Root cause identified; source repair is in progress."}'
```

## North-star metric

The critical coverage endpoint returns the percentage of critical assets with an accountable owner and a recent successful explainable run. It provides explicit exclusion reasons so a zero or low rate is actionable.

```bash
curl 'http://localhost:8000/api/v1/quality/metrics/critical-coverage?recency_hours=24'
```

## Deployment and safety notes

The quality API, database migration job, worker, and scheduler are included in the local Compose topology. Use `docker compose --env-file .env -f infra/docker-compose.yml up --build` after setting the local environment values. The worker uses JSON-only messages and a dedicated `quality` queue.

This increment does not allow arbitrary SQL rule expressions. That is deliberate: profile-based rules are deterministic and explainable. A future warehouse profiling adapter should populate the existing profile schema using parameterized, least-privilege queries. It should not bypass the durable run, result, incident, and evidence model.
