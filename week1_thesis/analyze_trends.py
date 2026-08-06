# =============================================================================
# TREND ANALYSIS — CCExposure and sentiment/risk over time, across all firms
#
# Combines the Eq.(1) exposure measures (score_and_correlate.py) and the
# Eq.(2)/Eq.(3) sentiment/risk measures (phase2_api.py) into a single pass
# over every transcript on disk, aggregated to firm-year, so trends over
# years can be compared across firms in one table/chart.
# =============================================================================
import os, glob, re, pickle, json
import numpy as np, pandas as pd, spacy
from nltk.tokenize import sent_tokenize
from sklearn.feature_extraction.text import CountVectorizer

# ---- paths --------------------------------------------------------------
DICT_DIR       = r"D:\sem_iitk\sem 8\thesis\old _work\code\jofi13219-sup-0002-replicationcode\Replication Files Sautner et al. (2023)\B. Figure 1 2, Table 2, and IA Table 6 7 8 9 11\bigrams"
TRANSCRIPT_DIR = r"D:\sem_iitk\sem 8\thesis\api_transcripts"
OUT_CSV        = r"D:\sem_iitk\sem 8\thesis\firm_year_trends.csv"

# ---- dictionaries ---------------------------------------------------------
def _d(n):
    with open(os.path.join(DICT_DIR, n), "rb") as f:
        return set(x.lower() for x in pickle.load(f))
CC = _d("bigrams_07222021.pkl")
OP = _d("opportunity_bigrams_4.pkl")
RG = _d("regulatory_bigrams_4.pkl")
PH = _d("physical_bigrams_4.pkl")

import pysentiment2  # noqa
_lm = pd.read_csv(os.path.join(os.path.dirname(pysentiment2.__file__), "static", "LM.csv"))
POS = set(_lm.loc[_lm["Positive"] > 0, "Word"].str.lower())
NEG = set(_lm.loc[_lm["Negative"] > 0, "Word"].str.lower())
RISKW = {
    "risk", "uncertainty", "threat", "hazard", "danger", "peril", "jeopardy",
    "vulnerable", "exposure", "volatility", "unpredictable", "unforeseen",
    "doubt", "contingency", "downside", "adverse", "disruption", "challenge",
    "concern", "pressure",
}   # RISK_THESAURUS, same as phase2_api.py

nlp = spacy.load("en_core_web_sm", disable=["ner", "parser"])
nlp.add_pipe("sentencizer")
vec = CountVectorizer(analyzer="word", strip_accents="unicode",
                      ngram_range=(2, 2), lowercase=True, stop_words="english")

def lemma_sents(text):
    out = []
    for s in sent_tokenize(text):
        d = nlp(s)
        l = [t.lemma_.lower() for t in d if not t.is_space and not t.is_punct]
        if l:
            out.append(" ".join(l))
    return out

def measures(sents):
    M = vec.fit_transform(sents)
    feats = np.array(vec.get_feature_names_out())
    counts = np.asarray(M.sum(axis=0)).ravel()
    B = int(counts.sum())
    freq = dict(zip(feats, counts))
    all_feats = set(feats)
    cc_total = sum(freq[b] for b in (all_feats & CC))
    op_total = sum(freq[b] for b in (all_feats & OP))
    rg_total = sum(freq[b] for b in (all_feats & RG))
    ph_total = sum(freq[b] for b in (all_feats & PH))

    pos = neg = risk = 0
    for i, s in enumerate(sents):
        row = M[i]
        hits = sum(int(c) for j, c in zip(row.indices, row.data) if feats[j] in CC)
        if hits == 0:
            continue
        w = set(s.split())
        if w & POS:   pos  += hits
        if w & NEG:   neg  += hits
        if w & RISKW: risk += hits

    return dict(B=B,
                cc_expo=cc_total / B, op_expo=op_total / B,
                rg_expo=rg_total / B, ph_expo=ph_total / B,
                cc_pos=pos / B, cc_neg=-neg / B,
                cc_sent=(pos - neg) / B, cc_risk=risk / B)

# ---- score every transcript -----------------------------------------------
PAT = re.compile(r"^([A-Z\.\-]+)_(\d{4})Q([1-4])", re.I)
rows, skipped = [], []
files = sorted(glob.glob(os.path.join(TRANSCRIPT_DIR, "*.txt")))
print(f"files found: {len(files)}")
for p in files:
    b = os.path.basename(p)
    m = PAT.match(b)
    if not m:
        skipped.append(b)
        continue
    text = open(p, encoding="utf-8", errors="ignore").read()
    r = measures(lemma_sents(text))
    r.update(ticker=m.group(1).upper(), year=int(m.group(2)), quarter=int(m.group(3)))
    rows.append(r)
if skipped:
    print("SKIPPED (filename not TICKER_YYYYQn):", skipped)
df = pd.DataFrame(rows)
print(f"transcripts scored: {len(df)}")

# ---- aggregate to firm-year -------------------------------------------------
MEASURE_COLS = ["cc_expo", "op_expo", "rg_expo", "ph_expo",
                "cc_pos", "cc_neg", "cc_sent", "cc_risk"]
fy = (df.groupby(["ticker", "year"])[MEASURE_COLS]
        .mean().reset_index())
n_q = df.groupby(["ticker", "year"]).size().reset_index(name="n_quarters")
fy = fy.merge(n_q, on=["ticker", "year"])
fy = fy.sort_values(["ticker", "year"])

fy.to_csv(OUT_CSV, index=False)
print(f"\nsaved -> {OUT_CSV}")

pd.set_option("display.float_format", lambda x: f"{x:.6f}")
print("\nFirm-year trends (cc_expo and cc_sent shown; full set in the CSV):")
print(fy[["ticker", "year", "n_quarters", "cc_expo", "cc_sent", "cc_risk"]].to_string(index=False))
