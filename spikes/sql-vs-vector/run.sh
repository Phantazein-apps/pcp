#!/usr/bin/env bash
# One-command reproduction of the sql-vs-vector spike.
#
#   ./run.sh              first pass: 60 questions x 3 conditions x sonnet x 1 seed
#   ./run.sh --full       adds haiku and a second seed
#   ./run.sh --embeddings none   BM25 only, for environments without HF egress
#
# Requires: python3.11+, and either an Anthropic API key or a logged-in
# `claude` CLI on PATH (the SDK uses whichever is available).
set -euo pipefail
cd "$(dirname "$0")"

EMB=local
FULL=""
TAG=first-pass
BACKEND=vector
while [ $# -gt 0 ]; do
  case "$1" in
    --full)        FULL="--full"; TAG=full; shift ;;
    --embeddings)  EMB="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
if [ "$EMB" = "none" ]; then BACKEND=lexical; TAG="$TAG-lexical"; fi

PY=.venv/bin/python
if [ ! -x "$PY" ]; then
  echo "== creating venv =="
  python3 -m venv .venv
  .venv/bin/pip install --quiet --upgrade pip
  # CPU-only torch keeps the venv at ~1.6 GB instead of ~4 GB
  .venv/bin/pip install --quiet torch==2.14.0 --index-url https://download.pytorch.org/whl/cpu \
    || .venv/bin/pip install --quiet torch==2.14.0
  .venv/bin/pip install --quiet -r requirements.txt
fi

echo "== build: corpus, storage, embeddings =="
$PY -m pcp_spike.build --embeddings "$EMB"

echo "== questions =="
$PY -m pcp_spike.qset

echo "== runs =="
$PY -m pcp_spike.runner --tag "$TAG" --backend "$BACKEND" --concurrency 6 $FULL

echo "== judging =="
$PY -m pcp_spike.judge --runs "logs/raw/runs-$TAG.jsonl"

echo "== tables =="
$PY -m pcp_spike.report --judged "logs/raw/judged-$TAG.jsonl" --out "logs/results-$TAG.md"
echo
echo "Tables:   logs/results-$TAG.md"
echo "Raw logs: logs/raw/runs-$TAG.jsonl (runs), logs/raw/judged-$TAG.jsonl (verdicts)"
