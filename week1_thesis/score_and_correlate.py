# =============================================================================
# MULTI-FIRM SCORING + CORRELATION  -- your headline thesis result
#
# One firm at 97.3% could be luck. Many firms cannot be. This script scores
# every transcript in api_transcripts/, aggregates to firm-year, matches to the
# official published scores by ISIN, and reports the CORRELATION.
#
# Target sentence for the thesis:
#   "Across N firm-years, the reproduced CCExposure correlates r = 0.9x with
#    the published measure of Sautner et al. (2023)."
#
# Run this after collect_bulk_transcripts.py has gathered data.
# =============================================================================
import os, glob, re, json, pickle
import numpy as np, pandas as pd, spacy
from nltk.tokenize import sent_tokenize
from sklearn.feature_extraction.text import CountVectorizer

# ---- paths (EDIT) -----------------------------------------------------------
TRANSCRIPT_DIR = r"D:\sem_iitk\sem 8\thesis\api_transcripts"
DICT_DIR       = r"D:\sem_iitk\sem 8\thesis\old _work\code\jofi13219-sup-0002-replicationcode\Replication Files Sautner et al. (2023)\B. Figure 1 2, Table 2, and IA Table 6 7 8 9 11\bigrams"
OFFICIAL_CSV   = r"D:\sem_iitk\sem 8\thesis\old _work\csv\firmyear_score_2024Q4_Version_2025_Jul_03.csv"
OUTPUT_DIR     = r"D:\sem_iitk\sem 8\thesis\outputs"
MAP_JSON       = os.path.join(OUTPUT_DIR, "ticker_isin_map.json")     # written by collect_bulk_transcripts.py

# ---- dictionaries -----------------------------------------------------------
def _d(n):
    with open(os.path.join(DICT_DIR, n), "rb") as f:
        return set(x.lower() for x in pickle.load(f))
CC, OP = _d("bigrams_07222021.pkl"), _d("opportunity_bigrams_4.pkl")
RG, PH = _d("regulatory_bigrams_4.pkl"), _d("physical_bigrams_4.pkl")

nlp = spacy.load("en_core_web_sm", disable=["ner", "parser"])
nlp.add_pipe("sentencizer")
vec = CountVectorizer(analyzer="word", strip_accents="unicode",
                      ngram_range=(2, 2), lowercase=True, stop_words="english")

def lemma_sents(text):
    out = []
    for s in sent_tokenize(text):
        d = nlp(s)
        l = [t.lemma_.lower() for t in d if not t.is_space and not t.is_punct]
        if l: out.append(" ".join(l))
    return out

def score(sents):
    M = vec.fit_transform(sents)
    feats = np.array(vec.get_feature_names_out())
    counts = np.asarray(M.sum(axis=0)).ravel()
    B = int(counts.sum())
    freq = dict(zip(feats, counts))
    hit = lambda D: sum(freq[b] for b in (set(feats) & D))
    return dict(B=B, cc_expo=hit(CC)/B, op_expo=hit(OP)/B,
                rg_expo=hit(RG)/B, ph_expo=hit(PH)/B)

# ---- 1. score every transcript ---------------------------------------------
PAT = re.compile(r"^([A-Z\.\-]+)_(\d{4})Q([1-4])", re.I)
rows, skipped = [], []
files = sorted(glob.glob(os.path.join(TRANSCRIPT_DIR, "*.txt")))
print(f"files found: {len(files)}")
for p in files:
    b = os.path.basename(p)
    m = PAT.match(b)
    if not m:
        skipped.append(b); continue
    r = score(lemma_sents(open(p, encoding="utf-8", errors="ignore").read()))
    r.update(ticker=m.group(1).upper(), year=int(m.group(2)), quarter=int(m.group(3)))
    rows.append(r)
if skipped:
    print("SKIPPED (filename not TICKER_YYYYQn):", skipped)
df = pd.DataFrame(rows)
print(f"transcripts scored: {len(df)}")

# ---- 2. SANITY CHECK: every firm-year needs all 4 quarters ------------------
# The official cc_expo_ew averages all 4 quarters. Comparing a 2-quarter average
# to a 4-quarter average is an error YOU introduced, and it will quietly lower
# your correlation. So drop incomplete firm-years instead of silently keeping them.
qc = df.groupby(["ticker", "year"]).size().reset_index(name="n_quarters")
bad = qc[qc.n_quarters < 4]
if len(bad):
    print("\nINCOMPLETE firm-years (dropped):")
    print(bad.to_string(index=False))
good = qc[qc.n_quarters == 4][["ticker", "year"]]
df = df.merge(good, on=["ticker", "year"], how="inner")
print(f"complete firm-years kept: {len(good)}")

# ---- 3. aggregate to firm-year, attach ISIN --------------------------------
fy = df.groupby(["ticker", "year"])[["cc_expo","op_expo","rg_expo","ph_expo"]].mean().reset_index()
fy = fy[fy["year"] <= 2024]      # instead of == 2024
TICKER_ISIN = json.load(open(MAP_JSON))
fy["isin"] = fy["ticker"].map(TICKER_ISIN)
missing = fy[fy["isin"].isna()]["ticker"].tolist()      # note: fy["isin"], NOT fy.isin
if missing:
    print("NO ISIN for:", missing, "-> add them to the map")

# ---- 4. merge with official + check the merge actually worked --------------
off = pd.read_csv(OFFICIAL_CSV, low_memory=False)
m = fy.merge(off[["isin","year","cc_expo_ew","op_expo_ew","rg_expo_ew","ph_expo_ew"]],
             on=["isin", "year"], how="left")
matched = m["cc_expo_ew"].notna().sum()
print(f"\nfirm-years: {len(m)} | matched to official: {matched}")
if matched < len(m):
    print("UNMATCHED (check the ISIN is correct and the year exists in the CSV):")
    print(m[m["cc_expo_ew"].isna()][["ticker","year","isin"]].to_string(index=False))

pd.set_option("display.float_format", lambda x: f"{x:.6f}")
m["pct_of_official"] = np.where(m["cc_expo_ew"] > 0,
                                100 * m["cc_expo"] / m["cc_expo_ew"], np.nan)
print("\nPer firm-year:")
print(m[["ticker","year","cc_expo","cc_expo_ew","pct_of_official"]].to_string(index=False))

# ---- 5. THE HEADLINE NUMBER -------------------------------------------------
v = m.dropna(subset=["cc_expo_ew"])
if len(v) >= 3:
    print("\n" + "=" * 52)
    print("CORRELATION WITH PUBLISHED SCORES")
    print("=" * 52)
    for a, b in [("cc_expo","cc_expo_ew"), ("op_expo","op_expo_ew"),
                 ("rg_expo","rg_expo_ew"), ("ph_expo","ph_expo_ew")]:
        if v[b].std() == 0 or v[a].std() == 0:
            print(f"  {a:8s}: n/a (no variation -- e.g. all zeros)")
        else:
            print(f"  {a:8s}: Pearson r = {v[a].corr(v[b]):.4f} | "
                  f"Spearman = {v[a].corr(v[b], method='spearman'):.4f}   (n={len(v)})")
    print("\n  Pearson  = do the VALUES track each other?")
    print("  Spearman = do the RANKINGS track each other? (robust to outliers)")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    m.to_csv(os.path.join(OUTPUT_DIR, "validation_results.csv"), index=False)
    print("\nsaved -> outputs/validation_results.csv")
else:
    print(f"\nonly {len(v)} matched firm-years -- collect more, need >=3 (aim 20+)")
