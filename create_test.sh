#!/usr/bin/env bash

ROOT="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$ROOT"

cd "$ROOT" && python3 tests/export_test.py "$@"
