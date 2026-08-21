import pytest

from test_policy_api import build_client, create_asset, headers


@pytest.mark.parametrize(
    ("role", "subject", "tenant", "asset_tenant", "classification", "owner", "action", "purpose", "expected"),
    [
        ("analyst", "analyst@example.com", "tenant-a", "tenant-a", None, "owner@example.com", "asset.read", "catalog analysis", "allow"),
        ("read_only", "reader@example.com", "tenant-a", "tenant-a", "payment_data", "owner@example.com", "asset.read", None, "deny"),
        ("analyst", "analyst@example.com", "tenant-a", "tenant-a", "payment_data", "owner@example.com", "asset.read", "financial reporting analysis", "allow_with_obligations"),
        ("data_owner", "owner@example.com", "tenant-a", "tenant-a", None, "owner@example.com", "asset.curate", None, "allow"),
        ("data_owner", "other-owner@example.com", "tenant-a", "tenant-a", None, "owner@example.com", "asset.curate", None, "deny"),
        ("analyst", "analyst@example.com", "tenant-b", "tenant-a", None, "owner@example.com", "asset.read", "catalog analysis", "deny"),
    ],
)
def test_role_tenant_asset_classification_purpose_action_matrix(
    monkeypatch,
    tmp_path,
    role: str,
    subject: str,
    tenant: str,
    asset_tenant: str,
    classification: str | None,
    owner: str,
    action: str,
    purpose: str | None,
    expected: str,
) -> None:
    client, secret = build_client(monkeypatch, tmp_path)
    with client:
        asset_id = create_asset(asset_tenant)
        from app.db.session import SessionLocal
        from app.models.catalog import Asset

        db = SessionLocal()
        db.info["tenant_id"] = asset_tenant
        asset = db.get(Asset, asset_id)
        assert asset is not None
        asset.classification = classification
        asset.owner = owner
        db.commit()
        db.close()

        response = client.post(
            "/api/v1/policy/decisions",
            json={
                "action": action,
                "resource": {"resource_type": "asset", "resource_id": asset_id},
                "purpose": purpose,
                "context": {},
            },
            headers=headers(secret, subject, [role], tenant),
        )

    assert response.status_code == 200
    assert response.json()["outcome"] == expected
