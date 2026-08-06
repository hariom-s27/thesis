# =============================================================================
# TRANSCRIPT COLLECTION via ALPHA VANTAGE  (free tier includes transcripts)
#
# FMP's transcript endpoints are paid-only, so we switch providers.
# Alpha Vantage free key: 25 requests/day, ~5 per minute. We need 8. Fits.
#
# Get a free key (instant, no card): https://www.alphavantage.co/support/#api-key
#
# GOAL OF THIS RUN: pull the SAME 8 ExxonMobil quarters you already have as
# PDF excerpts, and compare the word counts. This tests whether the missing
# 20% of your CCExposure is simply missing text.
#
# Setup:  pip install requests
# =============================================================================
import os, time, json
import requests

# ---- API key from .env  (ONLY the key, no URL, no quotes) -------------------
#   .env file must contain exactly one line like:
#       AV_API_KEY=ABCD1234EFGH5678
def load_key():
    key = os.environ.get("AV_API_KEY")
    if key:
        return key.strip()
    envfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(envfile):
        for line in open(envfile):
            if line.strip().startswith("AV_API_KEY"):
                return line.split("=", 1)[1].strip()
    raise SystemExit("No key. Put AV_API_KEY=yourkey in a .env file next to this script.")

API_KEY = load_key()
URL     = "https://www.alphavantage.co/query"
OUT_DIR = "api_transcripts"
os.makedirs(OUT_DIR, exist_ok=True)

# Alpha Vantage wants quarter as "2024Q1"
TARGETS = [("XOM", f"{y}Q{q}") for y in (2024, 2025) for q in (1, 2, 3, 4)]

def fetch(symbol, quarter):
    r = requests.get(URL, params={"function": "EARNINGS_CALL_TRANSCRIPT",
                                  "symbol": symbol, "quarter": quarter,
                                  "apikey": API_KEY}, timeout=60)
    if r.status_code != 200:
        print(f"   HTTP {r.status_code}: {r.text[:200]}")
        return None
    data = r.json()

    # Alpha Vantage reports problems inside a 200 response -- always check.
    for warn in ("Information", "Note", "Error Message"):
        if warn in data:
            print(f"   API says: {str(data[warn])[:180]}")
            return None

    turns = data.get("transcript")
    if not turns:
        print(f"   No transcript for {symbol} {quarter} (keys: {list(data.keys())})")
        return None

    # transcript is a list of speaker turns -> join the 'content' of each
    text = "\n".join(t.get("content", "") for t in turns)
    return text, len(turns)

results = []
for sym, qtr in TARGETS:
    print(f"Fetching {sym} {qtr} ...")
    got = fetch(sym, qtr)
    if got:
        text, nturns = got
        path = os.path.join(OUT_DIR, f"{sym}_{qtr}.txt")
        open(path, "w", encoding="utf-8").write(text)
        results.append(dict(symbol=sym, quarter=qtr, words=len(text.split()),
                            turns=nturns, path=path))
        print(f"   saved {len(text.split()):,} words from {nturns} speaker turns")
    time.sleep(15)      # free tier ~5 req/min -> stay well under the limit

# ---- THE COMPARISON ---------------------------------------------------------
print("\n" + "=" * 60)
print("ALPHA VANTAGE TRANSCRIPT SIZES")
print("=" * 60)
for r in results:
    print(f"  {r['symbol']} {r['quarter']}: {r['words']:>7,} words  ({r['turns']} turns)")

if results:
    avg = sum(r["words"] for r in results) / len(results)
    print(f"\n  average: {avg:,.0f} words")
    print("  your PDF excerpts: about 3,500-4,000 words each")
    print(f"  ratio: {avg/3800:.1f}x")
    print("\nHOW TO READ THIS:")
    print("  ratio >> 1  -> excerpts theory CONFIRMED; rerun scoring on this folder")
    print("  ratio ~= 1  -> theory WRONG; the 20% gap is caused by something else")

# NEXT: these are .txt not .pdf, so in exact_reproduction.py switch
#   glob '*.pdf' -> '*.txt'  and  read_pdf(p) -> open(p, encoding='utf-8').read()
# then check whether 79.6% moves toward 100%.