#!/usr/bin/env python3
import os, requests, datetime as dt

# --- ENV GUARD ---
APPS_URL   = os.getenv("APPS_URL", "").strip()
APPS_TOKEN = os.getenv("APPS_TOKEN", "").strip()
if not (APPS_URL.startswith("http://") or APPS_URL.startswith("https://")):
    raise SystemExit("APPS_URL missing/invalid in env")
if not APPS_TOKEN:
    raise SystemExit("APPS_TOKEN missing in env")
# -----------------

CAL_HEADERS = ["date","platform","hook","cta","media_path","status","notes"]

def api_get(sheet):
    r = requests.get(APPS_URL, params={"op":"get","sheet":sheet,"token":APPS_TOKEN}, timeout=60)
    r.raise_for_status()
    return r.json()

def api_post(payload):
    data = dict(payload); data["token"] = APPS_TOKEN
    r = requests.post(APPS_URL, json=data, timeout=60)
    r.raise_for_status()
    return r.json()

def ensure_calendar():
    api_post({"op":"ensureSheet","sheet":"Calendar","headers":CAL_HEADERS})

def main():
    ensure_calendar()

    quotes = api_get("Quotes_Backlog").get("rows", [])
    if not quotes:
        print("variant_generator: no quotes."); return

    today = dt.date.today().isoformat()
    rows = []
    for r in quotes:
        if (r.get("status") or "").strip().lower() != "collected":
            continue
        hook = (r.get("quote_text") or "").strip()
        if not hook:
            continue
        rows.append([today, "IG", hook, "Read more → [add link]", "", "needs_review", ""])

    if rows:
        api_post({"op":"appendRows","sheet":"Calendar","rows":rows})
        print(f"variant_generator: added {len(rows)} Calendar rows.")
    else:
        print("variant_generator: nothing to add.")

if __name__=="__main__":
    main()
