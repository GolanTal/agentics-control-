#!/usr/bin/env python3
import os, requests, datetime as dt

APPS_URL   = os.environ["APPS_URL"]
APPS_TOKEN = os.environ["APPS_TOKEN"]

REPORT_HEADERS = [
  "run_at","week_start","week_end",
  "quotes_proposed","quotes_collected","quotes_approved","quotes_rejected",
  "cal_needs_review","cal_approved","cal_total"
]

def api_get(sheet):
    r = requests.get(APPS_URL, params={"op":"get","sheet":sheet,"token":APPS_TOKEN}, timeout=60)
    r.raise_for_status(); return r.json()

def api_post(payload):
    j=dict(payload); j["token"]=APPS_TOKEN
    r=requests.post(APPS_URL,json=j,timeout=60)
    r.raise_for_status(); return r.json()

def ensure_reports():
    return api_post({"op":"ensureSheet","sheet":"Reports","headers":REPORT_HEADERS})

def count_status(rows, field="status", target=None):
    if target is None:
        return len(rows)
    return sum(1 for r in rows if (r.get(field,"") or "").strip().lower()==target)

def main():
    ensure_reports()

    quotes = api_get("Quotes_Backlog").get("rows", [])
    cal    = api_get("Calendar").get("rows", [])

    today = dt.date.today()
    week_start = today - dt.timedelta(days=today.weekday())
    week_end   = week_start + dt.timedelta(days=6)

    q_proposed  = count_status(quotes, target="proposed")
    q_collected = count_status(quotes, target="collected")
    q_approved  = count_status(quotes, target="approved")
    q_rejected  = count_status(quotes, target="rejected")

    c_needs     = count_status(cal, target="needs_review")
    c_app       = count_status(cal, target="approved")
    c_total     = len(cal)

    row = [[
      dt.datetime.utcnow().isoformat(timespec="seconds")+"Z",
      week_start.isoformat(), week_end.isoformat(),
      q_proposed, q_collected, q_approved, q_rejected,
      c_needs, c_app, c_total
    ]]

    api_post({"op":"appendRows","sheet":"Reports","rows":row})
    print("analyst: wrote weekly snapshot to Reports.")

if __name__ == "__main__":
    main()
