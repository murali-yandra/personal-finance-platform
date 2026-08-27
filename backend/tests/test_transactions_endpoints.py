"""API contract for the transaction and audit endpoints (Sprint 3)."""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from tests.conftest import authorization_header, register_user

ACCOUNTS_URL = "/api/v1/accounts"
TRANSACTIONS_URL = "/api/v1/transactions"
AUDIT_URL = "/api/v1/audit"


async def _create_account(client: AsyncClient, headers: dict[str, str]) -> str:
    response = await client.post(
        ACCOUNTS_URL,
        json={
            "account_type": "BANK",
            "account_name": "Salary",
            "bank_name": "ICICI",
            "last_four_digits": "0452",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["id"]


async def _create_transaction(
    client: AsyncClient,
    headers: dict[str, str],
    account_id: str,
    **overrides,
) -> dict:
    payload = {
        "account_id": account_id,
        "amount": "70.00",
        "direction": "DEBIT",
        "merchant_raw": "SmartQ",
        "reference_number": "REF123",
        "transaction_timestamp": "2026-06-02T10:00:00",
    }
    payload.update(overrides)
    response = await client.post(TRANSACTIONS_URL, json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["data"]


@pytest.mark.asyncio
async def test_create_transaction_returns_created_envelope(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    _, headers = authenticated_user
    account_id = await _create_account(auth_client, headers)

    data = await _create_transaction(auth_client, headers, account_id)

    assert data["amount"] == "70.00"
    assert data["direction"] == "DEBIT"
    assert data["account_id"] == account_id
    UUID(data["id"])


@pytest.mark.asyncio
async def test_duplicate_transaction_returns_conflict(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    _, headers = authenticated_user
    account_id = await _create_account(auth_client, headers)
    await _create_transaction(auth_client, headers, account_id)

    response = await auth_client.post(
        TRANSACTIONS_URL,
        json={
            "account_id": account_id,
            "amount": "70.00",
            "direction": "DEBIT",
            "merchant_raw": "SmartQ",
            "reference_number": "REF123",
            "transaction_timestamp": "2026-06-02T10:00:00",
        },
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_TRANSACTION"


@pytest.mark.asyncio
async def test_negative_amount_is_rejected(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    _, headers = authenticated_user
    account_id = await _create_account(auth_client, headers)

    response = await auth_client.post(
        TRANSACTIONS_URL,
        json={"account_id": account_id, "amount": "-1.00", "direction": "DEBIT"},
        headers=headers,
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_transactions_require_authentication(auth_client: AsyncClient) -> None:
    response = await auth_client.get(TRANSACTIONS_URL)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_transactions_returns_pagination_meta(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    _, headers = authenticated_user
    account_id = await _create_account(auth_client, headers)
    await _create_transaction(auth_client, headers, account_id, reference_number="A")
    await _create_transaction(auth_client, headers, account_id, reference_number="B")

    response = await auth_client.get(
        TRANSACTIONS_URL,
        params={"page": 1, "page_size": 1},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 1
    assert body["meta"] == {"page": 1, "page_size": 1, "total_records": 2}


@pytest.mark.asyncio
async def test_list_transactions_second_page_returns_the_rest(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    _, headers = authenticated_user
    account_id = await _create_account(auth_client, headers)
    await _create_transaction(auth_client, headers, account_id, reference_number="A")
    await _create_transaction(auth_client, headers, account_id, reference_number="B")

    first = await auth_client.get(
        TRANSACTIONS_URL,
        params={"page": 1, "page_size": 1},
        headers=headers,
    )
    second = await auth_client.get(
        TRANSACTIONS_URL,
        params={"page": 2, "page_size": 1},
        headers=headers,
    )

    assert first.json()["data"][0]["id"] != second.json()["data"][0]["id"]


@pytest.mark.asyncio
async def test_list_transactions_filters_by_account(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    _, headers = authenticated_user
    account_id = await _create_account(auth_client, headers)
    await _create_transaction(auth_client, headers, account_id)

    response = await auth_client.get(
        TRANSACTIONS_URL,
        params={"account_id": str(uuid4())},
        headers=headers,
    )

    assert response.json()["meta"]["total_records"] == 0


@pytest.mark.asyncio
async def test_get_transaction_owned_by_another_user_returns_not_found(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    _, headers = authenticated_user
    account_id = await _create_account(auth_client, headers)
    transaction = await _create_transaction(auth_client, headers, account_id)

    intruder_id = await register_user(auth_client, email="intruder@example.com")
    intruder_headers = authorization_header(intruder_id, email="intruder@example.com")

    response = await auth_client.get(
        f"{TRANSACTIONS_URL}/{transaction['id']}",
        headers=intruder_headers,
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TRANSACTION_NOT_FOUND"


@pytest.mark.asyncio
async def test_update_transaction_sets_description_and_category(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    _, headers = authenticated_user
    account_id = await _create_account(auth_client, headers)
    transaction = await _create_transaction(auth_client, headers, account_id)

    response = await auth_client.patch(
        f"{TRANSACTIONS_URL}/{transaction['id']}",
        json={"description": "Lunch with team", "is_reviewed": True},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["description"] == "Lunch with team"
    assert data["is_reviewed"] is True


@pytest.mark.asyncio
async def test_transaction_changes_are_audited(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    _, headers = authenticated_user
    account_id = await _create_account(auth_client, headers)
    transaction = await _create_transaction(auth_client, headers, account_id)
    await auth_client.patch(
        f"{TRANSACTIONS_URL}/{transaction['id']}",
        json={"description": "Lunch with team"},
        headers=headers,
    )

    response = await auth_client.get(
        AUDIT_URL,
        params={"entity_type": "transaction"},
        headers=headers,
    )

    assert response.status_code == 200
    actions = [entry["action"] for entry in response.json()["data"]]
    assert "CREATE" in actions
    assert "UPDATE" in actions


@pytest.mark.asyncio
async def test_audit_records_capture_the_old_and_new_value(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    _, headers = authenticated_user
    account_id = await _create_account(auth_client, headers)

    await auth_client.patch(
        f"{ACCOUNTS_URL}/{account_id}",
        json={"account_name": "Primary Salary"},
        headers=headers,
    )

    response = await auth_client.get(
        AUDIT_URL,
        params={"entity_type": "account"},
        headers=headers,
    )

    updates = [
        entry
        for entry in response.json()["data"]
        if entry["field_name"] == "account_name"
    ]
    assert len(updates) == 1
    assert updates[0]["old_value"] == "Salary"
    assert updates[0]["new_value"] == "Primary Salary"


@pytest.mark.asyncio
async def test_audit_never_exposes_another_users_records(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    _, headers = authenticated_user
    await _create_account(auth_client, headers)

    intruder_id = await register_user(auth_client, email="intruder@example.com")
    intruder_headers = authorization_header(intruder_id, email="intruder@example.com")

    response = await auth_client.get(AUDIT_URL, headers=intruder_headers)

    assert response.json()["meta"]["total_records"] == 0


@pytest.mark.asyncio
async def test_audit_api_is_read_only(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    """Audit rows are append-only, so there must be no write route."""
    _, headers = authenticated_user

    for method in (auth_client.post, auth_client.patch, auth_client.delete):
        response = await method(AUDIT_URL, headers=headers)
        assert response.status_code == 405
