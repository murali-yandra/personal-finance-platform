#!/usr/bin/env bash
# End-to-end smoke test against a running instance.
#
# Walks the flow a real user takes and asserts the transaction lands in the
# ledger, the balance, the reports and the audit trail. This is the check that
# proves the whole product rather than a layer of it, and is what to run
# against a deployment once it is live.
#
# Usage:
#   BASE_URL=https://your-service.onrender.com \
#   INGEST_API_KEY=... \
#   ./scripts/smoke_mvp.sh
#
# INGEST_API_KEY is used only to reach the API-key endpoints; the SMS itself is
# ingested with a per-user key issued during the run.
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
EMAIL="${SMOKE_EMAIL:-smoke+$(date +%s)@example.com}"
PASSWORD="${SMOKE_PASSWORD:-SecurePass1}"

SALARY_SMS='Dear Customer, Rs.85,000.00 credited to A/c XXXXX7788 on 15-06-2026 towards SALARY JUN 2026. Ref no 555444333.'

fail() { echo "FAIL: $*" >&2; exit 1; }

# Extract a value from a JSON response on stdin, e.g. field "['data']['id']".
json() {
  python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data$1)
"
}

echo "1.  Health check"
curl -fsS "$BASE_URL/health" > /dev/null || fail "health check did not respond"

echo "2.  Register and log in as $EMAIL"
curl -fsS -X POST "$BASE_URL/api/v1/auth/register" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"display_name\":\"Smoke User\"}" \
  > /dev/null || fail "registration"

TOKEN=$(curl -fsS -X POST "$BASE_URL/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
  | json "['data']['access_token']")
AUTH="Authorization: Bearer $TOKEN"

echo "3.  Issue a per-user API key"
KEY=$(curl -fsS -X POST "$BASE_URL/api/v1/api-keys" \
  -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"name":"smoke"}' | json "['data']['api_key']")

echo "4.  Create an account opening at 10000.00"
ACCOUNT_ID=$(curl -fsS -X POST "$BASE_URL/api/v1/accounts" \
  -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"account_type":"BANK","account_name":"Smoke Account","bank_name":"ICICI","last_four_digits":"7788","opening_balance":"10000.00"}' \
  | json "['data']['id']")

echo "5.  Ingest a salary SMS"
STATUS=$(curl -fsS -X POST "$BASE_URL/api/v1/ingest/sms" \
  -H "X-API-KEY: $KEY" -H 'Content-Type: application/json' \
  -d "{\"sender\":\"AD-ICICIB\",\"message_text\":\"$SALARY_SMS\",\"received_at\":\"2026-06-15T09:00:00\"}" \
  | json "['data']['status']")
[ "$STATUS" = "PROCESSED" ] || fail "expected PROCESSED, got $STATUS"

echo "6.  Transaction reached the ledger"
AMOUNT=$(curl -fsS "$BASE_URL/api/v1/transactions" -H "$AUTH" \
  | json "['data'][0]['amount']")
[ "$AMOUNT" = "85000.00" ] || fail "expected amount 85000.00, got $AMOUNT"

echo "7.  Balance moved to 95000.00"
BALANCE=$(curl -fsS "$BASE_URL/api/v1/accounts/$ACCOUNT_ID" -H "$AUTH" \
  | json "['data']['estimated_balance']")
[ "$BALANCE" = "95000.00" ] || fail "expected balance 95000.00, got $BALANCE"

echo "8.  Reports reflect the income"
INCOME=$(curl -fsS "$BASE_URL/api/v1/reports/monthly-summary?year=2026&month=6" \
  -H "$AUTH" | json "['data']['income']")
[ "$INCOME" = "85000.00" ] || fail "expected income 85000.00, got $INCOME"

NET_WORTH=$(curl -fsS "$BASE_URL/api/v1/reports/net-worth" -H "$AUTH" \
  | json "['data']['net_worth']")
[ "$NET_WORTH" = "95000.00" ] || fail "expected net worth 95000.00, got $NET_WORTH"

echo "9.  Audit trail recorded the creation"
ENTRIES=$(curl -fsS "$BASE_URL/api/v1/audit" -H "$AUTH" \
  | json "['meta']['total_records']")
[ "$ENTRIES" -gt 0 ] || fail "audit trail is empty"

echo "10. Replay is a duplicate and does not move the balance"
REPLAY=$(curl -fsS -X POST "$BASE_URL/api/v1/ingest/sms" \
  -H "X-API-KEY: $KEY" -H 'Content-Type: application/json' \
  -d "{\"sender\":\"AD-ICICIB\",\"message_text\":\"$SALARY_SMS\",\"received_at\":\"2026-06-15T09:00:00\"}" \
  | json "['data']['status']")
[ "$REPLAY" = "DUPLICATE" ] || fail "expected DUPLICATE, got $REPLAY"

AFTER=$(curl -fsS "$BASE_URL/api/v1/accounts/$ACCOUNT_ID" -H "$AUTH" \
  | json "['data']['estimated_balance']")
[ "$AFTER" = "95000.00" ] || fail "balance moved on replay: $AFTER"

echo
echo "PASS: SMS -> transaction -> balance -> reports -> audit, with replay protection."
