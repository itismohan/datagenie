from fastapi.testclient import TestClient

from app.main import app


def test_openapi_contract_exposes_curated_documentation_and_security_boundaries():
    schema = app.openapi()

    assert schema["openapi"] == "3.1.0"
    assert schema["info"]["version"] == "1.0.0"
    assert schema["servers"] == [{"url": "/", "description": "Current environment through the DataGenie TLS ingress"}]
    assert "BearerAuth" in schema["components"]["securitySchemes"]
    assert "ErrorEnvelope" in schema["components"]["schemas"]
    assert "RequestId" in schema["components"]["parameters"]

    protected = schema["paths"]["/api/v1/assets/"]["get"]
    assert protected["security"] == [{"BearerAuth": []}]
    assert "401" in protected["responses"]
    assert "429" in protected["responses"]
    assert any(parameter.get("$ref") == "#/components/parameters/RequestId" for parameter in protected["parameters"])

    health = schema["paths"]["/health"]["get"]
    assert "security" not in health


def test_interactive_documentation_and_openapi_routes_are_available():
    client = TestClient(app)

    openapi = client.get("/api/openapi.json")
    swagger = client.get("/api/docs")
    redoc = client.get("/api/redoc")

    assert openapi.status_code == 200
    assert openapi.json()["info"]["version"] == "1.0.0"
    assert swagger.status_code == 200
    assert "Swagger UI" in swagger.text
    assert redoc.status_code == 200
    assert "ReDoc" in redoc.text
