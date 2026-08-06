# =============================================================================
# PHASE 3 — TF-IDF weighted exposure (Sautner et al. 2023, Equation 4)
#
#   CCExposureTFIDF = (1/B) * SUM over climate bigrams b of
#                             [ count(b) * log( N / f_b ) ]
#
#   N   = total number of transcripts
#   f_b = number of transcripts in which bigram b appears (presence, not count)
#
# IDEA: a bigram that appears in EVERY transcript tells us nothing special, so
# log(N/N) = 0 kills it. A rare bigram is informative, so it gets a big weight.
#
# WHY TWO PASSES: f_b depends on ALL transcripts, so you cannot score any single
# transcript until you have seen every transcript. Pass 1 measures rarity,
# Pass 2 scores. This is why we cache results instead of re-reading PDFs.
#
# NOTE: there is NO TF-IDF column in the published CSV, so this measure cannot
# be validated against ground truth. Report it as unvalidated in the thesis.
# =============================================================================
import os, glob, re, pickle
from collections import Counter
import numpy as np, pandas as pd, spacy
from nltk.tokenize import sent_tokenize
from sklearn.feature_extraction.text import CountVectorizer

# ---- paths (same as your other scripts) -------------------------------------
DICT_DIR       = r"D:\sem_iitk\sem 8\thesis\old _work\code\jofi13219-sup-0002-replicationcode\Replication Files Sautner et al. (2023)\B. Figure 1 2, Table 2, and IA Table 6 7 8 9 11\bigrams"                 # folder holding the 4 .pkl dictionaries
TRANSCRIPT_DIR = r"D:\sem_iitk\sem 8\thesis\old _work\transcript"  

with open(os.path.join(DICT_DIR, "bigrams_07222021.pkl"), "rb") as f:
    CC = set(x.lower() for x in pickle.load(f))

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

def read_pdf(path):
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        return "\n".join(p.extract_text() or "" for p in pdf.pages)

# ---- DIAGNOSTIC: always look at what you actually loaded --------------------
files = sorted(glob.glob(os.path.join(TRANSCRIPT_DIR, "*.pdf")))
print("FILES FOUND:", len(files))
for f in files:
    print("   ", os.path.basename(f))
print()

# =============================================================================
# PASS 1 — measure rarity (f_b) and cache each transcript's counts
# =============================================================================
docs, doc_freq = [], Counter()
for p in files:
    b = os.path.basename(p)
    m = re.search(r"([1-4])Q(\d{2,4})|Q([1-4])(\d{2,4})", b)
    if m:
        qn = m.group(1) or m.group(3)
        yr = m.group(2) or m.group(4)
        year = int(yr) + 2000 if len(yr) == 2 else int(yr)
    else:
        year, qn = None, None

    sents = lemma_sents(read_pdf(p))
    M = vec.fit_transform(sents)
    feats = np.array(vec.get_feature_names_out())
    counts = np.asarray(M.sum(axis=0)).ravel()
    B = int(counts.sum())

    # counts of climate bigrams in THIS transcript
    cc_counts = {f: int(c) for f, c in zip(feats, counts) if f in CC and c > 0}

    docs.append(dict(year=year, quarter=qn, B=B, cc_counts=cc_counts, file=b))
    # KEY: +1 per transcript, no matter how many times it occurs inside it
    for bg in cc_counts:
        doc_freq[bg] += 1

N = len(docs)
print("N transcripts:", N, "| distinct climate bigrams seen:", len(doc_freq))
print("  in ALL transcripts  ->", sum(1 for v in doc_freq.values() if v == N), "(weight = 0)")
print("  in ONLY 1 transcript->", sum(1 for v in doc_freq.values() if v == 1),
      f"(weight = {np.log(N/1):.2f})")

# =============================================================================
# PASS 2 — score each transcript using the weights from Pass 1
# =============================================================================
rows = []
for d in docs:
    plain = sum(d["cc_counts"].values())          # Eq. 1 numerator
    weighted = 0.0
    for bg, c in d["cc_counts"].items():
        f = doc_freq[bg]
        if f > 0:                                  # f==0 impossible here, but safe
            weighted += c * np.log(N / f)          # Eq. 4 numerator
    rows.append(dict(year=d["year"], quarter=d["quarter"], B=d["B"],
                     cc_expo=plain / d["B"],
                     cc_tfidf=weighted / d["B"]))

df = pd.DataFrame(rows).sort_values(["year", "quarter"])
pd.set_option("display.float_format", lambda x: f"{x:.6f}")
print("\nPer quarter:")
print(df.to_string(index=False))
print("\nFirm-year:")
print(df.groupby("year")[["cc_expo", "cc_tfidf"]].mean().to_string())

# =============================================================================
# RESULT on 8 ExxonMobil excerpts:
#   2024:  cc_expo 0.004505   cc_tfidf 0.007521
#   2025:  cc_expo 0.002883   cc_tfidf 0.005229
#
# Diagnostic: 84 distinct climate bigrams; 0 appeared in all 8 transcripts;
# 74 of 84 appeared in only ONE. So almost every bigram got the maximum weight
# log(8/1)=2.08, which INFLATES TF-IDF above plain exposure.
#
# INTERPRETATION: with only 8 documents, "rare" is meaningless -- nearly
# everything looks rare. TF-IDF only becomes informative with many transcripts
# across many firms, where common boilerplate genuinely appears everywhere.
# On this sample the measure is computed correctly but is not meaningful.
# =============================================================================
