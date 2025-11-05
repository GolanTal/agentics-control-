#!/usr/bin/env bash
set -euo pipefail
python agents/quote_hunter.py
python agents/variant_generator.py
python agents/channel_mapper.py
