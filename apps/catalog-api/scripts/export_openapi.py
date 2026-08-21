"""Export the catalog OpenAPI contract for review, client generation, and CI drift checks.

Run from the repository root:
    python3 apps/catalog-api/scripts/export_openapi.py
"""

import json
import os
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
APPLICATION_ROOT = REPOSITORY_ROOT / "apps" / "catalog-api"
OUTPUT_PATH = REPOSITORY_ROOT / "docs" / "openapi" / "catalog-api-v1.json"


# The schema is configuration-independent and must be generated without production secrets.
os.environ.setdefault("DATAGENIE_ENVIRONMENT", "development")
os.environ.setdefault("DATAGENIE_AUTH_ENABLED", "false")
os.environ.setdefault("DATAGENIE_DATABASE_URL", "sqlite:///./datagenie_openapi_export.db")
sys.path.insert(0, str(APPLICATION_ROOT))

from app.main import app  # noqa: E402


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Exported OpenAPI {app.version} contract to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
