"""The MVP end to end: register, ingest an SMS, see it everywhere.

This is the one test that proves the whole product rather than a layer of it.
It walks the flow a real user takes and asserts the transaction shows up in the
ledger, the balance, the reports and the audit trail.
"""

from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.config import get_settings
from tests.conftest import register_user

ICICI_SALARY = (
    "Dear Customer, Rs.85,000.00 credited to A/c XXXXX7788 on 15-06-2026 "
    "towards SALARY JUN 2026. Ref no 555444333."
)
HDFC_LUNCH = (
    "Rs.70.00 debited from A/C XXXX7788 at SmartQ on 15-06-2026 13:05. Ref 998877"
)


@pytest.fixture
def ingest_owner(override_session: None):
    settings = get_settings()
    original = settings.ingest_user_email
    settings.ingest_user_email = "owner@example.com"
    try:
        yield {"X-API-KEY": settings.ingest_api_key.get_secret_value()}
    finally:
        settings.ingest_user_email = original


@pytest.mark.asyncio
async def test_sms_to_transaction_to_reports(
    auth_client: AsyncClient,
    ingest_owner: dict[str, str],
) -> None:
    # 1. Register and authenticate.
    await register_user(auth_client, email="owner@example.com")
    login = await auth_client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "SecurePass1"},
    )
    assert login.status_code == 200
    token = login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Register the account the SMS will refer to.
    created = await auth_client.post(
        "/api/v1/accounts",
        json={
            "account_type": "BANK",
            "account_name": "Salary Account",
            "bank_name": "ICICI",
            "last_four_digits": "7788",
            "opening_balance": "10000.00",
        },
        headers=headers,
    )
    assert created.status_code == 201
    account_id = created.json()["data"]["id"]

    # 3. Ingest a salary credit, exactly as MacroDroid would.
    salary = await auth_client.post(
        "/api/v1/ingest/sms",
        json={
            "sender": "AD-ICICIB",
            "message_text": ICICI_SALARY,
            "received_at": "2026-06-15T09:00:00",
        },
        headers=ingest_owner,
    )
    assert salary.status_code == 201, salary.text
    assert salary.json()["data"]["status"] == "PROCESSED"
    assert salary.json()["data"]["transaction_id"] is not None

    # 4. The transaction is in the ledger with the parsed details.
    listed = await auth_client.get("/api/v1/transactions", headers=headers)
    assert listed.status_code == 200
    body = listed.json()
    assert body["meta"]["total_records"] == 1

    transaction = body["data"][0]
    assert transaction["amount"] == "85000.00"
    assert transaction["direction"] == "CREDIT"
    assert transaction["business_type"] == "INCOME"
    assert transaction["account_id"] == account_id
    assert transaction["raw_event_id"] == salary.json()["data"]["raw_event_id"]

    # 5. The balance moved by the amount.
    account = await auth_client.get(
        f"/api/v1/accounts/{account_id}",
        headers=headers,
    )
    assert Decimal(account.json()["data"]["estimated_balance"]) == Decimal("95000.00")

    # 6. Reporting reflects it.
    summary = await auth_client.get(
        "/api/v1/reports/monthly-summary",
        params={"year": 2026, "month": 6},
        headers=headers,
    )
    assert summary.json()["data"]["income"] == "85000.00"

    net_worth = await auth_client.get("/api/v1/reports/net-worth", headers=headers)
    assert net_worth.json()["data"]["net_worth"] == "95000.00"

    # 7. The audit trail records the creation.
    audit = await auth_client.get(
        "/api/v1/audit",
        params={"entity_type": "transaction"},
        headers=headers,
    )
    assert "CREATE" in [entry["action"] for entry in audit.json()["data"]]


@pytest.mark.asyncio
async def test_expense_lowers_the_balance_and_shows_in_the_breakdown(
    auth_client: AsyncClient,
    ingest_owner: dict[str, str],
) -> None:
    await register_user(auth_client, email="owner@example.com")
    headers = {
        "Authorization": "Bearer "
        + (
            await auth_client.post(
                "/api/v1/auth/login",
                json={"email": "owner@example.com", "password": "SecurePass1"},
            )
        ).json()["data"]["access_token"]
    }

    created = await auth_client.post(
        "/api/v1/accounts",
        json={
            "account_type": "BANK",
            "account_name": "Salary Account",
            "bank_name": "HDFC",
            "last_four_digits": "7788",
            "opening_balance": "5000.00",
        },
        headers=headers,
    )
    account_id = created.json()["data"]["id"]

    ingested = await auth_client.post(
        "/api/v1/ingest/sms",
        json={
            "sender": "VK-HDFCBK",
            "message_text": HDFC_LUNCH,
            "received_at": "2026-06-15T13:06:00",
        },
        headers=ingest_owner,
    )
    assert ingested.json()["data"]["status"] == "PROCESSED"

    account = await auth_client.get(
        f"/api/v1/accounts/{account_id}",
        headers=headers,
    )
    assert Decimal(account.json()["data"]["estimated_balance"]) == Decimal("4930.00")

    breakdown = await auth_client.get(
        "/api/v1/reports/category-breakdown",
        params={"start_date": "2026-06-01", "end_date": "2026-06-30"},
        headers=headers,
    )
    rows = breakdown.json()["data"]
    assert rows[0]["amount"] == "70.00"
    assert rows[0]["category"] == "Uncategorized"


@pytest.mark.asyncio
async def test_replayed_sms_does_not_double_count_the_money(
    auth_client: AsyncClient,
    ingest_owner: dict[str, str],
) -> None:
    """A retrying sender must never move the balance twice."""
    await register_user(auth_client, email="owner@example.com")
    headers = {
        "Authorization": "Bearer "
        + (
            await auth_client.post(
                "/api/v1/auth/login",
                json={"email": "owner@example.com", "password": "SecurePass1"},
            )
        ).json()["data"]["access_token"]
    }

    created = await auth_client.post(
        "/api/v1/accounts",
        json={
            "account_type": "BANK",
            "bank_name": "HDFC",
            "last_four_digits": "7788",
            "opening_balance": "5000.00",
        },
        headers=headers,
    )
    account_id = created.json()["data"]["id"]

    payload = {
        "sender": "VK-HDFCBK",
        "message_text": HDFC_LUNCH,
        "received_at": "2026-06-15T13:06:00",
    }
    await auth_client.post("/api/v1/ingest/sms", json=payload, headers=ingest_owner)
    replay = await auth_client.post(
        "/api/v1/ingest/sms",
        json=payload,
        headers=ingest_owner,
    )

    assert replay.json()["data"]["status"] == "DUPLICATE"

    listed = await auth_client.get("/api/v1/transactions", headers=headers)
    assert listed.json()["meta"]["total_records"] == 1

    account = await auth_client.get(
        f"/api/v1/accounts/{account_id}",
        headers=headers,
    )
    assert Decimal(account.json()["data"]["estimated_balance"]) == Decimal("4930.00")


@pytest.mark.asyncio
async def test_unknown_account_creates_a_pending_account_for_review(
    auth_client: AsyncClient,
    ingest_owner: dict[str, str],
) -> None:
    """Real money is recorded even before the user has registered the account."""
    await register_user(auth_client, email="owner@example.com")
    headers = {
        "Authorization": "Bearer "
        + (
            await auth_client.post(
                "/api/v1/auth/login",
                json={"email": "owner@example.com", "password": "SecurePass1"},
            )
        ).json()["data"]["access_token"]
    }

    ingested = await auth_client.post(
        "/api/v1/ingest/sms",
        json={
            "sender": "VK-HDFCBK",
            "message_text": HDFC_LUNCH,
            "received_at": "2026-06-15T13:06:00",
        },
        headers=ingest_owner,
    )
    assert ingested.json()["data"]["status"] == "NEEDS_REVIEW"

    accounts = (await auth_client.get("/api/v1/accounts", headers=headers)).json()
    assert len(accounts["data"]) == 1
    assert accounts["data"][0]["status"] == "PENDING"
    assert accounts["data"][0]["last_four_digits"] == "7788"
