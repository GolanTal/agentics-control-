#!/usr/bin/env python3
"""
Analyst
- Preferred: read/write via Apps Script gateway (APPS_URL/APPS_TOKEN).
- Fallback: service account (GOOGLE_SERVICE_ACCOUNT_JSON + CONTROL_SHEET_ID).
- Self-heals missing sheets (Calendar, Analytics).
- Tolerates empty Calendar (writes a no-op Analytics).
"""
import os, json, collections, datetime as dt

# ---------------- Common stuff ----------------
CAL_HEADERS = [
  "date","platform","post_type","theme","hook","script_or_caption_url",
  "media_path","cta","utm_link","status","cxo_score","notes"
]
AN_HEADERS = ["metric","value"]

def _today_monday():
    today = dt.date.today()
    return today - dt.timedelta(days=today.weekday())

def _summarize(records):
    total = len(records)
    week = 0
    monday = _today_monday()
    for r in records:
        d = (r.get("date") or "").strip()
        try:
            if "-" in d:
                y, m, dd = map(int, d.split("-"))
            else:
                m, dd, y = map(int, d.split("/"))
            if dt.date(y, m, dd) >= monday:
                week += 1
        except Exception:
            pass
    by_platform = collections.Counter((r.get("platform") or "").strip() or "Unknown"
                                      for r in records)
    plat_rows = [[p, c] for p, c in sorted(by_platform.items(), key=lambda x: (-x[1], x[0]))]
    summary_rows = [
        ["as_of", dt.datetime.utcnow().isoformat() + "Z"],
        ["total_posts", total],
        ["week_posts", week],
    ]
    return summary_rows, plat_rows

# ---------------- Path A: Apps Script ----------------
def run_via_apps():
    import requests
    APPS_URL   = os.getenv("APPS_URL", "").strip()
    APPS_TOKEN = os.getenv("APPS_TOKEN", "").strip()
    if not (APPS_URL.startswith("http://") or APPS_URL.startswith("https://")):
        return False  # not available
    if not APPS_TOKEN:
        return False

    def gget(sheet):
        r = requests.get(APPS_URL, params={"op":"get","sheet":sheet,"token":APPS_TOKEN}, timeout=60)
        r.raise_for_status(); return r.json()

    def gpost(payload):
        data = dict(payload); data["token"] = APPS_TOKEN
        r = requests.post(APPS_URL, json=data, timeout=60)
        r.raise_for_status(); return r.json()

    # ensure sheets
    gpost({"op":"ensureSheet","sheet":"Calendar","headers":CAL_HEADERS})
    gpost({"op":"ensureSheet","sheet":"Analytics","headers":AN_HEADERS})

    cal = gget("Calendar")
    rows = cal.get("rows", [])

    # compose analytics grid
    summary_rows, plat_rows = _summarize(rows) if rows else (
        [["as_of", dt.datetime.utcnow().isoformat()+"Z"], ["total_posts", 0], ["week_posts", 0]],
        []
    )
    out = []
    out.append(["metric","value"])
    out.extend(summary_rows)
    out.append([])
    out.append(["platform","count"])
    out.extend(plat_rows)

    # write via updateRange to Analytics!A1
    gpost({"op":"updateRange","sheet":"Analytics","a1":"A1","values":out})
    print(f"analyst(apps): wrote Analytics (rows={len(rows)}).")
    return True

# ---------------- Path B: Service Account ----------------
def run_via_sa():
    import gspread
    from google.oauth2.service_account import Credentials

    sheet_id = os.environ["CONTROL_SHEET_ID"]
    sa       = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    scopes   = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(sa, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)

    def ensure_ws(title, headers):
        try:
            ws = sh.worksheet(title)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=title, rows=1000, cols=max(8, len(headers)))
            ws.update("A1", [headers])
            return ws
        first = ws.row_values(1)
        if [x.strip().lower() for x in first] != [x.lower() for x in headers]:
            ws.update("A1", [headers])
        return ws

    cal = ensure_ws("Calendar", CAL_HEADERS)
    ana = ensure_ws("Analytics", AN_HEADERS)

    values = cal.get_all_values()
    recs = []
    if values and len(values) > 1:
        headers = values[0]
        for r in values[1:]:
            recs.append({headers[i]: (r[i] if i < len(r) else "") for i in range(len(headers))})

    summary_rows, plat_rows = _summarize(recs) if recs else (
        [["as_of", dt.datetime.utcnow().isoformat()+"Z"], ["total_posts", 0], ["week_posts", 0]],
        []
    )
    out = []
    out.append(["metric","value"]); out.extend(summary_rows)
    out.append([]); out.append(["platform","count"]); out.extend(plat_rows)
    ana.batch_clear(["A1:D200"])
    ana.update("A1", out, value_input_option="RAW")
    print(f"analyst(sa): wrote Analytics (rows={len(recs)}).")

def main():
    if run_via_apps():
        return
    # fall back to service account (will raise helpful KeyError if env missing)
    run_via_sa()

if __name__ == "__main__":
    main()
