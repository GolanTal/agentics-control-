#!/usr/bin/env bash
set -euo pipefail

: "${APPS_URL:?missing APPS_URL}"
: "${APPS_TOKEN:?missing APPS_TOKEN}"

python agents/quote_miner.py
python agents/quote_hunter.py
python agents/variant_generator.py
