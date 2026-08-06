# =============================================================================
# MULTI-PROVIDER TRANSCRIPT COLLECTOR
#
# Problem: Alpha Vantage free = 25 requests/DAY. 10 firms x 3 years x 4 quarters
# = 120 calls = 5 days of waiting.
#
# Solution: use TWO providers. They have separate, independent quotas:
#   - Alpha Vantage : ~25 requests/DAY
#   - API Ninjas    : monthly quota, free key, last 5 years of transcripts
# When one refuses, the script automatically tries the other. This is not a
# trick -- each account is used within its own free-tier terms (academic,
# non-commercial use).
#
# Get free keys:
#   Alpha Vantage : https://www.alphavantage.co/support/#api-key
#   API Ninjas    : https://api-ninjas.com/  (sign up -> instant key)
#
# .env file (same folder), TWO lines, keys only -- no URLs, no quotes:
#   AV_API_KEY=xxxxxxxx
#   NINJA_API_KEY=yyyyyyyy
#
# Setup:  pip install requests
# =============================================================================
import os, time, json, csv
import requests

# ---- config -----------------------------------------------------------------
BASE       = r"D:\sem_iitk\sem 8\thesis"          # absolute -> always same folder
OUT_DIR    = os.path.join(BASE, "api_transcripts")
LOG_CSV    = os.path.join(BASE, "download_log.csv")
MAP_JSON   = os.path.join(BASE, "ticker_isin_map.json")
EMPTY_JSON = os.path.join(BASE, "confirmed_empty.json")   # quarters confirmed to have no transcript -- never re-spend a call on these

YEARS      = list(range(2007, 2025))   # pre-2007 mostly empty based on XOM/CVX pattern -- start here; never go PAST 2024
SLEEP_SEC  = 13                    # polite pacing
MAX_CALLS  = 200                   # hard stop so one run can't burn everything

MY_SHARE   = 0      # person A = 0, person B = 1, person C = 2
NUM_PEOPLE = 1       # temporarily solo -- claim ALL remaining jobs to finish the last 15

ONLY_TICKER = None  # e.g. "JPM" -- if set, download ONLY this one company
                     # (ignores MY_SHARE/NUM_PEOPLE; use this when each person
                     # owns one company instead of splitting jobs round-robin)

# ---- firms: ticker -> ISIN (VERIFY each one before trusting it) -------------
FIRMS = {
    # energy / utilities (high climate talk)
    "XOM":  "US30231G1022",   "CVX":  "US1667641005",
    "NEE":  "US65339F1012",   "DUK":  "US26441C2044",
    # industrials / autos (medium)
    "GM":   "US37045V1008",   "F":    "US3453708600",
    "CAT":  "US1491231015",   "BA":   "US0970231058",
    # finance / tech / consumer (low climate talk -- YOU NEED THESE for spread)
    "JPM":  "US46625H1005",   "MSFT": "US5949181045",
    "WMT":  "US9311421039",   "PFE":  "US7170811035",
    "KO":   "US1912161007",   "UNH":  "US91324P1021",
}

# ---- keys -------------------------------------------------------------------
# .env supports either a single key:
#   AV_API_KEY=xxxxxxxx
# or a pool of keys to rotate through as each one hits its daily cap:
#   AV_API_KEYS=key1,key2,key3,key4,key5,key6
def load_env():
    vals = {}
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(p):
        for line in open(p):
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip()
    for k in ("AV_API_KEY", "AV_API_KEYS", "NINJA_API_KEY"):
        if os.environ.get(k):
            vals[k] = os.environ[k].strip()
    return vals

ENV = load_env()
if ENV.get("AV_API_KEYS"):
    AV_KEY_POOL = [k.strip() for k in ENV["AV_API_KEYS"].split(",") if k.strip()]
elif ENV.get("AV_API_KEY"):
    AV_KEY_POOL = [ENV["AV_API_KEY"]]
else:
    AV_KEY_POOL = []
_av_idx  = 0        # index of the AV key currently in use
NJ_KEY   = None      # API Ninjas transcripts are premium-only
os.makedirs(OUT_DIR, exist_ok=True)
print(f"providers available -> AlphaVantage: {len(AV_KEY_POOL)} key(s) | API Ninjas: {bool(NJ_KEY)}")
if not (AV_KEY_POOL or NJ_KEY):
    raise SystemExit("No keys found in .env")

# ---- provider 1: Alpha Vantage ----------------------------------------------
# Two DIFFERENT kinds of throttling look similar but need opposite handling:
#   - DAILY cap ("25 requests per day")     -> this key is done for today;
#                                              rotate to the next key.
#   - PER-MINUTE pacing ("spreading out your
#     free API requests more sparingly")    -> transient; back off and retry
#                                              the SAME key/job, don't burn a
#                                              key rotation on it.
# Tries the current key; on daily exhaustion advances to the next key in the
# pool; on pacing throttle, backs off and retries a few times before giving up
# for this run (the job stays undone and will be picked up on the next run).
PACING_RETRIES = 3
PACING_BACKOFF_SEC = 60

NETWORK_RETRIES = 2
NETWORK_BACKOFF_SEC = 5

def fetch_av(sym, year, q):
    global _av_idx
    while _av_idx < len(AV_KEY_POOL):
        key = AV_KEY_POOL[_av_idx]
        for attempt in range(PACING_RETRIES + 1):
            for net_attempt in range(NETWORK_RETRIES + 1):
                try:
                    r = requests.get("https://www.alphavantage.co/query",
                                     params={"function": "EARNINGS_CALL_TRANSCRIPT", "symbol": sym,
                                             "quarter": f"{year}Q{q}", "apikey": key}, timeout=60)
                    break
                except requests.exceptions.RequestException as e:
                    if net_attempt < NETWORK_RETRIES:
                        print(f"[network error, retry {net_attempt+1}/{NETWORK_RETRIES}] ", end="")
                        time.sleep(NETWORK_BACKOFF_SEC)
                    else:
                        return None, f"network error: {type(e).__name__}", False
            if r.status_code != 200:
                return None, f"HTTP {r.status_code}", False
            d = r.json()
            msg = None
            for w in ("Information", "Note", "Error Message"):
                if w in d:
                    msg = str(d[w])[:150]
                    break
            if msg is None:
                turns = d.get("transcript")
                if not turns:
                    return None, "no transcript", False
                return "\n".join(t.get("content", "") for t in turns), f"{len(turns)} turns", False

            ml = msg.lower()
            daily_exhausted = "requests per day" in ml or ("rate limit" in ml and "day" in ml)
            pacing_throttle = "spreading out" in ml or "more sparingly" in ml or "frequency" in ml

            if daily_exhausted:
                print(f"[key {_av_idx+1}/{len(AV_KEY_POOL)} exhausted] ", end="")
                _av_idx += 1
                break   # try the next key in the pool for this same job
            if pacing_throttle and attempt < PACING_RETRIES:
                print(f"[paced, retry {attempt+1}/{PACING_RETRIES} in {PACING_BACKOFF_SEC}s] ", end="")
                time.sleep(PACING_BACKOFF_SEC)
                continue   # retry the SAME key, same job
            return None, msg, False   # real error, or pacing retries exhausted
    return None, "all AV keys exhausted", True

# ---- provider 2: API Ninjas -------------------------------------------------
def fetch_nj(sym, year, q):
    r = requests.get("https://api.api-ninjas.com/v1/earningscalltranscript",
                     params={"ticker": sym, "year": year, "quarter": q},
                     headers={"X-Api-Key": NJ_KEY}, timeout=60)
    if r.status_code == 429:
        return None, "quota exhausted (429)", True
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}: {r.text[:80]}", False
    d = r.json()
    if not d:
        return None, "no transcript", False
    rec = d[0] if isinstance(d, list) else d
    txt = rec.get("transcript") or rec.get("content") or ""
    if not txt:
        return None, f"empty (keys: {list(rec.keys())[:5]})", False
    return txt, "ok", False

PROVIDERS = []
if AV_KEY_POOL: PROVIDERS.append(("alphavantage", fetch_av))
if NJ_KEY:      PROVIDERS.append(("apininjas",    fetch_nj))
dead = set()          # providers whose quota is exhausted this run

# ---- confirmed-empty quarters: never re-spend a call re-checking these ------
def load_empty():
    if os.path.exists(EMPTY_JSON):
        return set(json.load(open(EMPTY_JSON)))
    return set()

def save_empty(s):
    json.dump(sorted(s), open(EMPTY_JSON, "w"), indent=2)

CONFIRMED_EMPTY = load_empty()
print(f"confirmed-empty quarters on file: {len(CONFIRMED_EMPTY)} (will be skipped)")

def already_known(t, y, q):
    return (os.path.exists(os.path.join(OUT_DIR, f"{t}_{y}Q{q}.txt"))
            or f"{t}_{y}Q{q}" in CONFIRMED_EMPTY)

# ---- job list, minus what we already have or already know is empty ----------
if ONLY_TICKER:
    if ONLY_TICKER not in FIRMS:
        raise SystemExit(f"{ONLY_TICKER!r} is not in FIRMS -- add it there first")
    jobs = [(ONLY_TICKER, y, q) for y in YEARS for q in (1, 2, 3, 4)]
    todo = [(t, y, q) for t, y, q in jobs if not already_known(t, y, q)]
    print(f"restricted to {ONLY_TICKER}: {len(jobs)} jobs | already have/known-empty: "
          f"{len(jobs)-len(todo)} | remaining: {len(todo)}")
else:
    jobs = [(t, y, q) for t in FIRMS for y in YEARS for q in (1, 2, 3, 4)]
    todo = [(t, y, q) for t, y, q in jobs if not already_known(t, y, q)]
    print(f"total jobs: {len(jobs)} | already have/known-empty: {len(jobs)-len(todo)} | remaining: {len(todo)}\n")
    todo = [job for i, job in enumerate(todo) if i % NUM_PEOPLE == MY_SHARE]
    print(f"my share: {len(todo)} jobs")
if not todo:
    print("Nothing left to download."); raise SystemExit(0)

# ---- run --------------------------------------------------------------------
log_rows, used = [], 0
for sym, yr, q in todo:
    if used >= MAX_CALLS or len(dead) == len(PROVIDERS):
        print("\nStopping: all providers exhausted (or call cap reached). "
              "Run again later -- it will resume automatically.")
        break
    text = note = None
    for pname, fn in PROVIDERS:
        if pname in dead:
            continue
        print(f"[{used+1}] {sym} {yr}Q{q} via {pname} ...", end=" ")
        text, note, exhausted = fn(sym, yr, q)
        used += 1
        if exhausted:
            print(f"QUOTA DONE ({note})"); dead.add(pname); text = None
            continue
        if text:
            print(f"OK {len(text.split()):,} words"); break
        print(f"fail - {note}")
        time.sleep(2)
    if text:
        open(os.path.join(OUT_DIR, f"{sym}_{yr}Q{q}.txt"), "w",
             encoding="utf-8").write(text)
        log_rows.append(dict(symbol=sym, isin=FIRMS[sym], quarter=f"{yr}Q{q}",
                             status="ok", words=len(text.split()), note=note))
    else:
        log_rows.append(dict(symbol=sym, isin=FIRMS[sym], quarter=f"{yr}Q{q}",
                             status="fail", words=0, note=str(note)[:100]))
        if note == "no transcript":   # genuinely confirmed empty -- never re-check
            CONFIRMED_EMPTY.add(f"{sym}_{yr}Q{q}")
            save_empty(CONFIRMED_EMPTY)
    time.sleep(SLEEP_SEC)

# ---- log + map --------------------------------------------------------------
new = not os.path.exists(LOG_CSV)
with open(LOG_CSV, "a", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["symbol","isin","quarter","status","words","note"])
    if new: w.writeheader()
    w.writerows(log_rows)
json.dump(FIRMS, open(MAP_JSON, "w"), indent=2)
print(f"confirmed-empty quarters on file: {len(CONFIRMED_EMPTY)}")

ok = sum(1 for r in log_rows if r["status"] == "ok")
have = len([f for f in os.listdir(OUT_DIR) if f.endswith(".txt")])
print(f"\nthis run: {ok} saved | total transcripts on disk: {have}")
print(f"complete firm-years possible: ~{have//4} (need 4 quarters each; target 20+)")
