#!/usr/bin/env python3
import os, requests

# --- ENV GUARD ---
APPS_URL   = os.getenv("APPS_URL", "").strip()
APPS_TOKEN = os.getenv("APPS_TOKEN", "").strip()
if not (APPS_URL.startswith("http://") or APPS_URL.startswith("https://")):
    raise SystemExit("APPS_URL missing/invalid in env")
if not APPS_TOKEN:
    raise SystemExit("APPS_TOKEN missing in env")
# -----------------

def api_get(sheet):
    r = requests.get(APPS_URL, params={"op":"get","sheet":sheet,"token":APPS_TOKEN}, timeout=60)
    r.raise_for_status()
    return r.json()

def api_post(payload):
    data = dict(payload); data["token"] = APPS_TOKEN
    r = requests.post(APPS_URL, json=data, timeout=60)
    r.raise_for_status()
    return r.json()

def classify_length(s):
    n = len(s or "")
    return "ultra_short" if n<=40 else ("short" if n<=140 else "long")

def fit_for(length):
    return {"ultra_short":"IG,TikTok,Shorts,X","short":"IG,LI,X","long":"LI,X"}[length]

def main():
    data = api_get("Quotes_Backlog")
    headers, rows = data.get("headers", []), data.get("rows", [])
    if not rows:
        print("quote_hunter: nothing to update."); return

    updated = 0
    for r in rows:
        status = (r.get("status") or "").strip().lower()
        if status in ("approved","rejected","collected"):
            continue
        q = (r.get("quote_text") or "").strip()
        if not q:
            continue

        length = classify_length(q)
        platform = fit_for(length)
        rownum = int(r["_row"])

        # H: length_category, I: platform_fit, J: owner, K: consent_status
        api_post({"op":"updateRange","sheet":"Quotes_Backlog",
                  "a1":f"H{rownum}:K{rownum}",
                  "values":[[length, platform, "Architect", "not_needed"]]})
        # M: status
        api_post({"op":"updateCell","sheet":"Quotes_Backlog",
                  "a1":f"M{rownum}","value":"collected"})
        updated += 1

    print(f"quote_hunter: updated {updated} rows.")

if __name__=="__main__":
    main()
