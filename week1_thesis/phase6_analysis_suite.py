# =============================================================================
# PHASE 6 — ANALYSIS SUITE (the paper's validation LOGIC, run on OUR data)
#
# This is NOT number-matching against the paper. These are the same ANALYSES the
# authors used to argue their measure is meaningful, applied to our own results
# so we can make the argument independently. If our data shows the same PATTERNS
# they found, the measure works -- regardless of exact values.
#
# What the paper does, and why:
#   1. FIRM PROFILES        - who scores high, and on which topic?
#   2. CROSS-FIRM RANKING   - does the ordering match economic common sense?
#   3. YEAR-ON-YEAR GROWTH  - does exposure move over time as expected?
#   4. TIME SERIES          - does the aggregate rise around climate events?
#   5. INDUSTRY VARIATION   - do utilities/energy top the list? (paper Table IV)
#   6. VARIANCE DECOMPOSITION - is variation FIRM-level, not just industry/year?
#      (paper Table VI -- this is their single strongest validity argument)
#
# Input: phase5_validation.csv  (transcript-level, from phase5_validation_suite.py)
# =============================================================================
import os
import numpy as np, pandas as pd

OUTPUT_DIR = r"D:\sem_iitk\sem 8\thesis\outputs"
RESULTS = os.path.join(OUTPUT_DIR, "phase5_validation.csv")

# industry labels -- EDIT to match your firm list
INDUSTRY = {
    "XOM":"Energy","CVX":"Energy","COP":"Energy","OXY":"Energy",
    "NEE":"Utilities","DUK":"Utilities","SO":"Utilities","D":"Utilities",
    "DAL":"Airlines",
    "GM":"Autos","F":"Autos",
    "CAT":"Machinery","BA":"Aerospace","MMM":"Industrials",
    "JPM":"Finance","MSFT":"Technology",
    "WMT":"Retail","KO":"Consumer","PFE":"Pharma","UNH":"Healthcare",
}

df = pd.read_csv(RESULTS)
df["industry"] = df["ticker"].map(INDUSTRY).fillna("Other")
pd.set_option("display.float_format", lambda x: f"{x:.6f}")

# keep only complete firm-years (4 quarters) -- same rule as the official data
qc = df.groupby(["ticker","year"]).size().reset_index(name="n")
df = df.merge(qc[qc["n"] == 4][["ticker","year"]], on=["ticker","year"], how="inner")
MEAS = ["cc_expo","op_expo","rg_expo","ph_expo"]
fy = df.groupby(["ticker","industry","year"])[MEAS].mean().reset_index()
print(f"firm-years: {len(fy)} | firms: {fy['ticker'].nunique()} | "
      f"years: {fy['year'].min()}-{fy['year'].max()}\n")

# =============================================================================
# 1. FIRM PROFILES — level + topic mix
# =============================================================================
print("=" * 70)
print("1. FIRM PROFILES  (mean across years; topic shares as % of topic total)")
print("=" * 70)
prof = fy.groupby(["ticker","industry"])[MEAS].mean().reset_index()
tot = prof[["op_expo","rg_expo","ph_expo"]].sum(axis=1).replace(0, np.nan)
for c in ["op","rg","ph"]:
    prof[f"{c}_share%"] = (100 * prof[f"{c}_expo"] / tot).round(1)
prof = prof.sort_values("cc_expo", ascending=False)
print(prof[["ticker","industry","cc_expo","op_share%","rg_share%","ph_share%"]]
      .to_string(index=False))
print("""
  READ THIS AS: cc_expo = how much climate talk. The shares say WHAT KIND.
  A utility heavy on op_share is chasing renewable OPPORTUNITY; a firm heavy on
  rg_share is worried about REGULATION. Two firms can have the same exposure
  for completely different reasons -- that is the point of the topic measures.
""")

# =============================================================================
# 2. CROSS-FIRM RANKING — the common-sense test
# =============================================================================
print("=" * 70)
print("2. CROSS-FIRM RANKING")
print("=" * 70)
rank = prof[["ticker","industry","cc_expo"]].reset_index(drop=True)
rank.index += 1
print(rank.to_string())
hi, lo = rank.iloc[0], rank.iloc[-1]
if lo["cc_expo"] > 0:
    print(f"\n  spread: {hi['ticker']} talks about climate "
          f"{hi['cc_expo']/lo['cc_expo']:.0f}x more than {lo['ticker']}")
print("""
  VALIDITY CHECK: utilities and energy should sit at the top, banks/consumer at
  the bottom. If that ordering holds, the measure is capturing something real.
  If a bank outranked a utility, something would be wrong.
""")

# =============================================================================
# 3. YEAR-ON-YEAR GROWTH
# =============================================================================
print("=" * 70)
print("3. YEAR-ON-YEAR GROWTH IN CCExposure (%)")
print("=" * 70)
g = fy.sort_values(["ticker","year"]).copy()
g["yoy_%"] = g.groupby("ticker")["cc_expo"].pct_change() * 100
piv = g.pivot_table(index="ticker", columns="year", values="yoy_%")
print(piv.round(1).to_string())
print("\n  mean growth by year (across firms):")
print(g.groupby("year")["yoy_%"].agg(["mean","median","count"]).round(1).to_string())
print("""
  Growth is noisier than levels -- a firm near zero can show +300% from one extra
  sentence. Trust growth rates for HIGH-exposure firms; treat low-exposure firms'
  growth as noise. (Same small-denominator problem as the regulatory measure.)
""")

# =============================================================================
# 4. TIME SERIES — aggregate trend
# =============================================================================
print("=" * 70)
print("4. AGGREGATE TIME SERIES (cross-firm mean per year)")
print("=" * 70)
ts = fy.groupby("year")[MEAS].mean().reset_index()
ts["n_firms"] = fy.groupby("year")["ticker"].nunique().values
print(ts.to_string(index=False))
print("""
  The paper finds exposure rising into ~2011, dipping around the 2012 Doha
  summit, then rising again after the 2015 Paris Agreement and 2016 US election.
  CAUTION: our firm count changes year to year, so a jump may reflect a change in
  WHICH firms are in the sample, not a real change in behaviour. Only compare
  years with a similar n_firms, or restrict to firms present in every year.
""")
bal = fy.groupby("ticker")["year"].nunique()
full = bal[bal == fy["year"].nunique()].index.tolist()
if len(full) >= 2:
    print(f"  balanced panel ({len(full)} firms present in all years): {full}")
    print(fy[fy["ticker"].isin(full)].groupby("year")["cc_expo"].mean().round(6).to_string())

# =============================================================================
# 5. INDUSTRY VARIATION  (paper Table IV)
# =============================================================================
print("\n" + "=" * 70)
print("5. INDUSTRY RANKING")
print("=" * 70)
ind = fy.groupby("industry")["cc_expo"].agg(["mean","std","count"]).sort_values(
    "mean", ascending=False)
print(ind.round(6).to_string())
print("""
  The paper's key point is NOT the ranking itself but the WITHIN-industry spread
  (the std column): if firms inside one industry differ a lot, then a firm-level
  measure is genuinely needed -- an industry average would not be enough.
""")

# =============================================================================
# 6. VARIANCE DECOMPOSITION  (paper Table VI) — the strongest validity argument
# =============================================================================
print("=" * 70)
print("6. VARIANCE DECOMPOSITION")
print("=" * 70)
def r2_of(groupcols, y="cc_expo", data=None):
    """R^2 from predicting y with group means = share of variance that group explains."""
    d = data.dropna(subset=[y])
    if d[y].std() == 0: return np.nan
    pred = d.groupby(groupcols)[y].transform("mean")
    ss_tot = ((d[y] - d[y].mean()) ** 2).sum()
    ss_res = ((d[y] - pred) ** 2).sum()
    return 1 - ss_res / ss_tot

for label, cols in [("year only", ["year"]),
                    ("industry only", ["industry"]),
                    ("industry x year", ["industry","year"]),
                    ("firm (ticker)", ["ticker"])]:
    v = r2_of(cols, data=fy)
    print(f"  {label:18s} explains {100*v:6.1f}% of variance in cc_expo")
ind_r2 = r2_of(["industry","year"], data=fy)
print(f"\n  => left UNEXPLAINED by industry x year: {100*(1-ind_r2):.1f}%")
print("""
  This is the paper's central validity claim: between 70% and 97% of the variation
  is at the FIRM level, not explained by industry, country, or time. If most
  variance were industry-level, you could just use an industry average and the
  firm-level measure would add nothing. A high unexplained share here means your
  measure is capturing real firm-specific differences.

  CAUTION with a small sample: with few firms per industry, 'firm' and 'industry'
  are nearly the same thing, so the firm R^2 is inflated. Report this alongside
  your firm count and treat it as indicative.
""")

fy.to_csv(os.path.join(OUTPUT_DIR, "phase6_firmyear_analysis.csv"), index=False)
prof.to_csv(os.path.join(OUTPUT_DIR, "phase6_firm_profiles.csv"), index=False)
print("saved -> outputs/phase6_firmyear_analysis.csv, outputs/phase6_firm_profiles.csv")
