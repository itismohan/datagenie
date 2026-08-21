from test_policy_api import build_client, create_asset


def test_private_transport_adapter_matches_rest_policy_semantics(monkeypatch, tmp_path) -> None:
    client, _ = build_client(monkeypatch, tmp_path)
    with client:
        asset_id = create_asset("tenant-a")
        from app.core.security import Principal
        from app.db.session import SessionLocal
        from app.services.policy_adapter import evaluate_transport_policy
        from app.services.policy_service import evaluate_rest_policy

        db = SessionLocal()
        db.info["tenant_id"] = "tenant-a"
        principal = Principal(subject="analyst@example.com", tenant_id="tenant-a", roles=frozenset({"analyst"}))
        rest_decision = evaluate_rest_policy(
            db,
            principal=principal,
            action="asset.read",
            resource_type="asset",
            resource_id=asset_id,
            purpose="catalog analysis",
            request_id="rest-policy-fixture",
        )
        db.commit()
        adapter_decision = evaluate_transport_policy(
            db,
            principal=principal,
            action="asset.read",
            resource_type="asset",
            resource_id=asset_id,
            purpose="catalog analysis",
            request_id="adapter-policy-fixture",
        )
        db.commit()
        db.close()

    assert adapter_decision.outcome == rest_decision.outcome
    assert adapter_decision.rule_ids == rest_decision.rule_ids
    assert adapter_decision.obligations == rest_decision.obligations
    assert adapter_decision.resource_visible == rest_decision.resource_visible


def test_private_transport_adapter_keeps_foreign_tenant_resource_non_visible(monkeypatch, tmp_path) -> None:
    client, _ = build_client(monkeypatch, tmp_path)
    with client:
        asset_id = create_asset("tenant-a")
        from app.core.security import Principal
        from app.db.session import SessionLocal
        from app.services.policy_adapter import evaluate_transport_policy

        db = SessionLocal()
        db.info["tenant_id"] = "tenant-b"
        principal = Principal(subject="analyst@example.com", tenant_id="tenant-b", roles=frozenset({"analyst"}))
        decision = evaluate_transport_policy(
            db,
            principal=principal,
            action="asset.read",
            resource_type="asset",
            resource_id=asset_id,
            purpose="catalog analysis",
            request_id="adapter-foreign-tenant",
        )
        db.commit()
        db.close()

    assert decision.outcome.value == "deny"
    assert decision.resource_visible is False
    assert decision.rule_ids == ("DG-POLICY-TENANT-NONVISIBLE",)
