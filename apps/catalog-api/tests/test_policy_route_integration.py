from test_policy_api import build_client, create_asset, headers


def test_certification_route_stops_before_mutation_when_policy_requires_human_approval(monkeypatch, tmp_path) -> None:
    client, secret = build_client(monkeypatch, tmp_path)
    with client:
        asset_id = create_asset("tenant-a")
        from app.db.session import SessionLocal
        from app.models.catalog import CertificationRequest, UsageDecisionStatus

        db = SessionLocal()
        db.info["tenant_id"] = "tenant-a"
        certification = CertificationRequest(asset_id=asset_id, requested_by="analyst@example.com")
        db.add(certification)
        db.commit()
        certification_id = certification.id
        db.close()

        response = client.post(
            f"/api/v1/governance/certification-requests/{certification_id}/decision",
            json={"status": "approved", "decision_note": "Attempted without current quality evidence"},
            headers=headers(secret, "steward@example.com", ["data_steward"], "tenant-a"),
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "policy_requires_human_approval"

        db = SessionLocal()
        db.info["tenant_id"] = "tenant-a"
        persisted = db.get(CertificationRequest, certification_id)
        assert persisted is not None
        assert persisted.status == UsageDecisionStatus.PENDING
        db.close()

        events = client.get(
            "/api/v1/audit-events/",
            headers=headers(secret, "admin@example.com", ["platform_admin"], "tenant-a"),
        ).json()["items"]

    policy_event = next(event for event in events if event["action"] == "policy.decision")
    assert policy_event["outcome"] == "requires_human_approval"
    denied_route_event = next(event for event in events if event["action"] == "certification.decide" and event["outcome"] == "denied")
    assert denied_route_event["metadata_json"]["policy_outcome"] == "requires_human_approval"


def test_policy_audit_failure_blocks_asset_curation(monkeypatch, tmp_path) -> None:
    client, secret = build_client(monkeypatch, tmp_path)
    with client:
        asset_id = create_asset("tenant-a")

        def fail_audit(*_args, **_kwargs):
            raise RuntimeError("audit store unavailable")

        monkeypatch.setattr("app.services.policy_service.record_audit_event", fail_audit)
        response = client.patch(
            f"/api/v1/assets/{asset_id}",
            json={"description": "This mutation must not be saved"},
            headers=headers(secret, "owner@example.com", ["data_owner"], "tenant-a"),
        )
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "policy_unavailable"

        from app.db.session import SessionLocal
        from app.models.catalog import Asset

        db = SessionLocal()
        db.info["tenant_id"] = "tenant-a"
        persisted = db.get(Asset, asset_id)
        assert persisted is not None
        assert persisted.description is None
        db.close()
