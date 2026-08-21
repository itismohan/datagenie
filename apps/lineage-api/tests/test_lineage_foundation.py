from datetime import datetime, timezone

from app.schemas.lineage import LineageEventCreate
from app.services import lineage_service


class FakeRecord:
    def __init__(self, payload):
        self.payload = payload

    def data(self):
        return self.payload


class FakeResult:
    def __init__(self, one=None, many=None):
        self.one = one
        self.many = many or []

    def single(self):
        return FakeRecord(self.one) if self.one is not None else None

    def __iter__(self):
        return iter([FakeRecord(item) for item in self.many])


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def run(self, query, **params):
        self.calls.append((query, params))
        return self.responses.pop(0)


def test_lineage_event_is_typed_provenance_backed_and_idempotent(monkeypatch):
    session = FakeSession([FakeResult(one={"event_id": "evt-1", "source_id": "orders", "target_id": "revenue", "relationship_type": "DERIVES_FROM"})])
    monkeypatch.setattr(lineage_service, "get_session", lambda: session)

    result = lineage_service.ingest_lineage_event(
        LineageEventCreate.model_validate(
            {
                "event_id": "evt-1",
                "source": {"id": "orders", "owner": "orders-owner@example.com", "business_criticality": "critical"},
                "target": {"id": "revenue", "node_type": "dashboard", "owner": "finance@example.com", "domain": "Finance"},
                "relationship_type": "DERIVES_FROM",
                "source_provenance": "dbt-manifest",
                "confidence": 92,
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {"run_id": "dbt-run-77"},
            }
        )
    )

    assert result["relationship_type"] == "DERIVES_FROM"
    query, params = session.calls[0]
    assert "MERGE (source)-[edge:DERIVES_FROM {event_id: $event_id}]->(target)" in query
    assert params["source_provenance"] == "dbt-manifest"
    assert params["confidence"] == 92


def test_lineage_traversal_and_quality_impact_return_downstream_owners_and_criticality(monkeypatch):
    traversal_session = FakeSession(
        [
            FakeResult(
                one={
                    "nodes": [{"id": "orders", "node_type": "asset"}, {"id": "revenue", "node_type": "dashboard", "owner": "finance@example.com"}],
                    "edges": [{"event_id": "evt-1", "source_id": "orders", "target_id": "revenue", "relationship_type": "CONSUMES", "source_provenance": "bi-catalog", "confidence": 95, "observed_at": "2026-08-21T00:00:00+00:00"}],
                }
            )
        ]
    )
    monkeypatch.setattr(lineage_service, "get_session", lambda: traversal_session)
    graph = lineage_service.get_lineage("orders", direction="downstream", max_depth=3)
    assert graph["nodes"][1]["owner"] == "finance@example.com"
    assert "-[edges*1..3]->" in traversal_session.calls[0][0]

    impact_session = FakeSession(
        [
            FakeResult(),
            FakeResult(
                many=[
                    {
                        "asset_id": "revenue",
                        "node_type": "dashboard",
                        "display_name": "Revenue dashboard",
                        "owner": "finance@example.com",
                        "domain": "Finance",
                        "business_criticality": "critical",
                        "minimum_confidence": 95,
                        "distance": 1,
                    }
                ]
            ),
        ]
    )
    monkeypatch.setattr(lineage_service, "get_session", lambda: impact_session)
    impact = lineage_service.downstream_impact(
        "orders",
        4,
        impact_type="quality_incident",
        event_reference="incident-22",
        metadata={"severity": "critical"},
    )
    assert impact["consumers"][0]["owner"] == "finance@example.com"
    assert impact["consumers"][0]["business_criticality"] == "critical"
    assert impact_session.calls[0][1]["event_reference"] == "incident-22"


def test_lineage_health_probes_distinguish_liveness_from_graph_readiness(monkeypatch):
    from app import main

    class ReadySession:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def run(self, query):
            assert query == "RETURN 1 AS ready"
            return FakeResult(one={"ready": 1})

    monkeypatch.setattr(main, "get_session", lambda: ReadySession())
    assert main.health() == {"status": "ok"}
    assert main.liveness() == {"status": "live"}
    assert main.readiness() == {"status": "ready"}

    monkeypatch.setattr(main, "get_session", lambda: (_ for _ in ()).throw(RuntimeError("neo4j offline")))
    try:
        main.readiness()
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 503
    else:
        raise AssertionError("Expected readiness to fail when Neo4j is unavailable")
