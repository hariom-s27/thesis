# =============================================================================
# PHASE 5 — FULL VALIDATION SUITE
# Replicates the validation exercises the AUTHORS themselves performed, so the
# thesis can say: "we validated the same way the original paper did."
#
# The paper publishes several numbers we can check our output against:
#
#  (1) Table IA.V correlations between measures:
#         CCExposure vs Opp = 0.897 | vs Reg = 0.523 | vs Phy = 0.224
#         EW vs TFIDF version   = 0.997
#  (2) Section A.5 / Figure 2 — seed-only vs discovery:
#         CCExposureInitial (initial bigrams only) wrongly shows ZERO exposure in
#         27% of top-decile transcripts, and >62% in the second decile.
#         This quantifies the VALUE ADDED by the keyword-discovery step.
#  (3) Section A.4 — perturbation test:
#         drop one initial bigram at a time; correlation with full CCExposure
#         stays above 85%, i.e. the measure does not hinge on any single seed.
#  (4) Face validity + human audit  (see audit_bigrams.py)
#
# NOTE on (3): the authors RE-RUN the whole discovery algorithm after dropping a
# seed. We cannot (their corpus is private), so we run a weaker but honest
# variant: we drop the seed from the released dictionary C. State this clearly
# in the thesis as a deviation.
# =============================================================================
import os, glob, re, pickle
from collections import Counter
import numpy as np, pandas as pd, spacy
from nltk.tokenize import sent_tokenize
from sklearn.feature_extraction.text import CountVectorizer

# ---- paths (EDIT) -----------------------------------------------------------
TRANSCRIPT_DIR = r"D:\sem_iitk\sem 8\thesis\api_transcripts"
DICT_DIR       = r"D:\sem_iitk\sem 8\thesis\old _work\code\jofi13219-sup-0002-replicationcode\Replication Files Sautner et al. (2023)\B. Figure 1 2, Table 2, and IA Table 6 7 8 9 11\bigrams"

# ---- Table IA.III — the 50 initial bigrams (typos preserved as published) ----
INITIAL = {"air pollution","electric vehicle","new energy","air quality","energy climate",
"ozone layer","air temperature","energy conversion","renewable energy","biomass energy",
"energy efficient","sea level","carbon dioxide","energy environment","sea water",
"carbon emission","environmental sustainability","snow ice","carbon energy","exterme weather",
"solar energy","carbon neutral","flue gas","solar thermal","carbon price","forest land",
"sustainable energy","carbon sink","gas emission","water resource","carbon tax","ghg emission",
"water resources","clean air","global decarbonization","wave energy","clean energy","global warm",
"weather climate","clean water","greenhouse gas","wind energy","climate change","heat power",
"wind power","coastal area","kyoto protocol","wind resource","costal region","natural hazard"}

# ---- Table IA.IV — topic initial bigrams ------------------------------------
INIT_OPP = {"heat power","new energy","renewable energy","wind power","electric vehicle",
"clean energy","wind energy","solar energy","plug hybrid","renewable resource","solar farm",
"rooftop solar","sustainable energy","hybrid car","renewable electricity","wave power",
"geothermal power","electric hybrid"}
INIT_REG = {"greenhouse gas","reduce emission","carbon emission","carbon dioxide","gas emission",
"air pollution","reduce carbon","carbon tax","carbon price","emission trade","dioxide emission",
"environmental standard","epa regulation","energy regulatory","nox emission","carbon reduction",
"carbon market","mercury emission","energy independence"}
INIT_PHY = {"coastal area","global warm","snow ice","forest land","sea level","nickel metal",
"storm water","heavy snow","air water","natural hazard","sea water","warm climate",
"water discharge","ice product"}

def _d(n):
    with open(os.path.join(DICT_DIR, n), "rb") as f:
        return set(x.lower() for x in pickle.load(f))
CC, OP = _d("bigrams_07222021.pkl"), _d("opportunity_bigrams_4.pkl")
RG, PH = _d("regulatory_bigrams_4.pkl"), _d("physical_bigrams_4.pkl")

# ---- sanity check: initial bigrams should live inside C ---------------------
inside = INITIAL & CC
print(f"initial bigrams found inside released C: {len(inside)}/{len(INITIAL)}")
print(f"  not found (expect the paper's typos): {sorted(INITIAL - CC)}\n")

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

# ---- score every transcript, caching bigram counts for reuse ----------------
PAT = re.compile(r"^([A-Z\.\-]+)_(\d{4})Q([1-4])", re.I)
recs, doc_freq = [], Counter()
files = sorted(glob.glob(os.path.join(TRANSCRIPT_DIR, "*.txt")))
print(f"scoring {len(files)} transcripts...")
for p in files:
    m = PAT.match(os.path.basename(p))
    if not m: continue
    sents = lemma_sents(open(p, encoding="utf-8", errors="ignore").read())
    M = vec.fit_transform(sents)
    feats = np.array(vec.get_feature_names_out())
    counts = np.asarray(M.sum(axis=0)).ravel()
    B = int(counts.sum())
    present = {f: int(n) for f, n in zip(feats, counts) if n > 0}
    cc_counts = {b: n for b, n in present.items() if b in CC}
    recs.append(dict(ticker=m.group(1).upper(), year=int(m.group(2)),
                     quarter=int(m.group(3)), B=B, present=present, cc=cc_counts))
    for b in cc_counts: doc_freq[b] += 1
N = len(recs)
print(f"scored: {N}\n")

def score(pres, B, D):
    return sum(n for b, n in pres.items() if b in D) / B

rows = []
for r in recs:
    tw = sum(n * np.log(N / doc_freq[b]) for b, n in r["cc"].items() if doc_freq[b] > 0)
    rows.append(dict(ticker=r["ticker"], year=r["year"], quarter=r["quarter"],
        cc_expo=score(r["present"], r["B"], CC),
        op_expo=score(r["present"], r["B"], OP),
        rg_expo=score(r["present"], r["B"], RG),
        ph_expo=score(r["present"], r["B"], PH),
        cc_tfidf=tw / r["B"],
        cc_init=score(r["present"], r["B"], INITIAL),
        op_init=score(r["present"], r["B"], INIT_OPP),
        rg_init=score(r["present"], r["B"], INIT_REG),
        ph_init=score(r["present"], r["B"], INIT_PHY)))
df = pd.DataFrame(rows)

# =============================================================================
# TEST 1 — correlations between measures  (paper Table IA.V)
# =============================================================================
print("=" * 66)
print("TEST 1 — CORRELATIONS BETWEEN MEASURES (paper Table IA.V)")
print("=" * 66)
targets = [("cc_expo","op_expo",0.897), ("cc_expo","rg_expo",0.523),
           ("cc_expo","ph_expo",0.224), ("cc_expo","cc_tfidf",0.997)]
for a, b, tgt in targets:
    if df[a].std() == 0 or df[b].std() == 0:
        print(f"  {a:8s} vs {b:9s}: n/a (no variation)"); continue
    got = df[a].corr(df[b])
    flag = "OK" if abs(got - tgt) < 0.15 else "CHECK"
    print(f"  {a:8s} vs {b:9s}: ours {got:6.3f} | paper {tgt:5.3f}   [{flag}]")
print("\n  Note: the paper computes these on 80,000+ firm-years across 34 countries.")
print("  A small, deliberately diverse sample will not reproduce them exactly;")
print("  the SIGN and rough ORDERING (Opp > Reg > Phy) are what matter.\n")

# =============================================================================
# TEST 2 — value added by keyword discovery  (paper Section A.5 / Figure 2)
# =============================================================================
print("=" * 66)
print("TEST 2 — SEED-ONLY vs DISCOVERY (paper Fig. 2: 27% zeros in top decile)")
print("=" * 66)
d = df[df["cc_expo"] > 0].copy()
d["decile"] = pd.qcut(d["cc_expo"], 10, labels=False, duplicates="drop") + 1
tab = d.groupby("decile").apply(
    lambda g: pd.Series({"n": len(g),
                         "pct_zero_initial": 100 * (g["cc_init"] == 0).mean()})
).reset_index()
print(tab.to_string(index=False))
top = tab[tab["decile"] == tab["decile"].max()]
if len(top):
    print(f"\n  top decile: seed-only wrongly shows ZERO in "
          f"{top['pct_zero_initial'].iloc[0]:.0f}% of transcripts (paper: 27%)")
print("  Higher % = the discovery step is doing more work. This is the single")
print("  best evidence that the King algorithm adds value over a hand-made list.\n")

for topic, full_c, init_c in [("Opp","op_expo","op_init"), ("Reg","rg_expo","rg_init"),
                              ("Phy","ph_expo","ph_init")]:
    sub = df[df[full_c] > 0]
    if len(sub):
        print(f"  {topic}: of {len(sub)} transcripts with positive exposure, "
              f"seed-only misses {100*(sub[init_c]==0).mean():.0f}%")

# =============================================================================
# TEST 3 — perturbation: does any single seed dominate?  (paper Section A.4)
# =============================================================================
print("\n" + "=" * 66)
print("TEST 3 — PERTURBATION (paper A.4: all correlations stay above 85%)")
print("=" * 66)
print("  DEVIATION: authors re-run discovery after dropping a seed; we drop the")
print("  seed from the released C. Weaker, but honest -- state this in the thesis.\n")
base = df["cc_expo"].values
res = []
for seed in sorted(INITIAL & CC):
    Cp = CC - {seed}
    vals = np.array([score(r["present"], r["B"], Cp) for r in recs])
    if vals.std() == 0: continue
    res.append((seed, np.corrcoef(base, vals)[0, 1]))
res.sort(key=lambda x: x[1])
print(f"  seeds tested: {len(res)} | min corr {res[0][1]:.4f} | "
      f"mean {np.mean([c for _, c in res]):.4f}")
print("  5 most influential seeds (lowest correlation when removed):")
for s, c in res[:5]:
    print(f"    {c:.4f}  {s}")
below = [s for s, c in res if c < 0.85]
print(f"\n  seeds falling below the paper's 85% threshold: "
      f"{len(below)}{' -> ' + str(below) if below else ' (none) -- matches the paper'}")

df.to_csv("phase5_validation.csv", index=False)
print("\nsaved -> phase5_validation.csv")
