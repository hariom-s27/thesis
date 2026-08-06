# =============================================================================
# AUDIT TOOL — check WHAT the algorithm is actually matching
#
# A score like 0.005592 tells you nothing about whether it is CORRECT.
# This script opens the black box and shows:
#   1. Which dictionary bigrams were matched, and how often   (= paper Table 2)
#   2. Dictionary COVERAGE: how much of the 9,641-word list was ever used
#   3. Sample sentences behind the matches -> read them yourself
#   4. Per-file health check: words, sentences, matches
#
# Point 3 is the important one. The paper validated its measure with 18 HUMAN
# CODERS reading sentences. You can do a small version of the same audit: read
# 20 matched sentences and ask "is this really about climate change?"
# =============================================================================
import os, glob, pickle, random
from collections import Counter
import numpy as np, pandas as pd, spacy
from nltk.tokenize import sent_tokenize
from sklearn.feature_extraction.text import CountVectorizer

# ---- paths (EDIT) -----------------------------------------------------------
TRANSCRIPT_DIR = r"D:\sem_iitk\sem 8\thesis\api_transcripts"
DICT_DIR       = r"D:\sem_iitk\sem 8\thesis\old _work\code\jofi13219-sup-0002-replicationcode\Replication Files Sautner et al. (2023)\B. Figure 1 2, Table 2, and IA Table 6 7 8 9 11\bigrams"
N_SAMPLE       = 25          # how many sentences to print for human reading

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
        if l: out.append(" ".join(l))
    return out

hits, per_file, samples = Counter(), [], []
files = sorted(glob.glob(os.path.join(TRANSCRIPT_DIR, "*.txt")))
print(f"auditing {len(files)} transcripts against a {len(CC):,}-bigram dictionary\n")

for p in files:
    name = os.path.basename(p)
    raw = open(p, encoding="utf-8", errors="ignore").read()
    sents = lemma_sents(raw)
    M = vec.fit_transform(sents)
    feats = np.array(vec.get_feature_names_out())
    counts = np.asarray(M.sum(axis=0)).ravel()

    n_hits, distinct = 0, 0
    for bg, n in zip(feats, counts):
        if bg in CC and n > 0:
            hits[bg] += int(n); n_hits += int(n); distinct += 1

    for i, s in enumerate(sents):
        got = [feats[j] for j in M[i].indices if feats[j] in CC]
        if got:
            samples.append((name, got[:3], s))

    per_file.append(dict(file=name, words=len(raw.split()), sentences=len(sents),
                         bigrams=int(counts.sum()), climate_hits=n_hits,
                         distinct=distinct))

# ---- 1. per-file health -----------------------------------------------------
pf = pd.DataFrame(per_file)
print("PER-FILE HEALTH CHECK")
print(pf.to_string(index=False))
print("\nLook for outliers: a file with far fewer words/sentences than the rest")
print("is probably truncated. A file with 0 climate_hits may be fine (low-climate")
print("firm) or may be broken -- open it and look.\n")

# ---- 2. coverage ------------------------------------------------------------
print("=" * 60)
print(f"DICTIONARY COVERAGE: {len(hits):,} of {len(CC):,} bigrams ever matched "
      f"({100*len(hits)/len(CC):.2f}%)")
print("=" * 60)
print("Low coverage is EXPECTED and not a bug: the dictionary was built from")
print("~800k transcripts across all industries. A handful of firms will only")
print("ever touch a small slice of it. Coverage should RISE as you add firms --")
print("track this number; it is a good progress indicator.\n")

# ---- 3. Table 2 style: most frequent matched bigrams ------------------------
print("TOP 30 MATCHED BIGRAMS  (this reproduces the paper's Table 2 format)")
top = pd.DataFrame(hits.most_common(30), columns=["bigram", "count"])
print(top.to_string(index=False))
top_all = pd.DataFrame(hits.most_common(), columns=["bigram", "count"])
top_all.to_csv("audit_matched_bigrams.csv", index=False)
print(f"\nfull list ({len(hits)} bigrams) -> audit_matched_bigrams.csv\n")

# ---- 4. HUMAN AUDIT: read these yourself ------------------------------------
print("=" * 60)
print(f"HUMAN AUDIT — read these {min(N_SAMPLE, len(samples))} sentences")
print("=" * 60)
print("For each one ask: is this REALLY about climate change? Count how many")
print("are correct. That percentage is your own mini version of the paper's")
print("18-coder human audit, and it belongs in your validation section.\n")
random.seed(42)                      # same sample every run = reproducible
for name, bgs, s in random.sample(samples, min(N_SAMPLE, len(samples))):
    print(f"[{name}]  matched: {bgs}")
    print(f"   {s[:220]}\n")

pd.DataFrame(samples, columns=["file","matched_bigrams","sentence"]) \
  .to_csv("audit_sentences.csv", index=False)
print(f"all {len(samples)} matched sentences -> audit_sentences.csv")

# =============================================================================
# KNOWN ISSUE TO REPORT IN YOUR THESIS (found by this tool):
# Because stop words are removed BEFORE bigrams are formed, some matches join
# words that were not adjacent in the original sentence. Real examples found:
#   "example carbon"  <- from "one example carbon fiber is another"
#   "gas equation", "reliable cost", "hydrogen carbon"
# These are artefacts of the method, NOT bugs in your code -- the authors' own
# pipeline does exactly the same thing (we copied their vectorizer settings).
# Mentioning this shows you inspected the measure rather than trusting it.
# =============================================================================
