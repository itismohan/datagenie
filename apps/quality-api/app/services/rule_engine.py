from dataclasses import dataclass
from datetime import datetime, timezone
from math import isclose
from typing import Any

from app.models.quality import QualityRule, RuleType


@dataclass(frozen=True)
class Evaluation:
    evaluated: bool
    passed: bool
    score: int
    observed_value: dict[str, Any]
    expected_value: dict[str, Any]
    evidence: dict[str, Any]
    explanation: str


def _as_number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _scope(profile: dict[str, Any], column_name: str | None) -> tuple[dict[str, Any], dict[str, Any]]:
    if column_name:
        column_profile = profile.get("columns", {}).get(column_name)
        if not isinstance(column_profile, dict):
            return {}, {"scope": "column", "column_name": column_name, "missing_profile": True}
        return column_profile, {"scope": "column", "column_name": column_name, "sample_rows": column_profile.get("sample_rows", [])}
    return profile, {"scope": "asset", "sample_rows": profile.get("sample_rows", [])}


def _not_evaluable(rule: QualityRule, evidence: dict[str, Any], message: str) -> Evaluation:
    return Evaluation(
        evaluated=False,
        passed=False,
        score=0,
        observed_value={},
        expected_value=dict(rule.parameters),
        evidence=evidence,
        explanation=message,
    )


def _ratio_evaluation(
    rule: QualityRule, numerator: float, denominator: float, threshold: float, label: str, evidence: dict[str, Any], greater_or_equal: bool = True
) -> Evaluation:
    if denominator <= 0:
        return _not_evaluable(rule, evidence, f"{label} could not be evaluated because row_count must be greater than zero.")
    ratio = numerator / denominator
    passed = ratio >= threshold if greater_or_equal else ratio <= threshold
    comparator = ">=" if greater_or_equal else "<="
    return Evaluation(
        evaluated=True,
        passed=passed,
        score=100 if passed else 0,
        observed_value={"ratio": ratio, "numerator": numerator, "denominator": denominator},
        expected_value={"threshold": threshold, "comparator": comparator},
        evidence=evidence,
        explanation=f"{label} ratio {ratio:.4f} {comparator} required threshold {threshold:.4f}: {'passed' if passed else 'failed'}.",
    )


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def evaluate_rule(rule: QualityRule, profile_snapshot: dict[str, Any], now: datetime | None = None) -> Evaluation:
    """Evaluate a declarative rule from a durable profile snapshot; never execute arbitrary SQL."""
    now = now or datetime.now(timezone.utc)
    profile, evidence = _scope(profile_snapshot, rule.column_name)
    if not profile:
        return _not_evaluable(rule, evidence, f"No profile evidence exists for rule scope {rule.column_name or 'asset'}.")
    row_count = _as_number(profile.get("row_count"))

    if rule.rule_type == RuleType.COMPLETENESS:
        null_count = _as_number(profile.get("null_count"))
        if row_count is None or null_count is None:
            return _not_evaluable(rule, evidence, "Completeness requires row_count and null_count evidence.")
        evidence.update({"row_count": row_count, "null_count": null_count})
        return _ratio_evaluation(rule, row_count - null_count, row_count, float(rule.parameters["minimum_ratio"]), "Completeness", evidence)

    if rule.rule_type == RuleType.UNIQUENESS:
        distinct_count = _as_number(profile.get("distinct_count"))
        if row_count is None or distinct_count is None:
            return _not_evaluable(rule, evidence, "Uniqueness requires row_count and distinct_count evidence.")
        evidence.update({"row_count": row_count, "distinct_count": distinct_count})
        return _ratio_evaluation(rule, distinct_count, row_count, float(rule.parameters["minimum_ratio"]), "Uniqueness", evidence)

    if rule.rule_type == RuleType.VALIDITY:
        invalid_count = _as_number(profile.get("invalid_count"))
        if row_count is None or invalid_count is None:
            return _not_evaluable(rule, evidence, "Validity requires row_count and invalid_count evidence.")
        evidence.update({"row_count": row_count, "invalid_count": invalid_count})
        return _ratio_evaluation(rule, row_count - invalid_count, row_count, float(rule.parameters["minimum_ratio"]), "Validity", evidence)

    if rule.rule_type == RuleType.FRESHNESS:
        latest_record_at = _parse_timestamp(profile.get("latest_record_at"))
        if latest_record_at is None:
            return _not_evaluable(rule, evidence, "Freshness requires a valid latest_record_at timestamp.")
        maximum_age = float(rule.parameters["maximum_age_minutes"])
        observed_age = max(0.0, (now - latest_record_at).total_seconds() / 60)
        passed = observed_age <= maximum_age
        evidence.update({"latest_record_at": latest_record_at.isoformat(), "evaluated_at": now.isoformat()})
        return Evaluation(
            evaluated=True,
            passed=passed,
            score=100 if passed else 0,
            observed_value={"age_minutes": observed_age},
            expected_value={"maximum_age_minutes": maximum_age},
            evidence=evidence,
            explanation=f"Freshness age {observed_age:.2f} minutes <= maximum {maximum_age:.2f}: {'passed' if passed else 'failed'}.",
        )

    if rule.rule_type == RuleType.REFERENTIAL_INTEGRITY:
        orphan_count = _as_number(profile.get("orphan_count"))
        if row_count is None or orphan_count is None:
            return _not_evaluable(rule, evidence, "Referential integrity requires row_count and orphan_count evidence.")
        evidence.update({"row_count": row_count, "orphan_count": orphan_count, "related_asset_id": profile.get("related_asset_id")})
        return _ratio_evaluation(
            rule,
            orphan_count,
            row_count,
            float(rule.parameters["maximum_orphan_ratio"]),
            "Referential-integrity orphan",
            evidence,
            greater_or_equal=False,
        )

    if rule.rule_type == RuleType.DISTRIBUTION_ANOMALY:
        current = _as_number(profile.get("current_value"))
        mean = _as_number(profile.get("baseline_mean"))
        stddev = _as_number(profile.get("baseline_stddev"))
        if current is None or mean is None or stddev is None:
            return _not_evaluable(rule, evidence, "Distribution anomaly requires current_value, baseline_mean, and baseline_stddev evidence.")
        if stddev < 0:
            return _not_evaluable(rule, evidence, "Distribution anomaly baseline_stddev cannot be negative.")
        if isclose(stddev, 0.0):
            z_score = 0.0 if isclose(current, mean) else float("inf")
        else:
            z_score = abs(current - mean) / stddev
        maximum = float(rule.parameters["maximum_z_score"])
        passed = z_score <= maximum
        evidence.update({"current_value": current, "baseline_mean": mean, "baseline_stddev": stddev})
        return Evaluation(
            evaluated=True,
            passed=passed,
            score=100 if passed else 0,
            observed_value={"z_score": z_score},
            expected_value={"maximum_z_score": maximum},
            evidence=evidence,
            explanation=f"Distribution z-score {z_score:.4f} <= maximum {maximum:.4f}: {'passed' if passed else 'failed'}.",
        )

    return _not_evaluable(rule, evidence, f"Unsupported rule type {rule.rule_type.value}.")
