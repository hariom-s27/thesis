# =============================================================================
# GAP ANALYSIS — "we are not at 100%, so WHERE is it going wrong?"
#
# A single accuracy % tells you nothing about the CAUSE. This tool separates
# the two kinds of error, which need completely different fixes:
#
#   SYSTEMATIC  = every firm is off by roughly the SAME amount (low spread).
#                 One shared cause. Fixable. e.g. all transcripts slightly
#                 shorter than the source used by the authors.
#
#   SCATTERED   = firms are off by very different amounts (high spread).
#                 Not one cause -- usually small-denominator noise. Often NOT
#                 fixable, and should be reported as a limitation instead.
#
# Knowing which one you have tells you whether to keep debugging or stop.
#
# Input: validation_results.csv  (written by score_and_correlate.py)
# =============================================================================
import os
import numpy as np, pandas as pd

RESULTS_CSV = r"D:\sem_iitk\sem 8\thesis\outputs\validation_results.csv"
TRANSCRIPT_DIR = r"D:\sem_iitk\sem 8\thesis\api_transcripts"

df = pd.read_csv(RESULTS_CSV)
df = df[df["cc_expo_ew"].notna()]          # drop years with no published benchmark
print(f"firm-years with a benchmark: {len(df)}\n")

PAIRS = [("cc_expo","cc_expo_ew"), ("op_expo","op_expo_ew"),
         ("rg_expo","rg_expo_ew"), ("ph_expo","ph_expo_ew"),
         ("cc_pos","cc_pos_ew"),   ("cc_neg","cc_neg_ew"),
         ("cc_sent","cc_sent_ew"), ("cc_risk","cc_risk_ew")]

print("PER-MEASURE GAP ANALYSIS")
print("=" * 62)
for ours, off in PAIRS:
    if ours not in df.columns or off not in df.columns:
        continue
    v = df[(df[off].notna()) & (df[off].abs() > 0)]
    if len(v) == 0:
        print(f"{ours:9s}: official is 0 everywhere -> nothing to compare")
        continue
    r = 100 * v[ours] / v[off]
    sd = r.std() if len(r) > 1 else float("nan")
    print(f"{ours:9s}: mean {r.mean():6.1f}%  sd {sd:5.1f}  "
          f"min {r.min():6.1f}%  max {r.max():6.1f}%  n={len(v)}")
    if len(r) > 1 and sd < 15 and abs(r.mean() - 100) > 5:
        print(f"           -> SYSTEMATIC ({r.mean()-100:+.0f}% on every firm). "
              f"One shared cause -- worth fixing.")
    elif len(r) > 1 and sd >= 15:
        print(f"           -> SCATTERED (sd={sd:.0f}). No single cause; usually "
              f"small-denominator noise. Report as a limitation.")
    else:
        print("           -> within tolerance")

# ---- per-firm ranking: which firm to inspect first --------------------------
df["pct"] = 100 * df["cc_expo"] / df["cc_expo_ew"]
print("\nPER-FIRM (cc_expo), worst first:")
print(df[["ticker","year","cc_expo","cc_expo_ew","pct"]]
      .sort_values("pct").to_string(index=False))

# ---- is transcript length driving the gap? ---------------------------------
# If shorter transcripts score lower, the cause is missing text, not bad code.
if os.path.isdir(TRANSCRIPT_DIR):
    import glob
    words = {}
    for p in glob.glob(os.path.join(TRANSCRIPT_DIR, "*.txt")):
        tk = os.path.basename(p).split("_")[0]
        words[tk] = words.get(tk, 0) + len(open(p, encoding="utf-8",
                                                errors="ignore").read().split())
    df["total_words"] = df["ticker"].map(words)
    ok = df.dropna(subset=["total_words"])
    if len(ok) > 2:
        c = ok["total_words"].corr(ok["pct"])
        print(f"\ncorrelation(transcript length, accuracy %) = {c:.3f}")
        print("  strongly positive -> shorter transcripts score lower ==> MISSING TEXT")
        print("  near zero         -> length is not the cause; look elsewhere")

print("""
WHAT TO DO WITH THIS
--------------------
1. SYSTEMATIC under-scoring on cc_expo -> the usual cause is transcript
   completeness (your source has slightly less text than the authors' source).
   Check the length correlation above. If confirmed, this is a DATA limitation
   to report, not a code bug.
2. SCATTERED on rg_expo / cc_risk -> these have tiny denominators, so one extra
   sentence swings the ratio hugely. Do NOT tune to fix this. Report the noise.
3. Always inspect the WORST firm first -- open its transcripts and check for a
   truncated quarter or a missing Q&A section.
""")
