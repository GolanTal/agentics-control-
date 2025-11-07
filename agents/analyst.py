#!/usr/bin/env python3
"""
Analyst: builds a simple one-pager from the Calendar tab.
- Creates missing sheets (Calendar, Analytics) with headers.
- Succeeds even if Calendar is empty (no-op report).
- NO Apps Script env required; uses ONLY Sheets creds.
"""
import os, json, collections, datetime as dt
import gspread
from google.oauth2.service_account import Credentials

CAL_HEADERS = [
  "date","platform","post_type","theme","hook","script_or_caption_url",
  "media_path","cta","utm_link","status","cxo_score","notes"
]
AN_HEADERS = ["metric","value"]

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
        ws = sh.add_worksheet(title=title, rows=1000, cols=max(8, len(headers)))
        ws.update("A1", [headers])
    # ensure header row
    first = ws.row_values(1)
    if [h.strip().lower() for h in first] != [h.lower() for h in headers]:
        ws.update("A1", [headers])
    return ws

def get_records(ws):
    values = ws.get_all_values()
    if not values or len(values) == 1:
        return []
    headers = values[0]
    rows = []
    for r in values[1:]:
        obj = {headers[i]: (r[i] if i < len(r) else "") for i in range(len(headers))}
        rows.append(obj)
    return rows

def write_analytics(ws, summary_rows, platform_rows):
    # clear a reasonable range then write two sections
    ws.batch_clear(["A1:D200"])
    out = []
    out.append(["metric","value"])
    out.extend(summary_rows)
    # blank line & section title
    out.append([])
    out.append(["platform","count"])
    out.extend(platform_rows)
    ws.update("A1", out, value_input_option="RAW")

def main():
    sheet_id = os.environ["CONTROL_SHEET_ID"]
    gc = auth()
    sh = gc.open_by_key(sheet_id)

    cal = ensure_ws(sh, "Calendar", CAL_HEADERS)
    ana = ensure_ws(sh, "Analytics", AN_HEADERS)

    records = get_records(cal)

    # no-op if nothing scheduled yet
    if not records:
        write_analytics(ana,
            [["as_of", dt.datetime.utcnow().isoformat()+"Z"],
             ["total_posts", 0],
             ["week_posts", 0]],
            []
        )
        print("analyst: Calendar empty → wrote no-op Analytics."); return

    # totals
    total_posts = len(records)
    # this week only
    this_monday = (dt.date.today() - dt.timedelta(days=dt.date.today().weekday()))
    week_posts = 0
    for r in records:
        d = (r.get("date") or "").strip()
        try:
            # accept "YYYY-MM-DD" or "MM/DD/YYYY"
            if "-" in d:
                y,m,dd = map(int, d.split("-"))
            else:
                m,dd,y = map(int, d.split("/"))
            if dt.date(y,m,dd) >= this_monday:
                week_posts += 1
        except Exception:
            pass

    # platform breakdown
    by_platform = collections.Counter((r.get("platform") or "").strip() or "Unknown" for r in records)
    plat_rows = [[p, c] for p,c in sorted(by_platform.items(), key=lambda x: (-x[1], x[0]))]

    summary_rows = [
        ["as_of", dt.datetime.utcnow().isoformat()+"Z"],
        ["total_posts", total_posts],
        ["week_posts", week_posts],
    ]

    write_analytics(ana, summary_rows, plat_rows)
    print(f"analyst: wrote Analytics (total={total_posts}, week={week_posts}).")

if __name__ == "__main__":
    main()
