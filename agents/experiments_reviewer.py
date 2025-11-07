#!/usr/bin/env python3
import os, json, re, time
import requests

APPS_URL   = os.environ["APPS_URL"]
APPS_TOKEN = os.environ["APPS_TOKEN"]
REVIEW_FROM_SHEET = os.getenv("REVIEW_FROM_SHEET", "Experiments")

def api_get(sheet):
    r = requests.get(APPS_URL,
                     params={"op":"get","sheet":sheet,"token":APPS_TOKEN},
                     timeout=60)
    r.raise_for_status()
    return r.json()

# simple heuristics
def has(value): return bool(str(value or "").strip())
def too_long(s, n): return len(str(s or "")) > n

def scan_row(rownum:int, r:dict):
    ts = int(time.time())

    # required fields
    required = ["idea","hypothesis","metric","owner"]
    for f in required:
        if not has(r.get(f)):
            yield (ts,"missing", rownum, f, r.get(f), "required field is empty", "fill value", "warn")

    # hook length
    if too_long(r.get("hook"), 140):
        yield (ts,"length", rownum, "hook", r.get("hook"), "hook too long", "shorten to <=140", "info")

    # platform sanity
    plat = (r.get("platform") or "").strip().lower()
    if plat and plat not in {"instagram","tiktok","x","linkedin","youtube","shorts"}:
        yield (ts,"platform", rownum, "platform", r.get("platform"), "unknown platform", "pick from IG/TikTok/X/LI/YouTube", "warn")

def main():
    data = api_get(REVIEW_FROM_SHEET)
    headers = data.get("headers") or []
    rows    = data.get("rows") or []

    if not headers or not rows:
        print("experiments_reviewer: no rows.")
        return

    H = {h:i for i,h in enumerate(headers)}

    findings = []
    for i, r in enumerate(rows, start=2):
        for f in scan_row(i, r):
            # tolerate 7-tuple legacy
            if len(f) == 7:
                f = (*f, "info")
            findings.append(f)

    if not findings:
        print("experiments_reviewer: no issues found.")
        return

    # Print a compact JSON payload (HITL could consume this)
    out = [{
        "ts":f[0], "tag":f[1], "row":f[2], "field":f[3],
        "value":f[4], "problem":f[5], "suggested":f[6], "severity":f[7]
    } for f in findings]

    print(json.dumps({"sheet": REVIEW_FROM_SHEET, "findings": out}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
