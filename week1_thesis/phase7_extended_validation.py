# =============================================================================
# PHASE 7 — EXTENDED VALIDATION SUITE
#
# Builds C1, C3, C4, C5, C6, C7 from the validation checklist in one run.
# (C2 external validity needs an outside download -- see notes at the bottom.)
#
#   C1  PLACEBO / NEGATIVE CONTROL   - can the measure correctly say "no"?
#   C5  SPLIT-HALF RELIABILITY       - is the measure internally consistent?
#   C6  PREPROCESSING ROBUSTNESS     - how much do our choices move the score?
#   C4  BALANCED-PANEL EVENT STUDY   - does exposure react to Paris 2015?
#   C3  HUMAN AUDIT SHEET            - exports 100 sentences for manual coding
#   C7  EXTERNAL VALIDITY (free!)    - our transcript scores vs the authors'
#                                      10-K MD&A scores (a DIFFERENT document type)
#
# Setup: pip install pdfplumber spacy nltk scikit-learn pandas
# =============================================================================
import os, glob, re, pickle, random
from collections import Counter
import numpy as np, pandas as pd, spacy
from nltk.tokenize import sent_tokenize
from sklearn.feature_extraction.text import CountVectorizer

# ---- paths (EDIT) -----------------------------------------------------------
TRANSCRIPT_DIR = r"D:\sem_iitk\sem 8\thesis\api_transcripts"
DICT_DIR       = r"D:\sem_iitk\sem 8\thesis\old _work\code\jofi13219-sup-0002-replicationcode\Replication Files Sautner et al. (2023)\B. Figure 1 2, Table 2, and IA Table 6 7 8 9 11\bigrams"
MEAS_ERR_CSV   = r"D:\sem_iitk\sem 8\thesis\old _work\csv\cc_measurementerror_reg.csv"
OUTPUT_DIR     = r"D:\sem_iitk\sem 8\thesis\outputs"

TICKER_ISIN = {"XOM":"US30231G1022","CVX":"US1667641005","NEE":"US65339F1012",
    "DUK":"US26441C2044","COP":"US20825C1045","OXY":"US6745991058","SO":"US8425871071",
    "D":"US25746U1097","DAL":"US2473617023",
    "GM":"US37045V1008","F":"US3453708600","CAT":"US1491231015",
    "BA":"US0970231058","MMM":"US88579Y1010",
    "JPM":"US46625H1005","MSFT":"US5949181045",
    "WMT":"US9311421039","PFE":"US7170811035","KO":"US1912161007","UNH":"US91324P1021"}

with open(os.path.join(DICT_DIR, "bigrams_07222021.pkl"), "rb") as f:
    CC = set(x.lower() for x in pickle.load(f))

nlp = spacy.load("en_core_web_sm", disable=["ner", "parser"])
nlp.add_pipe("sentencizer")
BASE_VEC = dict(analyzer="word", strip_accents="unicode", ngram_range=(2, 2), lowercase=True)

def make_vec(stop=True):
    return CountVectorizer(stop_words="english" if stop else None, **BASE_VEC)

def lemma_sents(text, lemmatise=True):
    out = []
    for s in sent_tokenize(text):
        if lemmatise:
            d = nlp(s)
            toks = [t.lemma_.lower() for t in d if not t.is_space and not t.is_punct]
        else:
            toks = [w.lower() for w in re.findall(r"[A-Za-z']+", s)]
        if toks: out.append(" ".join(toks))
    return out

def expo(sents, vec, D=CC):
    if not sents: return 0.0, 0
    M = vec.fit_transform(sents)
    feats = np.array(vec.get_feature_names_out())
    counts = np.asarray(M.sum(axis=0)).ravel()
    B = int(counts.sum())
    if B == 0: return 0.0, 0
    freq = dict(zip(feats, counts))
    return sum(int(freq[b]) for b in (set(feats) & D)) / B, B

# ---- load transcripts once --------------------------------------------------
PAT = re.compile(r"^([A-Z\.\-]+)_(\d{4})Q([1-4])", re.I)
docs = []
for p in sorted(glob.glob(os.path.join(TRANSCRIPT_DIR, "*.txt"))):
    m = PAT.match(os.path.basename(p))
    if not m: continue
    docs.append(dict(ticker=m.group(1).upper(), year=int(m.group(2)),
                     quarter=int(m.group(3)),
                     text=open(p, encoding="utf-8", errors="ignore").read()))
print(f"loaded {len(docs)} transcripts\n")
VEC = make_vec(True)

# =============================================================================
# C1 — PLACEBO / NEGATIVE CONTROL
# =============================================================================
# LOGIC: every test so far only shows the measure finds climate talk where it
# exists. None shows it can correctly return ZERO. We build three controls:
#   (a) WORD SCRAMBLE  - same words, random order. Real bigrams are destroyed,
#                        so a valid measure must collapse toward zero. If it does
#                        NOT, the measure is just counting single words.
#   (b) SENTENCE SHUFFLE - sentences reordered but kept intact. Bigrams survive,
#                        so the score SHOULD be unchanged. This is a control on
#                        the control: it proves (a)'s drop is not an artefact.
#   (c) LOW-CLIMATE FIRMS - JPM/PFE/UNH act as a natural negative control.
print("=" * 70)
print("C1 — PLACEBO / NEGATIVE CONTROL")
print("=" * 70)
random.seed(42)
sample = random.sample(docs, min(30, len(docs)))
rows = []
for d in sample:
    sents = lemma_sents(d["text"])
    real, B = expo(sents, VEC)
    words = " ".join(sents).split()
    random.shuffle(words)
    scrambled = [" ".join(words[i:i+20]) for i in range(0, len(words), 20)]
    scr, _ = expo(scrambled, VEC)
    shuf = sents[:]; random.shuffle(shuf)
    sh, _ = expo(shuf, VEC)
    rows.append(dict(doc=f"{d['ticker']}_{d['year']}Q{d['quarter']}",
                     real=real, scrambled=scr, sent_shuffled=sh))
pl = pd.DataFrame(rows)
print(f"  real text        mean exposure: {pl['real'].mean():.6f}")
print(f"  WORD-scrambled   mean exposure: {pl['scrambled'].mean():.6f}  "
      f"({100*pl['scrambled'].mean()/max(pl['real'].mean(),1e-12):.1f}% of real)")
print(f"  SENTENCE-shuffled mean exposure: {pl['sent_shuffled'].mean():.6f}  "
      f"({100*pl['sent_shuffled'].mean()/max(pl['real'].mean(),1e-12):.1f}% of real)")
print("""
  PASS if: word-scrambled collapses toward 0 (bigrams destroyed) AND
           sentence-shuffled stays ~100% (bigrams intact).
  FAIL if: word-scrambled stays high -> the measure is not really using word ORDER.
""")

# =============================================================================
# C5 — SPLIT-HALF RELIABILITY
# =============================================================================
# LOGIC: split each transcript into first half / second half of its sentences and
# score both. A reliable instrument gives a similar reading from either half.
# Low correlation would mean the score depends on WHERE in the call we look.
print("=" * 70)
print("C5 — SPLIT-HALF RELIABILITY")
print("=" * 70)
rows = []
for d in docs:
    sents = lemma_sents(d["text"])
    if len(sents) < 20: continue
    mid = len(sents) // 2
    a, _ = expo(sents[:mid], VEC)
    b, _ = expo(sents[mid:], VEC)
    rows.append(dict(doc=f"{d['ticker']}_{d['year']}Q{d['quarter']}", half1=a, half2=b))
sh = pd.DataFrame(rows)
r = sh["half1"].corr(sh["half2"])
sb = 2 * r / (1 + r) if r == r else np.nan          # Spearman-Brown correction
print(f"  n = {len(sh)} transcripts")
print(f"  correlation(first half, second half) = {r:.4f}")
print(f"  Spearman-Brown corrected reliability = {sb:.4f}")
print("""
  Spearman-Brown adjusts for the fact that each half is only half as long as the
  full transcript, so it estimates the reliability of the FULL measure.
  Above 0.7 is conventionally acceptable; above 0.8 is good.
""")

# =============================================================================
# C6 — PREPROCESSING ROBUSTNESS
# =============================================================================
# LOGIC: our audit found artefacts like "example carbon" created by removing stop
# words BEFORE forming bigrams. Does that choice change the answer? We re-score
# under three variants and correlate each against the baseline.
print("=" * 70)
print("C6 — PREPROCESSING ROBUSTNESS")
print("=" * 70)
sub = random.sample(docs, min(60, len(docs)))
res = []
for d in sub:
    lem = lemma_sents(d["text"], True)
    raw = lemma_sents(d["text"], False)
    base, _ = expo(lem, make_vec(True))
    nostop, _ = expo(lem, make_vec(False))
    nolem, _ = expo(raw, make_vec(True))
    res.append(dict(baseline=base, no_stopword_removal=nostop, no_lemmatisation=nolem))
rb = pd.DataFrame(res)
print(f"  n = {len(rb)} transcripts")
for c in ["no_stopword_removal", "no_lemmatisation"]:
    cr = rb["baseline"].corr(rb[c])
    ratio = rb[c].mean() / max(rb["baseline"].mean(), 1e-12)
    print(f"  {c:22s}: corr vs baseline {cr:.4f} | level {100*ratio:5.1f}% of baseline")
print("""
  High correlation = ranking of firms is robust even if levels shift.
  A large LEVEL change with high CORRELATION means: do not compare our absolute
  numbers to anyone using different preprocessing, but our RANKINGS are safe.
""")

# =============================================================================
# C4 — BALANCED-PANEL EVENT STUDY (Paris Agreement, Dec 2015)
# =============================================================================
print("=" * 70)
print("C4 — BALANCED-PANEL EVENT STUDY")
print("=" * 70)
sc = []
for d in docs:
    e, _ = expo(lemma_sents(d["text"]), VEC)
    sc.append(dict(ticker=d["ticker"], year=d["year"], quarter=d["quarter"], cc_expo=e))
sdf = pd.DataFrame(sc)
qc = sdf.groupby(["ticker","year"]).size().reset_index(name="n")
fy = sdf.merge(qc[qc["n"] == 4][["ticker","year"]], on=["ticker","year"]) \
        .groupby(["ticker","year"])["cc_expo"].mean().reset_index()
yrs = set(range(2012, 2021))
bal = [t for t, g in fy.groupby("ticker") if yrs.issubset(set(g["year"]))]
print(f"  balanced panel 2012-2020: {bal}")
if len(bal) >= 2:
    b = fy[(fy["ticker"].isin(bal)) & (fy["year"].between(2012, 2020))]
    pre = b[b["year"] <= 2015]["cc_expo"]
    post = b[b["year"] >= 2016]["cc_expo"]
    print(f"\n  pre-Paris  (2012-2015): mean {pre.mean():.6f}  n={len(pre)}")
    print(f"  post-Paris (2016-2020): mean {post.mean():.6f}  n={len(post)}")
    if pre.mean() > 0:
        print(f"  change: {100*(post.mean()/pre.mean()-1):+.1f}%")
    print("\n  per-year means (balanced panel only):")
    print(b.groupby("year")["cc_expo"].mean().round(6).to_string())
    print("""
  This is a DESCRIPTIVE comparison, not a causal claim. Many things changed after
  2015. State it as "exposure was higher after the Paris Agreement", never
  "Paris caused higher exposure".""")
else:
    print("  not enough firms with complete 2012-2020 coverage")

# =============================================================================
# C3 — HUMAN AUDIT CODING SHEET
# =============================================================================
# LOGIC: the paper used 18 human coders. We export a randomised sheet so you (and
# ideally a second coder) can mark each sentence 1 = genuinely about climate
# change, 0 = false positive. Precision = mean of the codes.
print("=" * 70)
print("C3 — HUMAN AUDIT SHEET")
print("=" * 70)
hits = []
for d in docs:
    sents = lemma_sents(d["text"])
    if not sents: continue
    M = VEC.fit_transform(sents)
    feats = np.array(VEC.get_feature_names_out())
    for i, s in enumerate(sents):
        got = [feats[j] for j in M[i].indices if feats[j] in CC]
        if got:
            hits.append(dict(doc=f"{d['ticker']}_{d['year']}Q{d['quarter']}",
                             matched_bigrams="; ".join(got[:4]), sentence=s[:300]))
random.seed(7)
audit = pd.DataFrame(random.sample(hits, min(100, len(hits))))
audit["coder1_is_climate_1or0"] = ""
audit["coder2_is_climate_1or0"] = ""
audit.to_csv(os.path.join(OUTPUT_DIR, "audit_coding_sheet.csv"), index=False)
print(f"  matched sentences available: {len(hits)}")
print(f"  exported {len(audit)} for coding -> outputs/audit_coding_sheet.csv")
print("""
  HOW TO USE: open in Excel. For each row mark 1 if the sentence is genuinely
  about climate change, 0 if not. Get a second person to code independently.
  Then report:
     precision      = mean of coder1 column
     agreement      = % of rows where both coders match
     Cohen's kappa  = agreement corrected for chance
  Report precision as your measure's accuracy at the sentence level.
""")

# =============================================================================
# C7 — EXTERNAL VALIDITY vs 10-K MD&A SCORES  (free, already in your files)
# =============================================================================
# LOGIC: cc_expo_ew_mda in cc_measurementerror_reg.csv is climate exposure the
# authors measured from 10-K MD&A sections -- a COMPLETELY DIFFERENT document type
# from earnings calls. If our transcript-based scores correlate with it, that is
# convergent validity from an independent text source, not circular.
print("=" * 70)
print("C7 — EXTERNAL VALIDITY: our transcripts vs 10-K MD&A")
print("=" * 70)
if os.path.exists(MEAS_ERR_CSV):
    me = pd.read_csv(MEAS_ERR_CSV, low_memory=False)
    fy2 = fy.copy()
    fy2["isin"] = fy2["ticker"].map(TICKER_ISIN)
    mg = fy2.merge(me[["isin","year","cc_expo_ew","cc_expo_ew_mda"]],
                   on=["isin","year"], how="inner")
    print(f"  matched firm-years: {len(mg)}")
    if len(mg) >= 5:
        print(f"  ours vs their CALL score : r = {mg['cc_expo'].corr(mg['cc_expo_ew']):.4f}")
        print(f"  ours vs their MD&A score : r = {mg['cc_expo'].corr(mg['cc_expo_ew_mda']):.4f}  <-- INDEPENDENT")
        print(f"  their call vs their MD&A : r = {mg['cc_expo_ew'].corr(mg['cc_expo_ew_mda']):.4f}  (benchmark)")
        print("""
  The MD&A correlation is the important one: it comes from annual reports, not
  earnings calls, so it shares no text with our pipeline. Expect it to be LOWER
  than the call-to-call correlation -- firms write differently in filings than
  they speak on calls. If ours-vs-MD&A is close to their-call-vs-MD&A, our measure
  behaves like theirs against an outside yardstick.""")
        mg.to_csv(os.path.join(OUTPUT_DIR, "c7_external_validity.csv"), index=False)
else:
    print("  cc_measurementerror_reg.csv not found -- check MEAS_ERR_CSV path")

pl.to_csv(os.path.join(OUTPUT_DIR, "c1_placebo.csv"), index=False)
sh.to_csv(os.path.join(OUTPUT_DIR, "c5_splithalf.csv"), index=False)
rb.to_csv(os.path.join(OUTPUT_DIR, "c6_robustness.csv"), index=False)
print("\nsaved -> outputs/c1_placebo.csv, outputs/c5_splithalf.csv, outputs/c6_robustness.csv,")
print("         outputs/audit_coding_sheet.csv, outputs/c7_external_validity.csv")

# =============================================================================
# C2 — NOT AUTOMATED (needs an outside download)
# For an emissions-based check, download EPA GHG Reporting Program facility data
# (free, epa.gov/ghgreporting), aggregate to parent company, match to your 14
# tickers by hand, and correlate with cc_expo. With n=14 this is indicative only.
# Note C7 above already gives you an independent-source validation for free.
# =============================================================================
