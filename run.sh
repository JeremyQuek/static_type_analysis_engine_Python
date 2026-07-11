#!/usr/bin/env bash

ROOT="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$ROOT"

cd "$ROOT" && python3 type_check.py "$@"
