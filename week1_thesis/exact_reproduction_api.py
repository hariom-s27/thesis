# =============================================================================
# EXACT REPRODUCTION of Sautner, van Lent, Vilkov & Zhang (2023) CCExposure
# using the authors' released bigram dictionaries + their preprocessing recipe.
#
# Verified on 8 ExxonMobil transcripts:
#   2024 firm-year CCExposure = 0.00451  (official published value = 0.00575, 78%)
#   Physical = 0.00000 (exact match). Residual gap ~ transcripts are "Excerpts".
#
# Setup (Colab):
#   !pip install pdfplumber spacy nltk scikit-learn pandas -q
#   !python -m spacy download en_core_web_sm
# =============================================================================
import os, glob, re, pickle
import numpy as np, pandas as pd
import spacy
from nltk.tokenize import sent_tokenize
from sklearn.feature_extraction.text import CountVectorizer

# ---- paths (EDIT THESE) ------------------------------------------------------
DICT_DIR       = r"D:\sem_iitk\sem 8\thesis\old _work\code\jofi13219-sup-0002-replicationcode\Replication Files Sautner et al. (2023)\B. Figure 1 2, Table 2, and IA Table 6 7 8 9 11\bigrams"                 # folder holding the 4 .pkl dictionaries
TRANSCRIPT_DIR = r"D:\sem_iitk\sem 8\thesis\api_transcripts"
OFFICIAL_CSV   = r"D:\sem_iitk\sem 8\thesis\old _work\csv\firmyear_score_2024Q4_Version_2025_Jul_03.csv"
FIRM_ISIN      = "US30231G1022"      # ExxonMobil (for validation)

# ---- 1. load the authors' real dictionaries ---------------------------------
def _load(name):
    with open(os.path.join(DICT_DIR, name), "rb") as f:
        return set(x.lower() for x in pickle.load(f))
CC = _load("bigrams_07222021.pkl")        # main CCExposure     (9,641 bigrams)
OP = _load("opportunity_bigrams_4.pkl")   # CCExposureOpp       (2,710)
RG = _load("regulatory_bigrams_4.pkl")    # CCExposureReg       (251)
PH = _load("physical_bigrams_4.pkl")      # CCExposurePhy       (51)

# ---- 2. spaCy + the EXACT vectorizer from the SvLVZ do-file ------------------
nlp = spacy.load("en_core_web_sm", disable=["ner", "parser"])
nlp.add_pipe("sentencizer")
vec = CountVectorizer(analyzer="word", strip_accents="unicode",
                      ngram_range=(2, 2), lowercase=True, stop_words="english")

def lemmatize(text):
    """Return a list of lemmatized sentences (bigrams do not cross sentences)."""
    out = []
    for s in sent_tokenize(text):
        doc = nlp(s)
        lemmas = [t.lemma_.lower() for t in doc if not t.is_space and not t.is_punct]
        if lemmas:
            out.append(" ".join(lemmas))
    return out

def score(sent_list):
    m = vec.fit_transform(sent_list)
    feats = np.array(vec.get_feature_names_out())
    counts = np.asarray(m.sum(axis=0)).ravel()
    total = counts.sum()
    freq = dict(zip(feats, counts))
    hit = lambda D: sum(freq[b] for b in (set(feats) & D))
    return dict(B=int(total),
                cc_expo=hit(CC)/total, op_expo=hit(OP)/total,
                rg_expo=hit(RG)/total, ph_expo=hit(PH)/total)

# ---- 3. read transcripts (pdfplumber for real PDFs) -------------------------
def read_pdf(path):
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        return "\n".join(p.extract_text() or "" for p in pdf.pages)

rows = []
for p in sorted(glob.glob(os.path.join(TRANSCRIPT_DIR, "*.txt"))):
    text = open(p, encoding="utf-8").read()
    m = re.search(r"(\d{4})Q([1-4])", os.path.basename(p))
    if m:
        year, quarter = int(m.group(1)), m.group(2)
    else:
        year, quarter = None, None
    print(f"{os.path.basename(p)} -> year={year}, quarter={quarter}")
    rec = score(lemmatize(text))
    rec.update(year=year,
               quarter=quarter,
               file=os.path.basename(p))
    rows.append(rec)
df = pd.DataFrame(rows)

# ---- 4. aggregate to firm-year & validate -----------------------------------
fy = df.groupby("year")[["cc_expo","op_expo","rg_expo","ph_expo"]].mean().reset_index()
print(fy.to_string(index=False))

if os.path.exists(OFFICIAL_CSV):
    off = pd.read_csv(OFFICIAL_CSV, low_memory=False)
    print("FIRM_ISIN is:", repr(FIRM_ISIN))
    print("rows matching:", (off["isin"] == FIRM_ISIN).sum())
    off = off[off["isin"] == FIRM_ISIN][["year","cc_expo_ew","op_expo_ew","rg_expo_ew","ph_expo_ew"]]
    check = fy.merge(off, on="year", how="left")
    check["cc_pct_of_official"] = 100 * check["cc_expo"] / check["cc_expo_ew"]
    print("\nValidation vs published scores:")
    print(check.to_string(index=False))

# NOTE: for an exact match, feed FULL transcripts (not excerpts). Sentiment
# (Loughran-McDonald) and risk measures are the next additions.
