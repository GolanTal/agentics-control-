#!/usr/bin/env bash
set -euo pipefail
python agents/quote_miner.py          # mines quotes -> Quotes_Backlog (status=proposed)
python agents/quote_hunter.py         # normalizes -> status=collected
python agents/variant_generator.py    # creates Calendar rows -> status=needs_review
