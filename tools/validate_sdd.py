#!/usr/bin/env python3
"""Validate DataGenie's specification-driven development baseline.

The validator is deliberately lightweight: it checks repository-native artifact
presence and the traceability manifest required for material changes. It runs in
CI without depending on an external SDD product or a hosted service.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "specs"
CHANGES = SPECS / "changes"
REQUIRED_TEMPLATES = {
    "proposal.md",
    "requirements.md",
    "design.md",
    "threat-model.md",
    "contracts.md",
    "test-plan.md",
    "rollout.md",
    "evidence.md",
    "traceability.yaml",
}
REQUIRED_CHANGE_ARTIFACTS = REQUIRED_TEMPLATES
CHANGE_ID_PATTERN = re.compile(r"^[0-9]{4}-[a-z0-9]+(?:-[a-z0-9]+)*$")
REQUIREMENT_ID_PATTERN = re.compile(r"^DG-[A-Z][A-Z0-9_]*(?:-[A-Z][A-Z0-9_]*)*-[0-9]{3,}$")
PR_CHANGE_PATTERN = re.compile(r"SDD_CHANGE_ID:\s*([0-9]{4}-[a-z0-9]+(?:-[a-z0-9]+)*)")
PR_EXEMPT_PATTERN = re.compile(r"SDD-EXEMPT:\s*(\S.+)")


class ValidationError(Exception):
    """Raised when a required SDD control is absent or inconsistent."""


def fail(message: str) -> None:
    raise ValidationError(message)


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        fail(f"{path.relative_to(ROOT)} is not valid YAML: {exc}")
    if not isinstance(payload, dict):
        fail(f"{path.relative_to(ROOT)} must contain a YAML mapping.")
    return payload


def validate_baseline() -> None:
    required_paths = {SPECS / "constitution.md", SPECS / "README.md", SPECS / "schemas" / "traceability.schema.json"}
    required_paths.update(SPECS / "templates" / template for template in REQUIRED_TEMPLATES)
    missing = [path.relative_to(ROOT).as_posix() for path in sorted(required_paths) if not path.is_file()]
    if missing:
        fail(f"SDD baseline is incomplete; missing: {', '.join(missing)}")
    try:
        json.loads((SPECS / "schemas" / "traceability.schema.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"specs/schemas/traceability.schema.json is invalid JSON: {exc}")


def validate_manifest(path: Path) -> None:
    payload = load_yaml(path)
    change_id = payload.get("change_id")
    if not isinstance(change_id, str) or not CHANGE_ID_PATTERN.fullmatch(change_id):
        fail(f"{path.relative_to(ROOT)} has an invalid change_id.")
    if path.parent.name != change_id:
        fail(f"{path.relative_to(ROOT)} change_id must match its directory name.")
    if not isinstance(payload.get("title"), str) or len(payload["title"].strip()) < 8:
        fail(f"{path.relative_to(ROOT)} must declare a descriptive title.")
    if payload.get("status") not in {"draft", "in_review", "approved", "implementing", "released", "archived"}:
        fail(f"{path.relative_to(ROOT)} has an invalid status.")
    requirements = payload.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        fail(f"{path.relative_to(ROOT)} must map at least one requirement.")
    seen_ids: set[str] = set()
    for requirement in requirements:
        if not isinstance(requirement, dict):
            fail(f"{path.relative_to(ROOT)} has a non-mapping requirement entry.")
        requirement_id = requirement.get("id")
        if not isinstance(requirement_id, str) or not REQUIREMENT_ID_PATTERN.fullmatch(requirement_id):
            fail(f"{path.relative_to(ROOT)} has an invalid requirement ID.")
        if requirement_id in seen_ids:
            fail(f"{path.relative_to(ROOT)} repeats requirement ID {requirement_id}.")
        seen_ids.add(requirement_id)
        if not isinstance(requirement.get("statement"), str) or len(requirement["statement"].strip()) < 20:
            fail(f"{path.relative_to(ROOT)} requirement {requirement_id} needs a testable statement.")
        for key in ("implementation", "tests", "evidence"):
            value = requirement.get(key)
            if not isinstance(value, list) or not value or not all(isinstance(item, str) and item.strip() for item in value):
                fail(f"{path.relative_to(ROOT)} requirement {requirement_id} needs non-empty {key} references.")


def validate_change_artifacts() -> None:
    if not CHANGES.is_dir():
        fail("specs/changes directory is missing.")
    for directory in sorted(path for path in CHANGES.iterdir() if path.is_dir()):
        if directory.name.startswith("."):
            continue
        if not CHANGE_ID_PATTERN.fullmatch(directory.name):
            fail(f"Change directory {directory.relative_to(ROOT)} must use NNNN-lowercase-kebab-case.")
        missing = [name for name in sorted(REQUIRED_CHANGE_ARTIFACTS) if not (directory / name).is_file()]
        if missing:
            fail(f"{directory.relative_to(ROOT)} is missing required artifacts: {', '.join(missing)}")
        validate_manifest(directory / "traceability.yaml")
        tasks = directory / "tasks.md"
        if tasks.is_file() and f"**Change ID:** {directory.name}" not in tasks.read_text(encoding="utf-8"):
            fail(f"{tasks.relative_to(ROOT)} must declare '**Change ID:** {directory.name}'.")


def changed_files(base: str, head: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{head}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def is_material_path(path: str) -> bool:
    if path.startswith(("specs/", ".github/", "docs/")):
        return False
    if path in {".DS_Store"}:
        return False
    return path.startswith(("apps/", "infra/", "tools/")) or path in {".env.example", "docker-compose.yml"}


def validate_pull_request_context() -> None:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path or not Path(event_path).is_file():
        return
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    pull_request = event.get("pull_request")
    if not isinstance(pull_request, dict):
        return
    body = str(pull_request.get("body") or "")
    base_sha = str(pull_request.get("base", {}).get("sha") or "")
    head_sha = str(pull_request.get("head", {}).get("sha") or "")
    if not base_sha or not head_sha:
        fail("Pull request event is missing base/head revisions for SDD validation.")
    material_files = [path for path in changed_files(base_sha, head_sha) if is_material_path(path)]
    if not material_files:
        return
    change_match = PR_CHANGE_PATTERN.search(body)
    exempt_match = PR_EXEMPT_PATTERN.search(body)
    if bool(change_match) == bool(exempt_match):
        fail("Material pull requests must include exactly one 'SDD_CHANGE_ID: NNNN-slug' or 'SDD-EXEMPT: reason' declaration.")
    if exempt_match:
        return
    change_id = change_match.group(1)
    change_directory = CHANGES / change_id
    if not change_directory.is_dir():
        fail(f"Pull request references missing change specification specs/changes/{change_id}.")
    validate_manifest(change_directory / "traceability.yaml")


def main() -> int:
    try:
        validate_baseline()
        validate_change_artifacts()
        validate_pull_request_context()
    except ValidationError as exc:
        print(f"SDD validation failed: {exc}", file=sys.stderr)
        return 1
    print("SDD baseline and traceability validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
