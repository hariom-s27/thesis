# =============================================================================
# PHASE 4 — two final validations
#
# (A) TF-IDF VALIDATION (Eq. 4)
#     The official CSV has no TF-IDF column, so we cannot compare values.
#     BUT the paper reports: corr(CCExposure, CCExposureTFIDF) = 99.7%.
#     So we test whether OUR two measures relate the same way. If we get ~0.99,
#     our Eq.(4) behaves as the authors' does. This is INDIRECT VALIDATION:
#     when you cannot check a value, check a published RELATIONSHIP.
#
# (B) RISK SPLIT-SAMPLE (Eq. 3)
#     The synonym list behind "risk, uncertainty, or their synonyms" is not
#     published. Picking the list that best matches the official numbers would
#     be OVERFITTING (fitting the answer). Instead:
#        - split firm-years into TRAIN and TEST halves
#        - choose the best list using TRAIN only
#        - report how it performs on TEST, which was never used to choose
#     If it still works on TEST, the list GENERALISES -> that is estimation,
#     not curve-fitting. This is the single most important idea in the script.
#
# Run AFTER you have collected transcripts. Uses the same folders as before.
# =============================================================================
import os, glob, re, pickle, json
from collections import Counter
import numpy as np, pandas as pd, spacy
from nltk.tokenize import sent_tokenize
from sklearn.feature_extraction.text import CountVectorizer

# ---- paths (EDIT) -----------------------------------------------------------
TRANSCRIPT_DIR = r"D:\sem_iitk\sem 8\thesis\api_transcripts"
DICT_DIR       = r"D:\sem_iitk\sem 8\thesis\old _work\code\jofi13219-sup-0002-replicationcode\Replication Files Sautner et al. (2023)\B. Figure 1 2, Table 2, and IA Table 6 7 8 9 11\bigrams"
OFFICIAL_CSV   = r"D:\sem_iitk\sem 8\thesis\old _work\csv\firmyear_score_2024Q4_Version_2025_Jul_03.csv"
OUTPUT_DIR     = r"D:\sem_iitk\sem 8\thesis\outputs"
MAP_JSON       = os.path.join(OUTPUT_DIR, "ticker_isin_map.json")

with open(os.path.join(DICT_DIR, "bigrams_07222021.pkl"), "rb") as f:
    CC = set(x.lower() for x in pickle.load(f))

# Loughran-McDonald uncertainty list (pip install pysentiment2)
import pysentiment2
_lm = pd.read_csv(os.path.join(os.path.dirname(pysentiment2.__file__), "static", "LM.csv"))
UNC = set(_lm.loc[_lm["Uncertainty"] > 0, "Word"].str.lower())

# ---- candidate synonym lists for Eq. (3) ------------------------------------
NARROW    = {"risk", "risky", "uncertainty", "uncertain"}
CURATED   = NARROW | {"volatile","volatility","threat","hazard","danger","doubt",
                      "doubtful","unpredictable","unclear","exposure","fluctuate",
                      "fluctuation","probable","possible","likelihood","chance",
                      "vary","variable"}
THESAURUS = NARROW | {"uncertainties","threat","threaten","hazard","hazardous",
                      "danger","dangerous","peril","perilous","jeopardy","jeopardize",
                      "vulnerability","vulnerable","exposure","expose","volatility",
                      "volatile","unpredictable","unforeseen","doubt","contingency",
                      "downside","adverse","adversely","disruption","disrupt",
                      "challenge","concern","pressure"}
LM_UNC    = NARROW | UNC
CANDIDATES = {"narrow": NARROW, "curated": CURATED,
              "thesaurus": THESAURUS, "lm_uncertainty": LM_UNC}

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

# =============================================================================
# PASS 1 — read every transcript once, cache what we need
# =============================================================================
PAT = re.compile(r"^([A-Z\.\-]+)_(\d{4})Q([1-4])", re.I)
docs, doc_freq = [], Counter()
files = sorted(glob.glob(os.path.join(TRANSCRIPT_DIR, "*.txt")))
print(f"reading {len(files)} transcripts (this takes a few minutes)...")

for p in files:
    m = PAT.match(os.path.basename(p))
    if not m: continue
    sents = lemma_sents(open(p, encoding="utf-8", errors="ignore").read())
    M = vec.fit_transform(sents)
    feats = np.array(vec.get_feature_names_out())
    counts = np.asarray(M.sum(axis=0)).ravel()
    B = int(counts.sum())
    cc_counts = {f: int(n) for f, n in zip(feats, counts) if f in CC and n > 0}

    # risk hits under EVERY candidate list, computed in this one pass
    risk_hits = {k: 0 for k in CANDIDATES}
    for i, s in enumerate(sents):
        row = M[i]
        hits = sum(int(c) for j, c in zip(row.indices, row.data) if feats[j] in CC)
        if hits == 0: continue
        w = set(s.split())
        for k, D in CANDIDATES.items():
            if w & D: risk_hits[k] += hits

    docs.append(dict(ticker=m.group(1).upper(), year=int(m.group(2)),
                     quarter=int(m.group(3)), B=B, cc=cc_counts, risk=risk_hits))
    for bg in cc_counts:
        doc_freq[bg] += 1

N = len(docs)
print(f"transcripts parsed: {N} | distinct climate bigrams seen: {len(doc_freq)}")

# =============================================================================
# PASS 2 — scores (TF-IDF needs doc_freq from pass 1, hence two passes)
# =============================================================================
rows = []
for d in docs:
    plain = sum(d["cc"].values())
    weighted = sum(n * np.log(N / doc_freq[bg])
                   for bg, n in d["cc"].items() if doc_freq[bg] > 0)
    r = dict(ticker=d["ticker"], year=d["year"], quarter=d["quarter"],
             cc_expo=plain / d["B"], cc_tfidf=weighted / d["B"])
    for k in CANDIDATES:
        r[f"risk_{k}"] = d["risk"][k] / d["B"]
    rows.append(r)
df = pd.DataFrame(rows)

# keep only firm-years with all 4 quarters (must match how the official is built)
qc = df.groupby(["ticker","year"]).size().reset_index(name="n")
good = qc[qc["n"] == 4][["ticker","year"]]
df = df.merge(good, on=["ticker","year"], how="inner")
value_cols = ["cc_expo","cc_tfidf"] + [f"risk_{k}" for k in CANDIDATES]
fy = df.groupby(["ticker","year"])[value_cols].mean().reset_index()
print(f"complete firm-years: {len(fy)}\n")

# =============================================================================
# (A) TF-IDF VALIDATION
# =============================================================================
print("=" * 62)
print("(A) TF-IDF VALIDATION  — paper reports corr(CCExposure, TFIDF) = 0.997")
print("=" * 62)
r_p = fy["cc_expo"].corr(fy["cc_tfidf"])
r_s = fy["cc_expo"].corr(fy["cc_tfidf"], method="spearman")
print(f"  our Pearson  = {r_p:.4f}")
print(f"  our Spearman = {r_s:.4f}   (n={len(fy)} firm-years)")
print(f"  ratio TFIDF/plain: mean {(fy['cc_tfidf']/fy['cc_expo'].replace(0,np.nan)).mean():.2f}x")
if r_p >= 0.97:
    print("  -> MATCHES the published relationship. Eq.(4) validated indirectly.")
else:
    print("  -> BELOW 0.97. Likely too few transcripts for stable IDF weights,")
    print("     or the dictionary terms are too rare in this sample. Report honestly.")

# =============================================================================
# (B) RISK SPLIT-SAMPLE
# =============================================================================
print("\n" + "=" * 62)
print("(B) RISK SPLIT-SAMPLE  — estimating the unpublished synonym list")
print("=" * 62)

TICKER_ISIN = json.load(open(MAP_JSON))
fy["isin"] = fy["ticker"].map(TICKER_ISIN)          # fy["isin"], NOT fy.isin
off = pd.read_csv(OFFICIAL_CSV, low_memory=False)
m = fy.merge(off[["isin","year","cc_risk_ew"]], on=["isin","year"], how="left")
m = m[m["cc_risk_ew"].notna()]
print(f"firm-years with an official risk value: {len(m)}")
print(f"  of which non-zero: {(m['cc_risk_ew'] > 0).sum()}")

if len(m) < 8:
    print("  too few to split. Collect more firm-years, then re-run part (B).")
else:
    # deterministic alternating split -> reproducible, and balances high/low firms
    m = m.sort_values(["ticker","year"]).reset_index(drop=True)
    train = m[m.index % 2 == 0]
    test  = m[m.index % 2 == 1]
    print(f"  TRAIN: {len(train)} firm-years | TEST: {len(test)} firm-years\n")

    def err(sub, col):
        """mean absolute error vs official -- lower is better"""
        return (sub[col] - sub["cc_risk_ew"]).abs().mean()

    print("  candidate performance on TRAIN (choosing happens here only):")
    scores = {}
    for k in CANDIDATES:
        e = err(train, f"risk_{k}")
        scores[k] = e
        print(f"    {k:16s} MAE = {e:.8f}   mean = {train[f'risk_{k}'].mean():.6f}")
    best = min(scores, key=scores.get)
    print(f"\n  BEST ON TRAIN: '{best}'")

    print("\n  now check it on TEST (never used for choosing):")
    e_test = err(test, f"risk_{best}")
    print(f"    {best:16s} MAE = {e_test:.8f}")
    for k in CANDIDATES:
        if k != best:
            print(f"    {k:16s} MAE = {err(test, f'risk_{k}'):.8f}")
    winner_on_test = min(CANDIDATES, key=lambda k: err(test, f"risk_{k}"))
    print(f"\n  best on TEST would have been: '{winner_on_test}'")
    if winner_on_test == best:
        print("  -> SAME list wins on both halves ==> it GENERALISES.")
        print("     You may report it as an estimated specification, with the caveat")
        print("     that the true list remains unpublished.")
    else:
        print("  -> DIFFERENT list wins on each half ==> it does NOT generalise.")
        print("     Do not claim to have recovered the list. Report the RANGE across")
        print("     specifications as a reproducibility limitation. This is a valid")
        print("     and honest result -- a failed estimate is still a finding.")

    if (test["cc_risk_ew"] > 0).sum() >= 3:
        c = test[f"risk_{best}"].corr(test["cc_risk_ew"])
        print(f"\n  correlation on TEST ({best} vs official) = {c:.4f}")

fy.to_csv(os.path.join(OUTPUT_DIR, "phase4_results.csv"), index=False)
print("\nsaved -> outputs/phase4_results.csv")
