#!/usr/bin/env python3
import os, json, datetime as dt
import gspread
from google.oauth2.service_account import Credentials

CAL_HEADERS = ["date","platform","post_type","theme","hook",
               "script_or_caption_url","media_path","cta","utm_link",
               "status","cxo_score","notes"]

def auth():
    sa = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
    return gspread.authorize(Credentials.from_service_account_info(sa, scopes=scopes))

def ensure_ws(sh, title, headers):
    try:
        ws = sh.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=title, rows=2000, cols=len(headers))
        ws.append_row(headers)
    return ws

def next_dates(n):
    today = dt.date.today()
    return [(today + dt.timedelta(days=i)).isoformat() for i in range(1, n+1)]

def main():
    gc = auth()
    sh = gc.open_by_key(os.environ["CONTROL_SHEET_ID"])
    backlog = sh.worksheet("Quotes_Backlog").get_all_records()
    cal_ws = ensure_ws(sh, "Calendar", CAL_HEADERS)

    # pick up to 3 new quotes
    candidates = [r for r in backlog if (r.get("status","").lower() == "collected" and r.get("quote_text"))][:3]
    if not candidates:
        print("variant_generator: nothing to schedule.")
        return

    dates = next_dates(len(candidates))
    rows_to_append = []
    updates = []  # (row_index, new_status)

    # map spreadsheet row indices for updating status -> 'proposed'
    # row 2 corresponds to backlog[0]
    for idx, (row, sched_date) in enumerate(zip(candidates, dates)):
        hook = row["quote_text"].strip()
        theme = row.get("theme","")
        platforms = (row.get("platform_fit") or "IG,LI,X").split(",")
        note = f"auto from {row.get('quote_id','')}"
        # propose one IG Reel per quote (you can add TikTok/Shorts similarly)
        rows_to_append.append([
            sched_date, "Instagram", "Reel/Carousel/Story", theme, hook,
            "", "", "Read the book", "", "needs_review", "", note
        ])

        # locate the spreadsheet row index to update to 'proposed'
        # find the matching quote_id
        quote_id = row.get("quote_id","")
        try:
            row_index = 2 + next(i for i,r in enumerate(backlog) if r.get("quote_id","")==quote_id)
            updates.append(row_index)
        except StopIteration:
            pass

    if rows_to_append:
        cal_ws.append_rows(rows_to_append, value_input_option="USER_ENTERED")

    # update statuses to 'proposed'
    if updates:
        for r in updates:
            sh.worksheet("Quotes_Backlog").update_acell(f"M{r}", "proposed")

    print(f"variant_generator: added {len(rows_to_append)} Calendar rows; marked {len(updates)} quotes as proposed.")

if __name__ == "__main__":
    main()
