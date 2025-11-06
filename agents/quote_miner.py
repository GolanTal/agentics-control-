#!/usr/bin/env python3
import os, re, itertools, requests

APPS_URL   = os.environ["APPS_URL"]
APPS_TOKEN = os.environ["APPS_TOKEN"]
SOURCE_TEXT_URL  = os.environ.get("SOURCE_TEXT_URL", "")
SOURCE_TEXT_PATH = os.environ.get("SOURCE_TEXT_PATH", "sources/book.txt")

BACKLOG_HEADERS = [
  "quote_id","source_type","quote_text","source_reference","location",
  "theme","tone_tag","length_category","platform_fit","owner",
  "consent_status","paraphrase_ok","status","notes"
]

def api_get(sheet):
    r = requests.get(APPS_URL, params={"op":"get","sheet":sheet,"token":APPS_TOKEN}, timeout=60)
    r.raise_for_status(); return r.json()

def api_post(payload):
    data = dict(payload); data["token"] = APPS_TOKEN
    r = requests.post(APPS_URL, json=data, timeout=60)
    r.raise_for_status(); return r.json()

def ensure_sheet():
    return api_post({"op":"ensureSheet","sheet":"Quotes_Backlog","headers":BACKLOG_HEADERS})

def load_text():
    if SOURCE_TEXT_URL:
        r = requests.get(SOURCE_TEXT_URL, timeout=60); r.raise_for_status(); return r.text
    if os.path.exists(SOURCE_TEXT_PATH):
        return open(SOURCE_TEXT_PATH, "r", encoding="utf-8").read()
    return ""

def sentences(text):
    text = re.sub(r"\s+", " ", text.strip())
    parts = re.split(r"(?<=[.!?])\s+", text)
    for s in parts:
        s = s.strip().strip('"“”')
        if 8 <= len(s) <= 180:
            yield s

def uniq(iterable):
    seen=set()
    for x in iterable:
        k=x.lower()
        if k in seen: continue
        seen.add(k); yield x

def classify_length(s):
    n=len(s)
    return "ultra_short" if n<=40 else ("short" if n<=140 else "long")

def fit_for(length):
    return {"ultra_short":"IG,TikTok,Shorts,X","short":"IG,LI,X","long":"LI,X"}[length]

def next_ids(n, existing_rows):
    base=len(existing_rows)+1
    for i in range(n): yield f"Q-{base+i:04d}"

def main():
    ensure_sheet()
    text = load_text()
    if not text:
        print("quote_miner: no SOURCE_TEXT_URL or sources/book.txt; skipping."); return
    cands = list(itertools.islice(uniq(sentences(text)), 50))
    if not cands:
        print("quote_miner: no sentences found."); return
    existing = api_get("Quotes_Backlog").get("rows", [])
    ids = list(next_ids(len(cands), existing))

    rows=[]
    for qid,q in zip(ids,cands):
        length=classify_length(q)
        rows.append([
          qid,"book_internal",q,"The New World: The Key","",
          "Awakening","uplifting",length,fit_for(length),"Architect",
          "not_needed","yes","proposed",""
        ])
    api_post({"op":"appendRows","sheet":"Quotes_Backlog","rows":rows})
    print(f"quote_miner: appended {len(rows)} proposed quotes.")

if __name__=="__main__":
    main()
