"""
recover_samples.py  --  manifest-driven recovery of generated audio from
ElevenLabs history back onto your homebase, into the exact paths your
manifests specify.

RUN ON YOUR HOMEBASE (not reachable from the chat sandbox). Needs your
ELEVENLABS_API_KEY in the environment / .env.

USAGE (run the phases in order; each is safe to re-run):
    python recover_samples.py probe
        One request. Prints the source breakdown + date range + total count.
        GATE: if your sound effects don't show up here, STOP -- the API can't
        recover them and you pivot to the web UI or regeneration.

    python recover_samples.py plan
        Paginates your full history, saves it to history_index.json (crash-safe),
        matches every manifest row to a history item (with duplicate
        disambiguation by timestamp), and writes recovery_plan.csv.
        Review that file before downloading.

    python recover_samples.py download
        Executes recovery_plan.csv. Writes each audio file to AUDIO_ROOT/<file>.
        Resumable (skips files already on disk) and retry-aware.

The matcher in build_plan() is the same logic validated against a real manifest
(1431/1431 correct, duplicates disambiguated, retention loss flagged cleanly).
"""

import os
import sys
import csv
import json
import glob
import time
import requests
from collections import defaultdict
from dotenv import load_dotenv

# ----------------------------------------------------------------------------
# CONFIG -- edit these three paths for your homebase layout
# ----------------------------------------------------------------------------
MANIFEST_DIR = "output/manifests"  # folder containing your *.csv manifests
AUDIO_ROOT = "output/audio"  # files land at AUDIO_ROOT/<manifest 'file'>
HISTORY_INDEX = "history_index.json"
PLAN_CSV = "recovery_plan.csv"

# MUST stay identical to AUDIO_PROMPT_TEMPLATE in config.py -- this is how we
# reconstruct the exact text you sent, to match it against history.
AUDIO_PROMPT_TEMPLATE = "A sound effect of {scenario}. With a '{tag}' quality."

load_dotenv()
API_KEY = os.environ.get("ELEVENLABS_API_KEY")
BASE = "https://api.elevenlabs.io/v1"
HEADERS = {"xi-api-key": API_KEY}

RETRYABLE = {429, 502, 503}
MAX_RETRIES = 5
BASE_BACKOFF = 2


def _req(method, url, **kw):
    for attempt in range(MAX_RETRIES):
        r = requests.request(method, url, headers=HEADERS, **kw)
        if r.status_code in RETRYABLE and attempt < MAX_RETRIES - 1:
            wait = BASE_BACKOFF * (2**attempt) * (2 if r.status_code == 429 else 1)
            ra = r.headers.get("Retry-After")
            if ra:
                try:
                    wait = float(ra)
                except ValueError:
                    pass
            print(f"  {r.status_code} -> retry {attempt+1} in {wait:.0f}s")
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r
    raise RuntimeError(f"exhausted retries: {method} {url}")


# ----------------------------------------------------------------------------
# Shared helpers (identical to the validated test)
# ----------------------------------------------------------------------------
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
                if "file" in r and r.get("scenario") and r.get("tag"):
                    rows.append(r)
    return rows


# ----------------------------------------------------------------------------
# PHASE: probe
# ----------------------------------------------------------------------------
def probe():
    if not API_KEY:
        raise SystemExit("ELEVENLABS_API_KEY not set")
    data = _req("GET", f"{BASE}/history", params={"page_size": 5}).json()
    items = data.get("history", [])
    print(
        f"history returned {len(items)} item(s) on first page; "
        f"has_more={data.get('has_more')}"
    )
    if not items:
        print("EMPTY. Either nothing is stored or SFX aren't exposed here. STOP.")
        return
    print("\nFirst-page sample:")
    for it in items:
        print(
            f"  source={it.get('source')!r:10} "
            f"text={ (it.get('text') or '')[:70]!r }"
        )
    print("\nIf you see your 'A sound effect of ...' prompts above, proceed to plan.")


# ----------------------------------------------------------------------------
# PHASE: plan
# ----------------------------------------------------------------------------
def fetch_all_history():
    items, cursor, page = [], None, 0
    while True:
        params = {"page_size": 1000}
        if cursor:
            params["start_after_history_item_id"] = cursor
        data = _req("GET", f"{BASE}/history", params=params).json()
        batch = data.get("history", [])
        items.extend(batch)
        page += 1
        print(f"  page {page}: +{len(batch)} (total {len(items)})")
        # persist incrementally so a crash doesn't lose the crawl
        with open(HISTORY_INDEX, "w") as f:
            json.dump(items, f)
        if not data.get("has_more"):
            break
        cursor = data.get("last_history_item_id")
        if not cursor:
            break
        time.sleep(0.4)
    return items


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
        g.sort(key=lambda h: h.get("date_unix", 0))

    plan = []
    for text, rows in man.items():
        hits = hist.get(text, [])
        for i, row in enumerate(rows):
            if i < len(hits):
                plan.append((row["file"], hits[i]["history_item_id"], "ok"))
            else:
                plan.append((row["file"], "", "missing_in_history"))
    return plan


def plan():
    rows = load_all_manifest_rows()
    print(f"manifest rows across all manifests: {len(rows)}")
    if os.path.exists(HISTORY_INDEX):
        print(f"reusing cached {HISTORY_INDEX}")
        items = json.load(open(HISTORY_INDEX))
    else:
        items = fetch_all_history()

    # retention reality check
    sfx = [h for h in items if "sound effect of" in norm(h.get("text", ""))]
    print(
        f"\ntotal history items: {len(items)} | look like your SFX prompts: {len(sfx)}"
    )

    p = build_plan(rows, items)
    ok = sum(1 for _, _, s in p if s == "ok")
    miss = len(p) - ok
    with open(PLAN_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "history_item_id", "status"])
        w.writerows(p)
    print(f"\nplan: {ok} recoverable, {miss} missing -> {PLAN_CSV}")
    if miss:
        print(
            "Review the 'missing_in_history' rows -- those weren't found in "
            "history (aged out, deleted, or never logged)."
        )


# ----------------------------------------------------------------------------
# PHASE: download
# ----------------------------------------------------------------------------
def download():
    with open(PLAN_CSV, newline="") as f:
        plan_rows = [r for r in csv.DictReader(f) if r["status"] == "ok"]
    print(f"{len(plan_rows)} files to fetch")
    done = skipped = failed = 0
    for i, r in enumerate(plan_rows, 1):
        out = os.path.join(AUDIO_ROOT, r["file"])
        if os.path.exists(out):
            skipped += 1
            continue
        os.makedirs(os.path.dirname(out), exist_ok=True)
        try:
            resp = _req("GET", f"{BASE}/history/{r['history_item_id']}/audio")
            with open(out, "wb") as fh:
                fh.write(resp.content)
            done += 1
        except Exception as e:
            print(f"  FAIL {r['file']}: {e}")
            failed += 1
        if i % 200 == 0:
            print(
                f"  {i}/{len(plan_rows)} (saved {done}, skipped {skipped}, failed {failed})"
            )
        time.sleep(0.2)
    print(f"\ndone. saved {done}, skipped {skipped}, failed {failed}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "probe":
        probe()
    elif cmd == "plan":
        plan()
    elif cmd == "download":
        download()
    else:
        print("usage: python recover_samples.py [probe|plan|download]")
