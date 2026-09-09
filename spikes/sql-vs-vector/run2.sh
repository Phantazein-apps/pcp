#!/usr/bin/env bash
# Second pass: corpus-a (atomic) against corpus-b (subject-shaped), four
# conditions, two models, three seeds.
#
#   ./run2.sh                 the full second pass, 1,008 runs
#   ./run2.sh --build-only    build both corpora and both question sets, stop
#   ./run2.sh --report-only   re-aggregate existing logs
#
# Requires: python3.11+, and either an Anthropic API key or a logged-in
# `claude` CLI on PATH (the SDK uses whichever is available).
set -euo pipefail
cd "$(dirname "$0")"

MODE=full
while [ $# -gt 0 ]; do
  case "$1" in
    --build-only)  MODE=build;  shift ;;
    --report-only) MODE=report; shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

PY=.venv/bin/python
if [ ! -x "$PY" ]; then
  echo "== creating venv =="
  python3 -m venv .venv
  .venv/bin/pip install --quiet --upgrade pip
  .venv/bin/pip install --quiet torch==2.14.0 --index-url https://download.pytorch.org/whl/cpu \
    || .venv/bin/pip install --quiet torch==2.14.0
  .venv/bin/pip install --quiet -r requirements.txt
fi

if [ "$MODE" != "report" ]; then
  echo "== build: both corpora at 2000 pages, storage, embeddings =="
  # corpus-b is embedded one vector per bullet (32.9k chunks); allow ~10 min.
  $PY -m pcp_spike.build --shape both --target-pages 2000 --with-reconcile

  echo "== questions =="
  $PY -m pcp_spike.qset2 --shape atomic  --corpus-root corpus-a --data-root data-a \
      --out questions/questions-a.json --overlap-out logs/overlap-a.json
  $PY -m pcp_spike.qset2 --shape subject --corpus-root corpus-b --data-root data-b \
      --out questions/questions-b.json --overlap-out logs/overlap-b.json
fi
[ "$MODE" = "build" ] && exit 0

if [ "$MODE" != "report" ]; then
  # Per-sweep budget guards, sized from the measured per-run costs in
  # NOTES.md §4.2 with headroom. They sum to $21.5; with the pilots and the
  # judge that lands under the $25 cap. A sweep that would overrun stops
  # paying rather than finishing and apologising afterwards.
  echo "== runs: 21 questions x 4 conditions x 2 models x 3 seeds x 2 corpora =="
  $PY -m pcp_spike.runner --shape atomic  --models haiku  --seeds 1,2,3 \
      --concurrency 6 --tag a-haiku  --budget 4.5
  $PY -m pcp_spike.runner --shape atomic  --models sonnet --seeds 1,2,3 \
      --concurrency 6 --tag a-sonnet --budget 5.0
  $PY -m pcp_spike.runner --shape subject --models haiku  --seeds 1,2,3 \
      --concurrency 6 --tag b-haiku  --budget 6.0
  $PY -m pcp_spike.runner --shape subject --models sonnet --seeds 1,2,3 \
      --concurrency 6 --tag b-sonnet --budget 6.0

  echo "== judging =="
  for tag in a-haiku a-sonnet; do
    $PY -m pcp_spike.judge --runs "logs/raw/runs-$tag.jsonl" \
        --questions questions/questions-a.json
  done
  for tag in b-haiku b-sonnet; do
    $PY -m pcp_spike.judge --runs "logs/raw/runs-$tag.jsonl" \
        --questions questions/questions-b.json
  done
fi

echo "== tables =="
$PY -m pcp_spike.report2 \
    --judged logs/raw/judged-a-haiku.jsonl logs/raw/judged-a-sonnet.jsonl \
             logs/raw/judged-b-haiku.jsonl logs/raw/judged-b-sonnet.jsonl \
    --out logs/results-second-pass.md

echo
echo "Tables:   logs/results-second-pass.md"
echo "Overlap:  logs/overlap-a.json, logs/overlap-b.json"
echo "Raw logs: logs/raw/runs-*.jsonl, logs/raw/judged-*.jsonl"
