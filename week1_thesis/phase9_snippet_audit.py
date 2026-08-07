# =============================================================================
# PHASE 9 — SNIPPET AUDIT (corrected design)
#
# WHY THE OLD SHEET WAS BROKEN
# The earlier audit_coding_sheet.csv sampled ONLY sentences the algorithm had
# already flagged. That can measure PRECISION (when it fires, is it right?) but
# never RECALL (how often does it MISS climate discussion?). A measure that never
# fires at all would score 100% precision on that design.
#
# THE CORRECTED DESIGN (Baker, Bloom & Davis 2016; Hassan et al. 2019)
#   ARM 1 - POSITIVE: transcripts with CCExposure > 0. Take the 10 sentences
#           surrounding the climate bigram with the highest frequency in that
#           transcript. Tests: when the algorithm fires, is it right?
#   ARM 2 - ZERO:     transcripts with CCExposure = 0. Take a RANDOM run of 10
#           consecutive sentences. Tests: when the algorithm stays silent, was
#           there really nothing there?
#
# Two further design points that matter:
#   BLINDING  - the two arms are shuffled together and the arm label is written
#               to a SEPARATE key file. If the coder can see which snippet the
#               algorithm flagged, they will unconsciously agree with it.
#   CONFIDENCE- coders record 3 (confident) / 2 / 1 (hard call), so you can check
#               whether errors concentrate in the hard calls.
#
# USAGE
#   MODE = "build"   -> creates audit_snippets.csv (to code) + audit_key.csv (hidden)
#   MODE = "analyse" -> reads the completed sheet and computes precision, recall,
#                       accuracy, and Cohen's kappa
# =============================================================================
import os, glob, re, pickle, random
import numpy as np, pandas as pd

MODE = "build"          # "build" first; switch to "analyse" after coding

TRANSCRIPT_DIR = r"D:\sem_iitk\sem 8\thesis\api_transcripts"
DICT_DIR       = r"D:\sem_iitk\sem 8\thesis\old _work\code\jofi13219-sup-0002-replicationcode\Replication Files Sautner et al. (2023)\B. Figure 1 2, Table 2, and IA Table 6 7 8 9 11\bigrams"
OUTPUT_DIR     = r"D:\sem_iitk\sem 8\thesis\outputs"
N_POSITIVE = 60         # snippets from scoring transcripts
N_ZERO     = 40         # snippets from zero-scoring transcripts  <-- the fix
SNIPPET_LEN = 10
SEED = 2024

# =============================================================================
if MODE == "build":
    import spacy
    from nltk.tokenize import sent_tokenize
    from sklearn.feature_extraction.text import CountVectorizer

    with open(os.path.join(DICT_DIR, "bigrams_07222021.pkl"), "rb") as f:
        CC = set(x.lower() for x in pickle.load(f))
    nlp = spacy.load("en_core_web_sm", disable=["ner", "parser"])
    nlp.add_pipe("sentencizer")
    vec = CountVectorizer(analyzer="word", strip_accents="unicode",
                          ngram_range=(2, 2), lowercase=True, stop_words="english")

    def prep(text):
        """Return (original sentences, lemmatised sentences) aligned by index."""
        orig, lem = [], []
        for s in sent_tokenize(text):
            d = nlp(s)
            l = [t.lemma_.lower() for t in d if not t.is_space and not t.is_punct]
            if l:
                orig.append(re.sub(r"\s+", " ", s).strip())
                lem.append(" ".join(l))
        return orig, lem

    PAT = re.compile(r"^([A-Z\.\-]+)_(\d{4})Q([1-4])", re.I)
    files = [p for p in sorted(glob.glob(os.path.join(TRANSCRIPT_DIR, "*.txt")))
             if PAT.match(os.path.basename(p))]
    random.seed(SEED)
    random.shuffle(files)

    positives, zeros = [], []
    for p in files:
        if len(positives) >= N_POSITIVE and len(zeros) >= N_ZERO:
            break
        name = os.path.basename(p).replace(".txt", "")
        orig, lem = prep(open(p, encoding="utf-8", errors="ignore").read())
        if len(orig) < SNIPPET_LEN + 2:
            continue
        M = vec.fit_transform(lem)
        feats = np.array(vec.get_feature_names_out())
        counts = np.asarray(M.sum(axis=0)).ravel()
        found = {f: int(n) for f, n in zip(feats, counts) if f in CC and n > 0}

        if found and len(positives) < N_POSITIVE:
            # the highest-frequency climate bigram in this transcript
            top = max(found, key=found.get)
            col = int(np.where(feats == top)[0][0])
            hits = M[:, col].nonzero()[0]
            if len(hits) == 0: continue
            centre = int(hits[0])
            lo = max(0, centre - SNIPPET_LEN // 2)
            hi = min(len(orig), lo + SNIPPET_LEN)
            positives.append(dict(doc=name, arm="positive", anchor_bigram=top,
                                  anchor_count=found[top],
                                  snippet=" ".join(orig[lo:hi])[:1500]))
        elif not found and len(zeros) < N_ZERO:
            # RANDOM window -- we have no anchor, because nothing was detected
            lo = random.randint(0, len(orig) - SNIPPET_LEN)
            zeros.append(dict(doc=name, arm="zero", anchor_bigram="", anchor_count=0,
                              snippet=" ".join(orig[lo:lo+SNIPPET_LEN])[:1500]))

    df = pd.DataFrame(positives + zeros)
    if df.empty:
        raise SystemExit("no snippets built -- check TRANSCRIPT_DIR")
    df = df.sample(frac=1, random_state=SEED).reset_index(drop=True)   # BLINDING
    df.insert(0, "snippet_id", [f"S{i:03d}" for i in range(len(df))])

    # hidden key: which arm each snippet came from
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df[["snippet_id", "doc", "arm", "anchor_bigram", "anchor_count"]] \
        .to_csv(os.path.join(OUTPUT_DIR, "audit_key.csv"), index=False)

    # coding sheet: NO arm, NO bigram -- the coder must judge the text alone
    sheet = df[["snippet_id", "snippet"]].copy()
    for c in ["coder1_climate_1or0", "coder1_confidence_1to3",
              "coder2_climate_1or0", "coder2_confidence_1to3"]:
        sheet[c] = ""
    sheet.to_csv(os.path.join(OUTPUT_DIR, "audit_snippets.csv"), index=False)

    print(f"built {len(df)} snippets: {len(positives)} positive-arm, {len(zeros)} zero-arm")
    print("  -> outputs/audit_snippets.csv  (give this to coders)")
    print("  -> outputs/audit_key.csv       (DO NOT show coders)")
    print("""
CODING INSTRUCTIONS (paste into the sheet or a separate guide)
  For each snippet mark:
    climate_1or0 = 1 if the text provides evidence that the firm is discussing
                     climate change, its risks, regulation, or related
                     opportunities. 0 otherwise.
    confidence   = 3 (clearly right), 2 (fairly sure), 1 (hard call)
  Judge ONLY the text shown. You are not told whether the algorithm flagged it.
  Two coders should code independently, then discuss disagreements and write
  down the rule used to resolve each one -- that becomes your coding guide.
""")

# =============================================================================
elif MODE == "analyse":
    sheet = pd.read_csv(os.path.join(OUTPUT_DIR, "audit_snippets.csv"))
    key = pd.read_csv(os.path.join(OUTPUT_DIR, "audit_key.csv"))
    d = sheet.merge(key, on="snippet_id")
    d = d[d["coder1_climate_1or0"].notna()]
    if len(d) == 0:
        raise SystemExit("no coded rows found -- fill in coder1_climate_1or0 first")
    d["c1"] = pd.to_numeric(d["coder1_climate_1or0"], errors="coerce")
    d = d[d["c1"].notna()]
    pos, zer = d[d["arm"] == "positive"], d[d["arm"] == "zero"]

    print("=" * 60)
    print("AUDIT RESULTS")
    print("=" * 60)
    print(f"  coded snippets: {len(d)}  (positive arm {len(pos)}, zero arm {len(zer)})\n")
    if len(pos):
        prec = pos["c1"].mean()
        print(f"  PRECISION  = {100*prec:.1f}%   "
              f"(of flagged snippets, {int(pos['c1'].sum())}/{len(pos)} truly climate)")
    if len(zer):
        miss = zer["c1"].mean()
        print(f"  FALSE-NEG  = {100*miss:.1f}%   "
              f"(of zero-scoring transcripts, {int(zer['c1'].sum())}/{len(zer)} DID discuss climate)")
        print(f"  implied RECALL (rough) = {100*(1-miss):.1f}%")
    if len(pos) and len(zer):
        tp, fn = pos["c1"].sum(), zer["c1"].sum()
        tn, fp = len(zer) - fn, len(pos) - tp
        print(f"\n  confusion (snippet level):  TP={int(tp)} FP={int(fp)} "
              f"FN={int(fn)} TN={int(tn)}")
        acc = (tp + tn) / (tp + tn + fp + fn)
        print(f"  accuracy = {100*acc:.1f}%")

    # confidence breakdown -- are errors concentrated in hard calls?
    if "coder1_confidence_1to3" in d.columns:
        d["conf"] = pd.to_numeric(d["coder1_confidence_1to3"], errors="coerce")
        cd = d[d["conf"].notna()]
        if len(cd):
            print("\n  by confidence (positive arm precision):")
            for lvl in (3, 2, 1):
                s = cd[(cd["conf"] == lvl) & (cd["arm"] == "positive")]
                if len(s):
                    print(f"    confidence {lvl}: {100*s['c1'].mean():5.1f}%  (n={len(s)})")

    # Cohen's kappa
    if "coder2_climate_1or0" in d.columns:
        d["c2"] = pd.to_numeric(d["coder2_climate_1or0"], errors="coerce")
        both = d[d["c2"].notna()]
        if len(both) >= 10:
            po = (both["c1"] == both["c2"]).mean()
            p1 = both["c1"].mean(); p2 = both["c2"].mean()
            pe = p1*p2 + (1-p1)*(1-p2)
            kappa = (po - pe) / (1 - pe) if pe < 1 else np.nan
            print(f"\n  inter-coder agreement = {100*po:.1f}%")
            print(f"  Cohen's kappa         = {kappa:.3f}")
            print("    <0.40 poor | 0.40-0.60 moderate | 0.60-0.80 substantial | >0.80 almost perfect")
        else:
            print("\n  (add a second coder for kappa -- needs >=10 double-coded rows)")

    print("""
  REPORTING NOTE: the zero-arm rate is a FALSE-NEGATIVE rate at the SNIPPET level,
  not at the transcript level -- a random 10-sentence window can easily miss
  climate talk that occurs elsewhere in the same call. Report it as a lower bound
  on missed discussion, and say so explicitly.
""")
