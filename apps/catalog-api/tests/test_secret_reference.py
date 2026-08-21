import pytest
from pydantic import ValidationError

from app.schemas.catalog import SourceCreate


def source_payload(secret_ref: str) -> dict:
    return {
        "name": "finance-warehouse",
        "source_type": "postgresql",
        "host": "warehouse.internal",
        "database_name": "finance",
        "username": "catalog_reader",
        "secret_ref": secret_ref,
    }


def test_connector_source_rejects_raw_passwords_and_accepts_external_secret_references():
    with pytest.raises(ValidationError, match="external secret reference"):
        SourceCreate.model_validate(source_payload("actual-production-password"))

    source = SourceCreate.model_validate(source_payload("vault://kv/datagenie/finance-warehouse"))
    assert source.secret_ref == "vault://kv/datagenie/finance-warehouse"
