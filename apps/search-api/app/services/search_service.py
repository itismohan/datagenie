
# Elasticsearch / OpenSearch abstraction
def index_asset(asset: dict):
    return True

def search_assets(query: str):
    return [
        {"id": "1", "name": "orders"},
        {"id": "2", "name": "customers"}
    ]
