"""Regression checks for non-secret staging Compose interpolation in CI."""

from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_ci_staging_compose_validation_supplies_required_mcp_placeholders() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()

    assert "DATAGENIE_AUTH_OIDC_AUDIENCE=datagenie-mcp" in workflow
    assert "DATAGENIE_AUTH_OIDC_ISSUER=https://auth.example.invalid" in workflow
    assert "DATAGENIE_AUTH_OIDC_JWKS_URL=https://auth.example.invalid/.well-known/jwks.json" in workflow
    assert "DATAGENIE_LEDGER_DATABASE_URL=postgresql+psycopg://" in workflow


def test_environment_template_documents_the_mcp_oidc_audience() -> None:
    environment = (ROOT / ".env.example").read_text()

    assert "DATAGENIE_AUTH_OIDC_AUDIENCE=datagenie-mcp" in environment
