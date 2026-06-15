import re
from pathlib import Path

ARCHITECTURE_ROOT = Path(__file__).resolve().parents[2] / "architecture"
CANONICAL_ACCOUNT_TYPES = {"BANK", "CREDIT_CARD", "CASH", "INVESTMENT", "LOAN"}


def _read_doc(relative_path: str) -> str:
    return (ARCHITECTURE_ROOT / relative_path).read_text(encoding="utf-8")


def _extract_account_types_block(
    document: str,
    heading_pattern: str,
    label_pattern: str = "",
) -> set[str]:
    match = re.search(
        rf"{heading_pattern}.*?{label_pattern}\s*```text(?P<body>.*?)```",
        document,
        flags=re.DOTALL,
    )
    assert match is not None
    return {line.strip() for line in match.group("body").splitlines() if line.strip()}


def test_sprint2_roadmap_uses_canonical_account_types() -> None:
    roadmap = _read_doc("14-sprint_roadmap.md")

    account_types = _extract_account_types_block(
        roadmap,
        r"# 7\. Sprint 2",
        "Account Types:",
    )

    assert account_types == CANONICAL_ACCOUNT_TYPES
    assert "`WALLET` is not a separate account type in Sprint 2" in roadmap


def test_bootstrap_prompt_uses_canonical_account_types() -> None:
    bootstrap_prompt = _read_doc("15-ai_project_bootstrap_prompt.md")

    account_types = _extract_account_types_block(
        bootstrap_prompt,
        r"# ACCOUNT TYPES",
    )

    assert account_types == CANONICAL_ACCOUNT_TYPES
    assert "`WALLET` is not a separate Sprint 2 account type" in bootstrap_prompt


def test_account_api_docs_define_archive_and_audit_behavior() -> None:
    api_contracts = _read_doc("08-api_contracts.md")

    assert all(
        account_type in api_contracts for account_type in CANONICAL_ACCOUNT_TYPES
    )
    assert "`WALLET` is not a separate account type" in api_contracts
    assert "DELETE /api/v1/accounts/{account_id}" in api_contracts
    assert "Set status = ARCHIVED" in api_contracts
    assert "Physical deletion is prohibited for account records." in api_contracts
    assert "Default list behavior returns non-archived accounts" in api_contracts
    assert "including `PENDING`,\n`ACTIVE`, and `DISABLED`" in api_contracts
    assert "Manual account creation returns `ACTIVE` by default" in api_contracts
    assert (
        "Automatically discovered\nunknown accounts remain `PENDING`" in api_contracts
    )
    assert "audit_log` persistence starts in Sprint 3" in api_contracts
    assert "AccountUpdated" in api_contracts
    assert "AccountArchived" in api_contracts


def test_account_architecture_docs_define_canonical_enum_source() -> None:
    database_schema = _read_doc("04-database_schema.md")
    data_dictionary = _read_doc("05-data_dictionary.md")
    high_level_design = _read_doc("06-high_level_design.md")

    for document in (database_schema, data_dictionary, high_level_design):
        assert all(account_type in document for account_type in CANONICAL_ACCOUNT_TYPES)

    assert "WALLET` is not" in database_schema
    assert "WALLET` is not" in data_dictionary
    assert "Cash wallets use the CASH account type" in high_level_design


def test_account_schema_docs_define_archive_and_event_hooks() -> None:
    database_schema = _read_doc("04-database_schema.md")

    assert "SET status = 'ARCHIVED'" in database_schema
    assert "AccountCreated" in database_schema
    assert "AccountUpdated" in database_schema
    assert "AccountArchived" in database_schema


def test_account_soft_delete_adr_documents_status_archive_exception() -> None:
    soft_delete_adr = _read_doc("adrs/012-use-soft-delete-for-financial-records.md.md")

    assert "accounts use status = ARCHIVED" in soft_delete_adr
    assert "replaces generic `is_deleted` metadata" in soft_delete_adr
