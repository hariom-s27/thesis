# =============================================================================
# BULK TRANSCRIPT COLLECTOR  (Alpha Vantage)
#
# Built around ONE hard constraint: the free tier gives ~25 requests/day.
# So this script is designed to be run REPEATEDLY over several days:
#   - it SKIPS anything already downloaded  (resume)
#   - it STOPS when the daily budget is spent (no wasted/failed calls)
#   - it LOGS every attempt so you know what is missing
#
# WHY 4 QUARTERS PER FIRM: the official cc_expo_ew is the average across all
# quarters of the year. If you download only 2 quarters, you are comparing a
# 2-quarter average against a 4-quarter average -- that is a measurement error
# you created yourself. Always fetch all 4 quarters of any year you use.
#
# Setup:  pip install requests
# =============================================================================
import os, time, json, csv
import requests

# ---- config -----------------------------------------------------------------
OUT_DIR      = r"D:\sem_iitk\sem 8\thesis\api_transcripts"
LOG_CSV      = r"D:\sem_iitk\sem 8\thesis\outputs\download_log.csv"
YEARS        = [2025]          # official CSV ends at 2024 -> never fetch beyond it
DAILY_BUDGET = 24              # keep 1 spare below the 25/day limit
SLEEP_SEC    = 15              # ~4 calls/min, safely under the per-minute cap

# ---- firms: ticker -> ISIN --------------------------------------------------
# The API speaks TICKERS. The official CSV speaks ISIN. You need the bridge, and
# you must build it BEFORE downloading, or you will end up with files you cannot
# match to ground truth. Verify each ISIN once (Google "<company> ISIN") and it
# is done forever. Start with a spread of industries: climate exposure differs
# hugely between oil, utilities, banks and software -- a sample of only oil
# firms would give you a correlation that says nothing about the general case.
FIRMS = {
    "XOM":  "US30231G1022",   # ExxonMobil        - oil & gas   (already verified)
    "CVX":  "US1667641005",   # Chevron           - oil & gas
    "COP":  "US20825C1045",   # ConocoPhillips    - oil & gas
    "OXY":  "US6745991058",   # Occidental        - oil & gas
    "NEE":  "US65339F1012",   # NextEra Energy    - utilities
    "DUK":  "US26441C2044",   # Duke Energy       - utilities
    "SO":   "US8425871071",   # Southern Co       - utilities
    "D":    "US25746U1097",   # Dominion Energy   - utilities
    "DAL":  "US2473617023",   # Delta Air Lines   - airlines
    "GM":   "US37045V1008",   # General Motors    - autos
    "F":    "US3453708600",   # Ford              - autos
    "CAT":  "US1491231015",   # Caterpillar       - machinery
    "BA":   "US0970231058",   # Boeing            - aerospace
    "JPM":  "US46625H1005",   # JPMorgan          - banking
    "MSFT": "US5949181045",   # Microsoft         - software
    "WMT":  "US9311421039",   # Walmart           - retail
    "PFE":  "US7170811035",   # Pfizer            - pharma
    "KO":   "US1912161007",   # Coca-Cola         - consumer
    "UNH":  "US91324P1021",   # UnitedHealth      - healthcare
}

# ---- key --------------------------------------------------------------------
def load_key():
    k = os.environ.get("AV_API_KEY")
    if k: return k.strip()
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(p):
        for line in open(p):
            if line.strip().startswith("AV_API_KEY"):
                return line.split("=", 1)[1].strip()
    raise SystemExit("Put AV_API_KEY=yourkey in .env next to this script.")

API_KEY = load_key()
URL = "https://www.alphavantage.co/query"
os.makedirs(OUT_DIR, exist_ok=True)

# ---- build the full job list, then subtract what we already have ------------
jobs = [(t, f"{y}Q{q}") for t in FIRMS for y in YEARS for q in (1, 2, 3, 4)]
todo = [(t, q) for t, q in jobs
        if not os.path.exists(os.path.join(OUT_DIR, f"{t}_{q}.txt"))]

print(f"total jobs: {len(jobs)} | already have: {len(jobs)-len(todo)} | remaining: {len(todo)}")
if not todo:
    print("Nothing left to download.")
    raise SystemExit(0)
print(f"this run will attempt: {min(DAILY_BUDGET, len(todo))}")
print(f"at {DAILY_BUDGET}/day this needs about {-(-len(todo)//DAILY_BUDGET)} more day(s)\n")

def fetch(symbol, quarter):
    r = requests.get(URL, params={"function": "EARNINGS_CALL_TRANSCRIPT",
                                  "symbol": symbol, "quarter": quarter,
                                  "apikey": API_KEY}, timeout=60)
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}"
    d = r.json()
    for w in ("Information", "Note", "Error Message"):
        if w in d:
            return None, str(d[w])[:120]
    turns = d.get("transcript")
    if not turns:
        return None, "no transcript"
    return "\n".join(t.get("content", "") for t in turns), f"{len(turns)} turns"

# ---- run --------------------------------------------------------------------
log_rows, used = [], 0
for sym, qtr in todo:
    if used >= DAILY_BUDGET:
        print("\nDaily budget reached. Run again tomorrow -- it will resume.")
        break
    print(f"[{used+1}/{DAILY_BUDGET}] {sym} {qtr} ...", end=" ")
    text, note = fetch(sym, qtr)
    used += 1
    if text:
        open(os.path.join(OUT_DIR, f"{sym}_{qtr}.txt"), "w", encoding="utf-8").write(text)
        words = len(text.split())
        print(f"OK {words:,} words ({note})")
        log_rows.append(dict(symbol=sym, isin=FIRMS[sym], quarter=qtr,
                             status="ok", words=words, note=note))
    else:
        print(f"FAIL - {note}")
        log_rows.append(dict(symbol=sym, isin=FIRMS[sym], quarter=qtr,
                             status="fail", words=0, note=note))
        # If the API says the daily limit is hit, stop -- further calls are wasted.
        if "limit" in note.lower() or "frequency" in note.lower():
            print("Rate limit hit. Stopping.")
            break
    time.sleep(SLEEP_SEC)

# ---- append to the log ------------------------------------------------------
new = not os.path.exists(LOG_CSV)
with open(LOG_CSV, "a", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["symbol","isin","quarter","status","words","note"])
    if new: w.writeheader()
    w.writerows(log_rows)

ok = sum(1 for r in log_rows if r["status"] == "ok")
print(f"\nthis run: {ok} saved, {len(log_rows)-ok} failed. Log -> {LOG_CSV}")

# ---- save the ticker->ISIN bridge for the scoring step ----------------------
MAP_JSON = r"D:\sem_iitk\sem 8\thesis\outputs\ticker_isin_map.json"
with open(MAP_JSON, "w") as f:
    json.dump(FIRMS, f, indent=2)
print(f"ticker -> ISIN map saved to {MAP_JSON}")
