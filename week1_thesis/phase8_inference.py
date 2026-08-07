# =============================================================================
# PHASE 8 — STATISTICAL INFERENCE
#
# Everything so far is a point estimate with no uncertainty attached. This adds:
#
#   8.1  CLUSTER BOOTSTRAP CIs      - "r = 0.986, 95% CI [x, y]" instead of "r = 0.986"
#   8.2  PERMUTATION TEST           - turns the 58% scramble result into a formal test
#   8.3  SPLIT-STABILITY            - is 'curated' really the best risk list, or luck?
#
# WHY CLUSTERING MATTERS (8.1): firm-years from the same firm are NOT independent
# observations -- XOM 2022, 2023, 2024 share the same company, industry and
# vocabulary. Resampling ROWS pretends you have 51 independent data points when
# you really have ~14. That makes your confidence interval too narrow and your
# result look more certain than it is. We resample FIRMS instead.
#
# Setup: pip install spacy nltk scikit-learn pandas
# =============================================================================
import os, glob, re, pickle, random
import numpy as np, pandas as pd

# ---- paths (EDIT) -----------------------------------------------------------
OUTPUT_DIR     = r"D:\sem_iitk\sem 8\thesis\outputs"
VALIDATION_CSV = os.path.join(OUTPUT_DIR, "validation_results.csv")   # from score_and_correlate.py
PHASE4_CSV     = os.path.join(OUTPUT_DIR, "phase4_results.csv")       # from phase4_tfidf_and_risk.py
OFFICIAL_CSV   = r"D:\sem_iitk\sem 8\thesis\old _work\csv\firmyear_score_2024Q4_Version_2025_Jul_03.csv"
TRANSCRIPT_DIR = r"D:\sem_iitk\sem 8\thesis\api_transcripts"
DICT_DIR       = r"D:\sem_iitk\sem 8\thesis\old _work\code\jofi13219-sup-0002-replicationcode\Replication Files Sautner et al. (2023)\B. Figure 1 2, Table 2, and IA Table 6 7 8 9 11\bigrams"

N_BOOT   = 5000     # bootstrap replications
N_PERM   = 200      # scrambles per transcript (200 x 40 docs = 8000 fits, ~15 min)
N_DOCS   = 40       # transcripts used for the permutation test
N_SPLITS = 1000     # random train/test splits for 8.3
SEED     = 42

# =============================================================================
# 8.1 — CLUSTER BOOTSTRAP CONFIDENCE INTERVALS
# =============================================================================
print("=" * 72)
print("8.1 — CLUSTER BOOTSTRAP CONFIDENCE INTERVALS (resampling FIRMS, not rows)")
print("=" * 72)

v = pd.read_csv(VALIDATION_CSV)
v = v[v["cc_expo_ew"].notna()].copy()
print(f"firm-years: {len(v)} | distinct firms: {v['ticker'].nunique()}\n")

def cluster_bootstrap(d, a, b, n_boot=N_BOOT, seed=SEED, method="pearson"):
    rng = np.random.default_rng(seed)
    firms = d["ticker"].unique()
    groups = {f: d[d["ticker"] == f] for f in firms}
    out = []
    for _ in range(n_boot):
        pick = rng.choice(firms, size=len(firms), replace=True)
        s = pd.concat([groups[f] for f in pick], ignore_index=True)
        if s[a].std() > 0 and s[b].std() > 0:
            out.append(s[a].corr(s[b], method=method))
    out = np.array(out)
    return np.percentile(out, [2.5, 97.5]), out

PAIRS = [("cc_expo","cc_expo_ew"), ("op_expo","op_expo_ew"),
         ("rg_expo","rg_expo_ew"), ("ph_expo","ph_expo_ew")]
rows = []
for a, b in PAIRS:
    if a not in v.columns or b not in v.columns: continue
    sub = v[(v[a].notna()) & (v[b].notna())]
    if sub[a].std() == 0 or sub[b].std() == 0:
        print(f"  {a:9s}: no variation -- cannot compute"); continue
    for meth in ("pearson", "spearman"):
        pt = sub[a].corr(sub[b], method=meth)
        ci, _ = cluster_bootstrap(sub, a, b, method=meth)
        rows.append(dict(measure=a, method=meth, r=round(pt,4),
                         lo=round(ci[0],4), hi=round(ci[1],4), n=len(sub)))
res = pd.DataFrame(rows)
for _, r in res.iterrows():
    print(f"  {r['measure']:9s} {r['method']:9s} r = {r['r']:.4f}   "
          f"95% CI [{r['lo']:.4f}, {r['hi']:.4f}]   n = {r['n']}")

# show how much the naive (wrong) bootstrap would have understated uncertainty
sub = v[(v["cc_expo"].notna()) & (v["cc_expo_ew"].notna())]
rng = np.random.default_rng(SEED); naive = []
for _ in range(N_BOOT):
    s = sub.sample(len(sub), replace=True)
    if s["cc_expo"].std() > 0: naive.append(s["cc_expo"].corr(s["cc_expo_ew"]))
nl, nh = np.percentile(naive, [2.5, 97.5])
cl = res[(res.measure=="cc_expo") & (res.method=="pearson")].iloc[0]
print(f"""
  Naive row bootstrap would give [{nl:.4f}, {nh:.4f}] -- width {nh-nl:.4f}
  Cluster bootstrap gives        [{cl['lo']:.4f}, {cl['hi']:.4f}] -- width {cl['hi']-cl['lo']:.4f}
  The clustered interval is the honest one. Report it.
""")
res.to_csv(os.path.join(OUTPUT_DIR, "phase8_bootstrap_ci.csv"), index=False)

# =============================================================================
# 8.2 — PERMUTATION TEST FOR THE SCRAMBLE FINDING
# =============================================================================
print("=" * 72)
print("8.2 — PERMUTATION TEST: is the real score above the random-order null?")
print("=" * 72)
print(f"  scrambling {N_DOCS} transcripts x {N_PERM} times -- this takes a while...\n")

import spacy
from nltk.tokenize import sent_tokenize
from sklearn.feature_extraction.text import CountVectorizer

with open(os.path.join(DICT_DIR, "bigrams_07222021.pkl"), "rb") as f:
    CC = set(x.lower() for x in pickle.load(f))
nlp = spacy.load("en_core_web_sm", disable=["ner", "parser"]); nlp.add_pipe("sentencizer")
vec = CountVectorizer(analyzer="word", strip_accents="unicode",
                      ngram_range=(2,2), lowercase=True, stop_words="english")

def lemma_sents(text):
    out = []
    for s in sent_tokenize(text):
        d = nlp(s)
        l = [t.lemma_.lower() for t in d if not t.is_space and not t.is_punct]
        if l: out.append(" ".join(l))
    return out

def expo(sents):
    if not sents: return 0.0
    M = vec.fit_transform(sents)
    f = np.array(vec.get_feature_names_out())
    c = np.asarray(M.sum(axis=0)).ravel(); B = int(c.sum())
    if B == 0: return 0.0
    fr = dict(zip(f, c))
    return sum(int(fr[b]) for b in (set(f) & CC)) / B

PAT = re.compile(r"^([A-Z\.\-]+)_(\d{4})Q([1-4])", re.I)
files = [p for p in sorted(glob.glob(os.path.join(TRANSCRIPT_DIR, "*.txt")))
         if PAT.match(os.path.basename(p))]
random.seed(SEED)
rng = np.random.default_rng(SEED)
rows = []
for p in random.sample(files, min(N_DOCS, len(files))):
    sents = lemma_sents(open(p, encoding="utf-8", errors="ignore").read())
    real = expo(sents)
    if real == 0: continue
    words = " ".join(sents).split()
    null = []
    for _ in range(N_PERM):
        w = words[:]; rng.shuffle(w)
        null.append(expo([" ".join(w[i:i+20]) for i in range(0, len(w), 20)]))
    null = np.array(null)
    z = (real - null.mean()) / null.std() if null.std() > 0 else np.nan
    p_emp = (1 + (null >= real).sum()) / (1 + len(null))    # one-sided empirical p
    rows.append(dict(doc=os.path.basename(p).replace(".txt",""), real=real,
                     null_mean=null.mean(), null_sd=null.std(), z=z, p=p_emp))
perm = pd.DataFrame(rows)
print(perm.round(6).to_string(index=False))
sig = (perm["p"] < 0.05).mean() * 100
print(f"""
  transcripts tested: {len(perm)}
  mean z-score: {perm['z'].mean():.2f}
  real score exceeds the random-order null at p<0.05 in {sig:.0f}% of transcripts
  mean null / real ratio: {(perm['null_mean']/perm['real']).mean():.3f}

  HOW TO READ: the null is what the measure returns when word order is destroyed
  but vocabulary is identical. A high null/real ratio means most of the measured
  exposure is explained by WHICH WORDS appear, not by which PHRASES. A low
  proportion of significant transcripts would mean the measure barely
  distinguishes real text from word soup -- an important limitation either way.
""")
perm.to_csv(os.path.join(OUTPUT_DIR, "phase8_permutation.csv"), index=False)

# =============================================================================
# 8.3 — SPLIT-STABILITY OF THE RISK SYNONYM LIST
# =============================================================================
print("=" * 72)
print("8.3 — SPLIT-STABILITY: does 'curated' win because it is best, or by luck?")
print("=" * 72)
if not os.path.exists(PHASE4_CSV):
    print("  phase4_results.csv not found -- run phase4_tfidf_and_risk.py first")
else:
    p4 = pd.read_csv(PHASE4_CSV)
    off = pd.read_csv(OFFICIAL_CSV, low_memory=False)
    m = p4.merge(off[["isin","year","cc_risk_ew"]], on=["isin","year"], how="inner")
    m = m[m["cc_risk_ew"].notna()].reset_index(drop=True)
    cands = [c for c in m.columns if c.startswith("risk_")]
    print(f"  firm-years: {len(m)} | candidate lists: {[c.replace('risk_','') for c in cands]}\n")

    rng = np.random.default_rng(SEED)
    firms = m["ticker"].unique()
    wins_train, wins_test, agree = {c: 0 for c in cands}, {c: 0 for c in cands}, 0
    for _ in range(N_SPLITS):
        # split by FIRM so no firm appears in both halves (avoids leakage)
        perm_f = rng.permutation(firms)
        half = len(perm_f) // 2
        tr = m[m["ticker"].isin(perm_f[:half])]
        te = m[m["ticker"].isin(perm_f[half:])]
        if len(tr) < 3 or len(te) < 3: continue
        mae = lambda d, c: (d[c] - d["cc_risk_ew"]).abs().mean()
        bt = min(cands, key=lambda c: mae(tr, c))
        bs = min(cands, key=lambda c: mae(te, c))
        wins_train[bt] += 1; wins_test[bs] += 1
        if bt == bs: agree += 1
    tot = sum(wins_train.values())
    print("  how often each list wins (out of %d random firm-level splits):" % tot)
    for c in cands:
        print(f"    {c.replace('risk_',''):16s} TRAIN {100*wins_train[c]/tot:5.1f}%  "
              f"TEST {100*wins_test[c]/tot:5.1f}%")
    print(f"\n  train-winner == test-winner in {100*agree/tot:.1f}% of splits")
    print("""
  INTERPRETATION:
    >80% agreement -> the choice is stable; report it as an estimated specification
    ~50% agreement -> it is a coin flip; report the RANGE across lists instead and
                      state that the synonym list cannot be recovered from public data
  Note we now split by FIRM, not by row. Splitting rows would put XOM 2022 in
  training and XOM 2023 in testing -- near-duplicate observations that would make
  any list look artificially stable.
""")
print("saved -> outputs/phase8_bootstrap_ci.csv, outputs/phase8_permutation.csv")
