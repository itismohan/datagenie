from datetime import datetime, timezone
from typing import Any, Literal

from app.db.neo4j import get_session
from app.schemas.lineage import LineageEventCreate, LineageNodeInput


ALLOWED_RELATIONSHIPS = {"FLOWS_TO", "DERIVES_FROM", "CONSUMES", "COLUMN_FLOWS_TO"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def node_properties(node: LineageNodeInput) -> dict[str, Any]:
    return {
        "id": node.id,
        "node_type": node.node_type,
        "display_name": node.display_name or node.id,
        "owner": node.owner,
        "domain": node.domain,
        "business_criticality": node.business_criticality,
        "updated_at": utc_now(),
    }


def ingest_lineage_event(event: LineageEventCreate) -> dict[str, Any]:
    relationship = event.relationship_type
    if relationship not in ALLOWED_RELATIONSHIPS:
        raise ValueError("Unsupported lineage relationship type.")
    query = f"""
    MERGE (source:LineageNode {{id: $source_id}})
    SET source += $source_properties
    MERGE (target:LineageNode {{id: $target_id}})
    SET target += $target_properties
    MERGE (source)-[edge:{relationship} {{event_id: $event_id}}]->(target)
    SET edge.source_provenance = $source_provenance,
        edge.confidence = $confidence,
        edge.observed_at = $observed_at,
        edge.created_at = coalesce(edge.created_at, $created_at),
        edge.metadata = $metadata
    RETURN edge.event_id AS event_id, source.id AS source_id, target.id AS target_id, type(edge) AS relationship_type
    """
    with get_session() as session:
        record = session.run(
            query,
            source_id=event.source.id,
            target_id=event.target.id,
            source_properties=node_properties(event.source),
            target_properties=node_properties(event.target),
            event_id=event.event_id,
            source_provenance=event.source_provenance,
            confidence=event.confidence,
            observed_at=event.observed_at.isoformat(),
            created_at=utc_now(),
            metadata=event.metadata,
        ).single()
        return dict(record.data()) if record else {"event_id": event.event_id}


def _traversal_query(direction: Literal["upstream", "downstream", "both"], max_depth: int) -> str:
    if direction == "upstream":
        pattern = f"(focal:LineageNode {{id: $asset_id}})<-[edges*1..{max_depth}]-(node:LineageNode)"
    elif direction == "downstream":
        pattern = f"(focal:LineageNode {{id: $asset_id}})-[edges*1..{max_depth}]->(node:LineageNode)"
    else:
        pattern = f"(focal:LineageNode {{id: $asset_id}})-[edges*1..{max_depth}]-(node:LineageNode)"
    return f"""
    MATCH path={pattern}
    UNWIND nodes(path) AS graph_node
    WITH collect(DISTINCT graph_node) AS nodes, collect(DISTINCT edges) AS edge_paths
    UNWIND edge_paths AS relationship_path
    UNWIND relationship_path AS edge
    WITH nodes, collect(DISTINCT edge) AS edges
    RETURN [node IN nodes | properties(node)] AS nodes,
           [edge IN edges | properties(edge) + {{relationship_type: type(edge), source_id: startNode(edge).id, target_id: endNode(edge).id}}] AS edges
    """


def get_lineage(asset_id: str, direction: Literal["upstream", "downstream", "both"] = "both", max_depth: int = 5) -> dict[str, Any]:
    with get_session() as session:
        record = session.run(_traversal_query(direction, max_depth), asset_id=asset_id).single()
        if not record:
            return {"focal_asset_id": asset_id, "direction": direction, "nodes": [], "edges": []}
        data = record.data()
        return {"focal_asset_id": asset_id, "direction": direction, "nodes": data.get("nodes", []), "edges": data.get("edges", [])}


def _record_operational_event(asset_id: str, event_reference: str, impact_type: str, metadata: dict[str, Any]) -> None:
    with get_session() as session:
        session.run(
            """
            MERGE (event:OperationalEvent {id: $event_reference})
            SET event.impact_type = $impact_type, event.metadata = $metadata,
                event.updated_at = $updated_at, event.created_at = coalesce(event.created_at, $created_at)
            MERGE (asset:LineageNode {id: $asset_id})
            MERGE (event)-[:AFFECTS]->(asset)
            """,
            event_reference=event_reference,
            impact_type=impact_type,
            metadata=metadata,
            asset_id=asset_id,
            updated_at=utc_now(),
            created_at=utc_now(),
        )


def downstream_impact(asset_id: str, max_depth: int, impact_type: str, event_reference: str | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    if event_reference:
        _record_operational_event(asset_id, event_reference, impact_type, metadata or {})
    query = f"""
    MATCH path=(focal:LineageNode {{id: $asset_id}})-[edges*1..{max_depth}]->(consumer:LineageNode)
    WITH consumer, min(length(path)) AS distance,
         max(reduce(minimum = 100, edge IN edges | CASE WHEN coalesce(edge.confidence, 0) < minimum THEN coalesce(edge.confidence, 0) ELSE minimum END)) AS minimum_confidence
    RETURN consumer.id AS asset_id,
           consumer.node_type AS node_type,
           consumer.display_name AS display_name,
           consumer.owner AS owner,
           consumer.domain AS domain,
           consumer.business_criticality AS business_criticality,
           minimum_confidence,
           distance
    ORDER BY CASE consumer.business_criticality WHEN 'critical' THEN 1 WHEN 'high' THEN 2 ELSE 3 END, distance, consumer.id
    """
    with get_session() as session:
        consumers = [dict(record.data()) for record in session.run(query, asset_id=asset_id)]
    return {"impact_type": impact_type, "asset_id": asset_id, "event_reference": event_reference, "consumers": consumers}
