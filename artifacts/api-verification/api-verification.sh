#!/usr/bin/env bash
# Reproducible API verification against a real uvicorn process.
#
# Starts the API on an empty temporary SQLite database with demo mode off, then
# claims the workspace through registration, creates real records and downloads
# a CSV. Requires the backend virtual environment to exist.
set -uo pipefail

PORT="${PORT:-8011}"
BASE="http://127.0.0.1:${PORT}/api/v1"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BACKEND="${ROOT}/backend"
# Relative to the backend directory; SQLite wants a portable URL.
STAMP="$(date +%s)"
DB="./data/verify-${PORT}-${STAMP}.db"
COOKIES="./data/verify-cookies-${STAMP}.txt"
LOG="${ROOT}/artifacts/api-verification/server.log"

rm -f "$LOG"

# Refuse to run against a server we did not start: a leftover process would make
# every assertion below meaningless.
if curl -sf "${BASE}/health" >/dev/null 2>&1; then
  echo "ERROR: something is already serving ${BASE}. Stop it before running this script." >&2
  exit 1
fi

cd "$BACKEND"
DATABASE_URL="sqlite:///${DB}" DEMO_MODE=false LOG_LEVEL=WARNING \
  .venv/Scripts/python.exe -m uvicorn app.main:app --port "$PORT" >"$LOG" 2>&1 &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null; wait "$SERVER_PID" 2>/dev/null; sleep 0.5; rm -f "$DB" "$COOKIES"' EXIT

READY=0
for _ in $(seq 1 60); do
  if curl -sf "${BASE}/health" >/dev/null 2>&1; then READY=1; break; fi
  sleep 0.5
done
if [ "$READY" -ne 1 ]; then
  echo "ERROR: the API did not become ready on port ${PORT}." >&2
  sed -n '1,40p' "$LOG" >&2
  exit 1
fi

status() { curl -s -o /dev/null -w '%{http_code}' "$@"; }

echo "# API verification — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Database: empty SQLite, DEMO_MODE=false"
echo
echo "## Health before any account exists"
curl -s "${BASE}/health"; echo
echo
echo "## Data routes require a session"
echo "GET /projects anonymous -> $(status "${BASE}/projects")"
echo "GET /exports/participants.csv anonymous -> $(status "${BASE}/exports/participants.csv")"
echo
echo "## First-run registration claims the workspace"
curl -s -c "$COOKIES" -X POST "${BASE}/auth/register" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Verification Admin","email":"verify@example.test","password":"verification-password","organisation_name":"Everyday Goods"}' \
  -w '\nstatus=%{http_code}\n'
echo
echo "GET /auth/me -> $(status -b "$COOKIES" "${BASE}/auth/me")"
echo "Registration closed on second attempt -> $(status -X POST "${BASE}/auth/register" -H 'Content-Type: application/json' -d '{"name":"Second Admin","email":"second@example.test","password":"another-password-1","organisation_name":"Other"}')"
echo
echo "## Real records created through the API"
PROJECT=$(curl -s -b "$COOKIES" -X POST "${BASE}/projects" -H 'Content-Type: application/json' \
  -d '{"name":"Verification project","objective":"Prove the API persists real records from an empty database."}')
echo "project created -> $(echo "$PROJECT" | head -c 160)…"
PARTICIPANT=$(curl -s -b "$COOKIES" -X POST "${BASE}/participants" -H 'Content-Type: application/json' \
  -d '{"display_name":"Zo\u00eb \u00c5ngstr\u00f6m","segment":"repeat_buyer","purchase_frequency":"Every 6 weeks","product_category":"Shampoo","eligibility":"eligible"}')
echo "participant created -> $(echo "$PARTICIPANT" | head -c 160)…"
echo
echo "## CSV export with a real session"
curl -s -b "$COOKIES" -D - -o /tmp/verify-export.csv "${BASE}/exports/participants.csv" \
  | grep -iE 'HTTP/|content-type|content-disposition|x-row-count|x-data-origin'
echo "--- file head ---"
head -2 /tmp/verify-export.csv | cut -c1-200
rm -f /tmp/verify-export.csv
echo
echo "## Sign-out revokes the session"
echo "POST /auth/logout -> $(status -b "$COOKIES" -c "$COOKIES" -X POST "${BASE}/auth/logout")"
echo "GET /auth/me after logout -> $(status -b "$COOKIES" "${BASE}/auth/me")"
