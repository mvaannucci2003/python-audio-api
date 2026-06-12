"""
recover_samples.py  --  recover your ElevenLabs sound-effect generations onto
your homebase, into the exact paths your manifests specify.

Confirmed endpoints (reverse-engineered from the logged-in web app, your data):
  LIST :  GET  https://api.us.elevenlabs.io/v1/sound-generation/history?page_size=N
          paginates with start_after_history_item_id; response carries
          last_history_item_id + has_more.
  AUDIO:  GET  https://api.us.elevenlabs.io/v1/sound-generation/history/<id>/audio?convert_to_mpeg=true
          returns audio/mpeg bytes.
Both authenticate with your SESSION BEARER TOKEN (not the xi-api-key).

TOKEN HANDLING
  The Bearer token expires (~<1h). Put it in token.txt (just the token, no
  "Bearer " prefix). The script re-reads token.txt on every request, so when it
  expires you paste a fresh one (copy the Authorization header value from any
  live request in DevTools), save, and it keeps going. On a 401 it pauses.

USAGE (run in order; all phases are safe to re-run):
  python recover_samples.py probe      # 1 request: confirm the list works
  python recover_samples.py plan       # crawl full history, match to manifests
  python recover_samples.py download   # pull audio to AUDIO_ROOT/<file>, resumable
"""

import os
import sys
import csv
import json
import glob
import time
import requests
from collections import defaultdict

# ---------------------------------------------------------------------------
# CONFIG -- edit for your homebase layout
# ---------------------------------------------------------------------------
MANIFEST_DIR = "output/manifests"
AUDIO_ROOT = "output/audio"
HISTORY_INDEX = "sfx_history_index.json"
PLAN_CSV = "recovery_plan.csv"
TOKEN_FILE = "token.txt"

API = "https://api.us.elevenlabs.io/v1"
LIST_URL = f"{API}/sound-generation/history"
AUDIO_URL = API + "/sound-generation/history/{id}/audio"
PAGE_SIZE = 1000

AUDIO_PROMPT_TEMPLATE = "A sound effect of {scenario}. With a '{tag}' quality."

RETRYABLE = {429, 500, 502, 503}
MAX_RETRIES = 5
BASE_BACKOFF = 2


def read_token():
    if os.path.exists(TOKEN_FILE):
        t = open(TOKEN_FILE).read().strip()
        if t:
            return t
    return os.environ.get("ELEVENLABS_BEARER", "").strip()


def _req(method, url, **kw):
    attempt = 0
    while True:
        token = read_token()
        if not token:
            input(
                f"No token. Paste your Bearer token into {TOKEN_FILE}, save, press Enter..."
            )
            continue
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.request(method, url, headers=headers, **kw)
        if r.status_code == 401:
            print("\n401 Unauthorized -- token expired or invalid.")
            input(
                f"Paste a FRESH token into {TOKEN_FILE}, save, then press Enter to continue..."
            )
            continue
        if r.status_code in RETRYABLE:
            attempt += 1
            if attempt >= MAX_RETRIES:
                r.raise_for_status()
            wait = BASE_BACKOFF * (2**attempt) * (2 if r.status_code == 429 else 1)
            ra = r.headers.get("Retry-After")
            if ra:
                try:
                    wait = float(ra)
                except ValueError:
                    pass
            print(f"  {r.status_code} -> retry {attempt}/{MAX_RETRIES} in {wait:.0f}s")
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r


def norm(text):
    return " ".join((text or "").split()).lower()


def expected_text(row):
    return AUDIO_PROMPT_TEMPLATE.format(scenario=row["scenario"], tag=row["tag"])


def file_index(path):
    return int(path.rsplit("_", 1)[-1].split(".")[0])


def load_all_manifest_rows():
    rows = []
    for path in sorted(glob.glob(os.path.join(MANIFEST_DIR, "*.csv"))):
        with open(path, newline="") as f:
            for r in csv.DictReader(f):
                if r.get("file") and r.get("scenario") and r.get("tag"):
                    rows.append(r)
    return rows


def build_plan(manifest_rows, history_items):
    man = defaultdict(list)
    for r in manifest_rows:
        man[norm(expected_text(r))].append(r)
    for g in man.values():
        g.sort(key=lambda r: file_index(r["file"]))
    hist = defaultdict(list)
    for h in history_items:
        hist[norm(h.get("text", ""))].append(h)
    for g in hist.values():
        g.sort(key=lambda h: h.get("created_at_unix", 0))
    plan = []
    for text, rows in man.items():
        hits = hist.get(text, [])
        for i, row in enumerate(rows):
            if i < len(hits):
                plan.append(
                    (row["file"], hits[i]["sound_generation_history_item_id"], "ok")
                )
            else:
                plan.append((row["file"], "", "missing_in_history"))
    return plan


def probe():
    data = _req("GET", LIST_URL, params={"page_size": 5}).json()
    items = data.get("history", [])
    print(
        f"list OK: {len(items)} item(s) on first page; has_more={data.get('has_more')}"
    )
    for it in items:
        print(
            f"  {it.get('sound_generation_history_item_id')}  {(it.get('text') or '')[:70]!r}"
        )


def crawl_history():
    items, cursor, page = [], None, 0
    while True:
        params = {"page_size": PAGE_SIZE}
        if cursor:
            params["start_after_sound_generation_history_item_id"] = cursor
        data = _req("GET", LIST_URL, params=params).json()
        batch = data.get("history", [])
        items.extend(batch)
        page += 1
        print(f"  page {page}: +{len(batch)} (total {len(items)})")
        with open(HISTORY_INDEX, "w") as f:
            json.dump(items, f)
        if not data.get("has_more"):
            break
        cursor = data.get("last_history_item_id")
        if not cursor:
            break
        time.sleep(0.3)
    return items


def plan():
    rows = load_all_manifest_rows()
    print(f"manifest rows across all manifests: {len(rows)}")
    if os.path.exists(HISTORY_INDEX):
        print(f"reusing cached {HISTORY_INDEX} (delete it to re-crawl)")
        items = json.load(open(HISTORY_INDEX))
    else:
        items = crawl_history()
    print(f"history items: {len(items)}")
    p = build_plan(rows, items)
    ok = sum(1 for _, _, s in p if s == "ok")
    miss = len(p) - ok
    with open(PLAN_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "history_item_id", "status"])
        w.writerows(p)
    print(f"plan: {ok} recoverable, {miss} missing -> {PLAN_CSV}")


def download():
    with open(PLAN_CSV, newline="") as f:
        targets = [r for r in csv.DictReader(f) if r["status"] == "ok"]
    print(f"{len(targets)} files to fetch")
    done = skipped = failed = 0
    for i, r in enumerate(targets, 1):
        out = os.path.join(AUDIO_ROOT, r["file"])
        if os.path.exists(out) and os.path.getsize(out) > 0:
            skipped += 1
            continue
        os.makedirs(os.path.dirname(out), exist_ok=True)
        try:
            resp = _req(
                "GET",
                AUDIO_URL.format(id=r["history_item_id"]),
                params={"convert_to_mpeg": "true"},
            )
            with open(out, "wb") as fh:
                fh.write(resp.content)
            done += 1
        except Exception as e:
            print(f"  FAIL {r['file']}: {e}")
            failed += 1
        if i % 200 == 0:
            print(
                f"  {i}/{len(targets)}  saved {done} skipped {skipped} failed {failed}"
            )
        time.sleep(0.15)
    print(f"\ndone. saved {done}, skipped {skipped}, failed {failed}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"probe": probe, "plan": plan, "download": download}.get(
        cmd, lambda: print("usage: python recover_samples.py [probe|plan|download]")
    )()
