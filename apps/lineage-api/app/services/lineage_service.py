
from app.db.neo4j import get_session

def create_lineage(source: str, target: str):
    with get_session() as session:
        session.run(
            "MERGE (s:Asset {id:$source}) "
            "MERGE (t:Asset {id:$target}) "
            "MERGE (s)-[:FLOWS_TO]->(t)",
            source=source, target=target
        )

def get_lineage(asset_id: str):
    with get_session() as session:
        result = session.run(
            "MATCH (a:Asset {id:$id})-[r*1..3]->(b) RETURN a,b",
            id=asset_id
        )
        return [r.data() for r in result]
