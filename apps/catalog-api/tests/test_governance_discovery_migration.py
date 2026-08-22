"""Regression checks for named PostgreSQL enums used by governed discovery."""

from pathlib import Path


MIGRATION = Path(__file__).parents[1] / "alembic" / "versions" / "20260821_04_governance_discovery.py"


def test_governance_discovery_creates_named_enums_before_batch_alter() -> None:
    source = MIGRATION.read_text()

    enum_creation = source.index("enum_type.create(bind, checkfirst=True)")
    glossary_batch_alter = source.index('with op.batch_alter_table("business_glossary_terms")')

    assert enum_creation < glossary_batch_alter
    for enum_name in (
        "glossarystatus",
        "classificationtype",
        "reviewstatus",
        "discoveryeventtype",
        "usagedecisionstatus",
        "suggestiontype",
    ):
        assert enum_name in source


def test_governance_discovery_downgrade_drops_named_enums() -> None:
    source = MIGRATION.read_text()
    downgrade = source[source.index("def downgrade() -> None:") :]

    assert 'sa.Enum(name=enum_name).drop(bind, checkfirst=True)' in downgrade
