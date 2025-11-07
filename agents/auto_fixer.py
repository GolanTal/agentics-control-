#!/usr/bin/env python3
import os, re, json, datetime, itertools
import requests

APPS_URL   = os.environ["APPS_URL"]
APPS_TOKEN = os.environ["APPS_TOKEN"]
FIX_SHEET  = os.getenv("FIX_SHEET", "Calendar")

# ---------- helpers ----------
def api_get(sheet):
    r = requests.get(APPS_URL,
                     params={"op":"get","sheet":sheet,"token":APPS_TOKEN},
                     timeout=60)
    r.raise_for_status()
    return r.json()

def api_post(payload: dict):
    data = dict(payload); data["token"] = APPS_TOKEN
    r = requests.post(APPS_URL, json=data, timeout=60)
    r.raise_for_status()
    return r.json()

def col_letter(n:int)->str:
    s=""
    while n:
        n, rem = divmod(n-1, 26)
        s = chr(65+rem) + s
    return s

# Google Sheets serial date -> ISO
def from_serial(n):
    base = datetime.date(1899, 12, 30)  # Sheets epoch
    return (base + datetime.timedelta(days=int(n))).isoformat()

# Very tolerant date parser. Returns ISO (YYYY-MM-DD) or None.
def parse_date(x):
    if x is None: return None
    if isinstance(x, (int,float)):
        try: return from_serial(x)
        except Exception: return None
    s = str(x).strip()
    if not s or s.lower() in {"tbd","na","n/a","none","-"}:
        return None

    # Try a bunch of common formats
    fmts = (
        "%Y-%m-%d","%Y/%m/%d",
        "%m/%d/%Y","%d/%m/%Y",
        "%m-%d-%Y","%d-%m-%Y",
        "%m/%d/%y","%d/%m/%y",
        "%b %d, %Y","%d %b %Y","%b %d %y","%d %b %y"
    )
    for f in fmts:
        try:
            return datetime.datetime.strptime(s, f).date().isoformat()
        except ValueError:
            pass

    # Fallback regex like 2025.11.07 or 2025.1.7
    m = re.match(r"^\s*(\d{4})[./-](\d{1,2})[./-](\d{1,2})\s*$", s)
    if m:
        Y,M,D = m.groups()
        try: return datetime.date(int(Y),int(M),int(D)).isoformat()
        except ValueError: return None

    return None

def slug(v):
    s = (v or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+","-",s).strip("-")
    return s or "na"

def build_utm(r):
    # If already present, keep it
    link = (r.get("utm_link") or "").strip()
    if link: return link
    source   = slug(r.get("platform"))
    medium   = slug(r.get("post_type"))
    campaign = slug(r.get("theme"))
    content  = slug((r.get("hook") or "")[:40])
    return f"utm_source={source}&utm_medium={medium}&utm_campaign={campaign}&utm_content={content}"

# ---------- main ----------
def main():
    data = api_get(FIX_SHEET)
    if "headers" not in data or "rows" not in data:
        print(f"auto_fixer: '{FIX_SHEET}' not found or no data; got keys {list(data.keys())}")
        return

    headers = data["headers"]
    rows    = data["rows"]
    H = {h:i for i,h in enumerate(headers)}  # header -> col index

    # Ensure expected columns exist; if not, add them virtually
    expected = ["date","platform","post_type","theme","hook",
                "script_or_caption_url","media_path","cta","utm_link",
                "status","cxo_score","notes"]
    for h in expected:
        if h not in H:
            headers.append(h)
            H[h] = len(headers)-1
            for r in rows:
                r[h] = r.get(h, "")

    updated_matrix = []
    needs_write = False
    for r in rows:
        # Normalize date
        iso = parse_date(r.get("date"))
        if iso:
            if r.get("date") != iso:
                needs_write = True
            r["date"] = iso
        else:
            # mark row for attention but don't crash
            if (r.get("status") or "").lower() != "needs_date":
                r["status"] = "needs_date"
                needs_write = True

        # Normalize status to lowercase canonical set
        st = (r.get("status") or "").strip().lower()
        if st and st not in {"backlog","draft","ready","scheduled","posted","needs_date"}:
            r["status"] = "draft"; needs_write = True

        # UTM link
        utm = build_utm(r)
        if utm != (r.get("utm_link") or "").strip():
            r["utm_link"] = utm; needs_write = True

        # Collect updated row in sheet order
        updated_matrix.append([r.get(h,"") for h in headers])

    if not needs_write:
        print("auto_fixer: nothing to change.")
        return

    # Write back whole table (excluding header)
    last_col = col_letter(len(headers))
    a1 = f"A2:{last_col}{len(updated_matrix)+1}"
    out = api_post({"op":"updateRange","sheet":FIX_SHEET,"a1":a1,"values":updated_matrix})
    print("auto_fixer:", json.dumps(out))

if __name__ == "__main__":
    main()
