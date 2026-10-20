#!/bin/sh
# Runs the conformance suite against the reference server: the personal
# context (with the work context as the second context), then the team
# context with a second principal. Exits non-zero on any failure.
# Usage: conformance/run-reference.sh [python]
set -eu
PY="${1:-python3}"
HERE="$(cd "$(dirname "$0")" && pwd)"
PORT="${PCP_REF_PORT:-8765}"
BASE="http://127.0.0.1:$PORT/pcp"

start() {  # start [extra server args...]
  "$PY" "$HERE/reference/server.py" --port "$PORT" --test-mode "$@" &
  SERVER=$!
  i=0
  until curl -fsS "http://127.0.0.1:$PORT/.well-known/pcp.json" >/dev/null 2>&1; do
    i=$((i + 1)); [ "$i" -gt 50 ] && { echo "reference server did not start"; exit 1; }
    sleep 0.2
  done
}
SERVER=
trap 'kill $SERVER 2>/dev/null || true' EXIT INT TERM
start

cd "$HERE"
"$PY" -m pcp_conformance self-check
echo "== personal context"
"$PY" -m pcp_conformance run --endpoint "$BASE/dana/mcp" --other-endpoint "$BASE/acme-dana/mcp" \
  --allow-writes --revocation-wait 10
echo "== work context"
"$PY" -m pcp_conformance run --endpoint "$BASE/acme-dana/mcp" --other-endpoint "$BASE/dana/mcp" \
  --allow-writes --revocation-wait 10
echo "== team context"
"$PY" -m pcp_conformance run --endpoint "$BASE/crew/mcp" --second-login scout --private-partition private \
  --allow-writes --allow-load --revocation-wait 10
kill $SERVER; wait $SERVER 2>/dev/null || true

# Each deliberate violation must make the suite fail.
OUT="$(mktemp)"
for case in "sensitive-leak SCOPE-02" "audience AUTH-25" "origin AUTH-06" "framing SEC-10"; do
  set -- $case
  start --break "$1"
  echo "== broken server ($1): expecting $2 to fail"
  if "$PY" -m pcp_conformance run --endpoint "$BASE/dana/mcp" --other-endpoint "$BASE/acme-dana/mcp" \
      --allow-writes --only "$2" >"$OUT" 2>&1; then
    cat "$OUT"; echo "the suite did not catch --break $1"; exit 1
  fi
  grep "^FAIL" "$OUT"
  kill $SERVER; wait $SERVER 2>/dev/null || true
done
echo "all mutation cases caught"
