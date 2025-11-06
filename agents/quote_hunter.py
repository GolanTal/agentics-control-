#!/usr/bin/env python3
import os, json
import gspread
from google.oauth2.service_account import Credentials

BACKLOG_HEADERS = [
  "quote_id","source_type","quote_text","source_reference","location",
  "theme","tone_tag","length_category","platform_fit","owner",
  "consent_status","paraphrase_ok","status","notes"
]

def auth():
    sa = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(sa, scopes=scopes)
    return gspread.authorize(creds)

def ensure_ws(sh, title, headers):
    try:
        ws = sh.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=title, rows=1000, cols=len(headers))
        ws.append_row(headers)
    return ws

def classify_length(txt: str) -> str:
    n = len((txt or "").strip())
    if n <= 40:  return "ultra_short"
    if n <= 140: return "short"
    return "long"

def platform_fit_for(length: str) -> str:
    return {
        "ultra_short": "IG,TikTok,Shorts,X",
        "short":       "IG,LI,X",
        "long":        "LI,X",
    }.get(length, "IG,LI,X")

def main():
    gc = auth()
    sh = gc.open_by_key(os.environ["CONTROL_SHEET_ID"])
    ws = ensure_ws(sh, "Quotes_Backlog", BACKLOG_HEADERS)

    rows = ws.get_all_records()
    updated = 0

    for i, r in enumerate(rows, start=2):  # data starts at row 2
        q = (r.get("quote_text") or "").strip()
        if not q:
            continue

        status = (r.get("status") or "").strip().lower()
        if status in ("approved","rejected","proposed"):
            continue

        length = r.get("length_category") or classify_length(q)
        platform = r.get("platform_fit") or platform_fit_for(length)
        owner = r.get("owner") or "Architect"
        consent = r.get("consent_status") or "not_needed"

        ws.update(f"H{i}:K{i}", [[length, platform, owner, consent]])
        ws.update_acell(f"M{i}", "collected")
        updated += 1

    print(f"quote_hunter: updated {updated} rows.")

if __name__ == "__main__":
    main()
