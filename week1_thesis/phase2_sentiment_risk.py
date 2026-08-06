# =============================================================================
# PHASE 2 — Sentiment (Eq. 2) and Risk (Eq. 3) measures
# Sautner, van Lent, Vilkov & Zhang (2023), Journal of Finance
#
# Eq.(2) CCSentimentPos/Neg = (1/B) * sum over climate bigrams b, counted ONLY
#        if the SENTENCE containing b also holds a Loughran-McDonald pos/neg word.
# Eq.(3) CCRisk = (1/B) * sum over climate bigrams b, counted ONLY if the
#        SENTENCE containing b also holds "risk"/"uncertainty" or a synonym.
#
# KEY POINT: the condition is checked SENTENCE BY SENTENCE. B (the denominator)
# is still the total bigram count of the WHOLE transcript, same as Eq. (1).
#
# Setup:
#   pip install pdfplumber spacy nltk scikit-learn pandas pysentiment2
#   python -m spacy download en_core_web_sm
# =============================================================================
import os, glob, re, pickle, io, zipfile
import numpy as np, pandas as pd, spacy
from nltk.tokenize import sent_tokenize
from sklearn.feature_extraction.text import CountVectorizer

# ---- paths (EDIT THESE — same as exact_reproduction.py) ---------------------
DICT_DIR       = r"D:\sem_iitk\sem 8\thesis\old _work\code\jofi13219-sup-0002-replicationcode\Replication Files Sautner et al. (2023)\B. Figure 1 2, Table 2, and IA Table 6 7 8 9 11\bigrams"                 # folder holding the 4 .pkl dictionaries
TRANSCRIPT_DIR = r"D:\sem_iitk\sem 8\thesis\old _work\transcript"     # folder of REAL transcript PDFs
OFFICIAL_CSV   = r"D:\sem_iitk\sem 8\thesis\old _work\csv\firmyear_score_2024Q4_Version_2025_Jul_03.csv"
FIRM_ISIN      = "US30231G1022"      # ExxonMobil (for validation)

# ---- 1. climate bigram dictionary -------------------------------------------
with open(os.path.join(DICT_DIR, "bigrams_07222021.pkl"), "rb") as f:
    CC = set(x.lower() for x in pickle.load(f))

# ---- 2. Loughran-McDonald tone words ----------------------------------------
# Easiest route: `pip install pysentiment2` bundles the LM master dictionary.
import pysentiment2  # noqa
_lm_path = os.path.join(os.path.dirname(pysentiment2.__file__), "static", "LM.csv")
_lm = pd.read_csv(_lm_path)
POS = set(_lm.loc[_lm["Positive"] > 0, "Word"].str.lower())      # 354 words
NEG = set(_lm.loc[_lm["Negative"] > 0, "Word"].str.lower())      # 2,355 words
UNC = set(_lm.loc[_lm["Uncertainty"] > 0, "Word"].str.lower())   # 297 words

# ---- 3. risk vocabulary -----------------------------------------------------
# The paper says: "risk", "uncertainty", or their SYNONYMS -- but never lists
# them. This choice materially changes the result (see notes at bottom), so we
# expose it as an explicit, reportable parameter instead of hiding it.
RISK_NARROW  = {"risk", "risky", "uncertainty", "uncertain"}
RISK_CURATED = RISK_NARROW | {
    "volatile", "volatility", "threat", "hazard", "danger", "doubt", "doubtful",
    "unpredictable", "unclear", "exposure", "fluctuate", "fluctuation",
    "probable", "possible", "likelihood", "chance", "vary", "variable",
}
RISK_LM_UNC  = RISK_NARROW | UNC          # broadest: whole LM uncertainty list

RISKW = RISK_CURATED                      # <-- change this to test sensitivity

# ---- 4. preprocessing (identical to Eq. 1 pipeline) -------------------------
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

# ---- 5. the measures --------------------------------------------------------
def measures(sents):
    M = vec.fit_transform(sents)
    feats = np.array(vec.get_feature_names_out())
    B = int(np.asarray(M.sum(axis=0)).ravel().sum())   # denominator = whole transcript
    cc = pos = neg = risk = 0
    for i, s in enumerate(sents):
        row = M[i]
        hits = sum(int(c) for j, c in zip(row.indices, row.data) if feats[j] in CC)
        if hits == 0:
            continue
        cc += hits
        w = set(s.split())                  # words of THIS sentence
        if w & POS:   pos  += hits          # Eq. 2 positive
        if w & NEG:   neg  += hits          # Eq. 2 negative
        if w & RISKW: risk += hits          # Eq. 3
    return dict(B=B,
                cc_expo=cc / B,
                cc_pos=pos / B,
                cc_neg=-neg / B,            # stored NEGATIVE, matching the authors
                cc_sent=(pos - neg) / B,    # net = pos + (negative-signed neg)
                cc_risk=risk / B)

def read_pdf(path):
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        return "\n".join(p.extract_text() or "" for p in pdf.pages)

# ---- 6. run over transcripts ------------------------------------------------
rows = []
for p in sorted(glob.glob(os.path.join(TRANSCRIPT_DIR, "*.pdf"))):
    b = os.path.basename(p)
    m = re.search(r"([1-4])Q(\d{2,4})|Q([1-4])(\d{2,4})", b)
    if m:
        qn = m.group(1) or m.group(3)
        yr = m.group(2) or m.group(4)
        year = int(yr) + 2000 if len(yr) == 2 else int(yr)
    else:
        year, qn = None, None
    r = measures(lemma_sents(read_pdf(p)))
    r.update(year=year, quarter=qn, file=b)
    rows.append(r)

df = pd.DataFrame(rows).sort_values(["year", "quarter"])
pd.set_option("display.float_format", lambda x: f"{x:.6f}")
print(df[["year","quarter","B","cc_expo","cc_pos","cc_neg","cc_sent","cc_risk"]].to_string(index=False))

fy = df.groupby("year")[["cc_expo","cc_pos","cc_neg","cc_sent","cc_risk"]].mean().reset_index()
print("\nFirm-year:")
print(fy.to_string(index=False))

# ---- 7. validate against published scores -----------------------------------
if os.path.exists(OFFICIAL_CSV):
    off = pd.read_csv(OFFICIAL_CSV, low_memory=False)
    print("rows matching ISIN:", (off["isin"] == FIRM_ISIN).sum())   # sanity check!
    off = off[off["isin"] == FIRM_ISIN][
        ["year","cc_expo_ew","cc_pos_ew","cc_neg_ew","cc_sent_ew","cc_risk_ew"]]
    chk = fy.merge(off, on="year", how="left")
    print("\nValidation vs published:")
    print(chk.to_string(index=False))

# =============================================================================
# RESULTS on 8 ExxonMobil excerpt transcripts (2024 firm-year):
#
#   measure    ours       official    match
#   cc_expo    0.004505   0.005747     78%
#   cc_pos     0.001659   0.002484     67%
#   cc_neg    -0.000891  -0.001348     66%
#   cc_sent    0.000767   0.001136     68%
#   cc_risk    0.000064   0.000399     16%   <-- sensitive, see below
#
# Note 1 (sign): the authors store cc_neg as a NEGATIVE number, and
#   cc_sent_ew = cc_pos_ew + cc_neg_ew  (0.002484 - 0.001348 = 0.001136). Verified.
#
# Note 2 (risk sensitivity — REPORT THIS IN THE THESIS): Eq. (3) depends on an
#   unpublished synonym list. On this sample:
#       RISK_NARROW  -> 0.000000
#       RISK_CURATED -> 0.000064
#       RISK_LM_UNC  -> 0.000728
#       official     =  0.000399
#   The official value sits between the curated and broad lists. We deliberately
#   do NOT tune the list to hit 0.000399: fitting a free parameter to a single
#   observation is overfitting, not replication. Instead we report the range.
#
# Note 3: sentiment and risk are computed on far fewer sentences than exposure,
#   so they are noisier on a small sample. With more firms these stabilise.
# =============================================================================
