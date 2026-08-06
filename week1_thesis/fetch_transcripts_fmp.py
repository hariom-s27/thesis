# =============================================================================
# STEP 1 OF DATA COLLECTION — test the API on data you ALREADY know
#
# WHY THIS TEST: your 8 PDFs are "Excerpts" and gave 79.6% of the official
# CCExposure. Theory: the missing 20% is missing text. This script pulls the
# SAME 8 ExxonMobil quarters from the API and compares word counts. If the API
# text is much longer, the theory is confirmed. If it is the same length, the
# theory is WRONG and we look elsewhere. Either answer is useful.
#
# Never test a new data source on unknown data. Test it where you know the answer.
#
# Setup:  pip install requests
# =============================================================================
import os, json, time, glob
import requests

# ---- API KEY: never hardcode it ---------------------------------------------
# Make a file named  .env  next to this script containing ONE line:
#     FMP_API_KEY=your_new_key_here
# Then add  .env  to your .gitignore so it never reaches GitHub.
def load_key():
    key = os.environ.get("FMP_API_KEY")
    if key:
        return key
    envfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(envfile):
        for line in open(envfile):
            if line.strip().startswith("FMP_API_KEY"):
                return line.split("=", 1)[1].strip()
    raise SystemExit("No API key found. Create a .env file with FMP_API_KEY=...")

API_KEY = load_key()
BASE    = "https://financialmodelingprep.com/stable/earning-call-transcript"

OUT_DIR        = "api_transcripts"      # where JSON+txt get saved
PDF_DIR        = r"D:\sem_iitk\sem 8\thesis\old _work\transcript"   # your excerpts
os.makedirs(OUT_DIR, exist_ok=True)

# ---- what to fetch: the same 8 quarters you already have --------------------
TARGETS = [("XOM", 2024, q) for q in (1, 2, 3, 4)] + \
          [("XOM", 2025, q) for q in (1, 2, 3, 4)]

def fetch(symbol, year, quarter):
    """Return transcript text, or None if unavailable."""
    r = requests.get(BASE, params={"symbol": symbol, "year": year,
                                   "quarter": quarter, "apikey": API_KEY},
                     timeout=60)
    if r.status_code != 200:
        print(f"  HTTP {r.status_code} for {symbol} {year} Q{quarter}: {r.text[:200]}")
        return None
    data = r.json()
    if not data:                      # empty list = no transcript on this plan
        print(f"  EMPTY response for {symbol} {year} Q{quarter} (plan limit?)")
        return None
    rec = data[0] if isinstance(data, list) else data
    # field name has been 'content' historically; fall back if they rename it
    for field in ("content", "transcript", "text"):
        if field in rec and rec[field]:
            return rec[field]
    print("  Unexpected fields:", list(rec.keys()))
    return None

# ---- pull them --------------------------------------------------------------
results = []
for sym, yr, q in TARGETS:
    print(f"Fetching {sym} {yr} Q{q} ...")
    txt = fetch(sym, yr, q)
    if txt:
        path = os.path.join(OUT_DIR, f"{sym}_{yr}_Q{q}.txt")
        open(path, "w", encoding="utf-8").write(txt)
        results.append(dict(symbol=sym, year=yr, quarter=q,
                            words=len(txt.split()), chars=len(txt), path=path))
        print(f"   saved {len(txt.split()):,} words")
    time.sleep(1)      # be polite to the API; avoids rate-limit errors

# ---- THE COMPARISON: API vs your PDF excerpts -------------------------------
print("\n" + "=" * 62)
print("API TRANSCRIPT SIZES")
print("=" * 62)
for r in results:
    print(f"  {r['symbol']} {r['year']} Q{r['quarter']}: {r['words']:>7,} words")

print("\nYour PDF excerpts produced roughly 3,500-4,000 BIGRAMS each,")
print("which is roughly 3,500-4,000 words each.")
print("\nHOW TO READ THIS:")
print("  API words >> 4,000  -> excerpts theory CONFIRMED, use API data")
print("  API words ~= 4,000  -> theory WRONG, the gap is something else")
print("  Empty/HTTP 403      -> transcripts not included in your free plan")

# NEXT STEP once this looks good: point TRANSCRIPT_DIR in exact_reproduction.py
# at the api_transcripts folder (and switch read_pdf -> plain text reading),
# then check whether 79.6% moves toward 100%.
