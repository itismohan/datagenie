# DataGenie Trustworthy Quality Foundation Contract

## Product boundaries

Quality is an evidence-backed technical signal, not a certification decision. DataGenie stores technical quality, business criticality, certification status, and accountability independently so that an excellent technical score cannot make an uncertified or low-context dataset appear automatically suitable for use.

| Signal | Meaning | Managed by |
|---|---|---|
| Technical quality | Deterministic rule outcomes calculated from an execution snapshot | Quality engine and data steward |
| Business criticality | Business impact tier: `low`, `medium`, `high`, or `critical` | Asset owner or data steward |
| Certification status | Governance decision: `under_review`, `certified`, or `deprecated` | Data owner or data steward |
| Accountability | Named rule owner, incident assignee, and critical-asset owner | Data owner or data steward |

## Durable domain model

| Record | Purpose |
|---|---|
| `quality_rules` | Versioned, owner-assigned rule definition with target asset or column, parameters, threshold, schedule, and enabled state |
| `quality_runs` | Immutable queued, running, succeeded, failed, or cancelled execution record; captures trigger, snapshot, score, and effective rule versions |
| `quality_rule_results` | One explainable result per effective rule version: observed and expected values, pass/fail, score impact, sampled evidence, and row/column scope |
| `quality_incidents` | Operational incident created for failed high-severity checks; includes status, severity, assignee, evidence, and timestamps |
| `quality_incident_comments` | Resolution and investigation history; comments are append-only and attributed |
| `asset_quality_contexts` | Quality context independent of catalog certification: business criticality, accountable owner, latest explainable run, and technical score |

## Initial deterministic rule set

Rules use safe, declarative profile snapshots rather than arbitrary SQL expressions. A run receives a data-profile snapshot per asset or column. Production connectors can populate the same schema from warehouse queries without changing rule semantics.

| Rule type | Required snapshot evidence | Parameters | Pass condition |
|---|---|---|---|
| `completeness` | `row_count`, `null_count` | `minimum_ratio` | `(row_count - null_count) / row_count >= minimum_ratio` |
| `uniqueness` | `row_count`, `distinct_count` | `minimum_ratio` | `distinct_count / row_count >= minimum_ratio` |
| `validity` | `row_count`, `invalid_count` | `minimum_ratio` | `(row_count - invalid_count) / row_count >= minimum_ratio` |
| `freshness` | `observed_at`, `latest_record_at` | `maximum_age_minutes` | Latest record age is within the threshold |
| `referential_integrity` | `row_count`, `orphan_count`, related asset/column | `maximum_orphan_ratio` | `orphan_count / row_count <= maximum_orphan_ratio` |
| `distribution_anomaly` | `current_value`, `baseline_mean`, `baseline_stddev` | `maximum_z_score` | Absolute z-score is within the threshold |

Each result persists the observed numerator and denominator, threshold, calculation, scope, rule version, and evidence snapshot. A score is marked explainable only when every evaluated rule has this payload.

## Execution and scheduling contract

A manual API trigger creates a durable `quality_run` in `queued` state and dispatches a worker task. The worker records effective rule versions, turns the run `running`, evaluates enabled rules, persists results and score, opens or updates incidents, and commits `succeeded` or `failed`. The API never returns a synthetic score and does not treat queued or failed work as authoritative.

Rules may have a `schedule_cron` and `next_run_at`. A scheduling task selects enabled due rules, groups them by asset, creates durable `scheduled` runs, and dispatches them through the same worker path. This preserves one execution model for manual and scheduled checks.

## Score and incident behavior

A quality run score is the weighted percentage of passing evaluated rules. A score is `null` when no eligible rules run. The run exposes `explainable=true` only if it has at least one result and each result contains an evidence payload and rule version.

A failed rule opens an incident when its severity is `high` or `critical`; repeated failure of an unresolved incident updates its last-seen timestamp and evidence rather than creating unbounded duplicates. Incidents require an explicit status transition and record comments for investigation and resolution history.

## North-star metric

> **Critical asset coverage** is the percentage of assets marked `critical` that have an accountable owner and a recent successful, explainable run within the configured freshness window.

The metric is reported with numerator, denominator, configured recency window, and explicit exclusion reasons. Certification status is displayed next to, but never blended into, the technical quality score.
