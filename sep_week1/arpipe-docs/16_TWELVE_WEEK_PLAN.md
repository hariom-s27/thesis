# 16 — WEEK-BY-WEEK PLAN

The order is deliberate. The two decisions that cost the most money — **how
much OCR do we need** and **does segmentation work** — are answered in the
first month, before any money is committed.

---

## WEEK 0 — Unblock (do this now, it takes 2 hours)

Before anything else:

```powershell
winget install --exact --id tesseract-ocr.tesseract
winget install --exact --id QPDF.QPDF
```

And fix the four bugs the live run exposed (details in the step files):

| Bug | File | Fix |
|---|---|---|
| DVR ISIN treated as a separate company | `universe.py` | Collapse ISINs by CIN; prefer INE over IN9; flag DVR series |
| ISIN never extracted from any PDF | `verify.py` | Widen pattern to `IN[EF9CD]`, search cover + shareholder-info pages, log where |
| `supporters: 0` graded `high` | `verify.py` | Make supporter count a hard gate on confidence |
| Terminator matched a body word (`"trademarks"`) | `segment.py` | Require heading shape — short, own line, near top |

Plus two small ones:

| Bug | File | Fix |
|---|---|---|
| Windows backslash paths in the manifest | `store.py` | Store forward-slash paths relative to the dataset root |
| `configs/default.yaml` is never read | `cli.py` | Wire it, or delete it — a config file that lies is worse than none |

**Exit test:** re-run the 4 sample reports. KRBL FY2025 should now come out
`medium`, not `high`. Jain Irrigation should appear once, not twice.

---

## WEEKS 1-2 — Company list and discovery

**Do:**

- Wire the **BSE scrip master** (this is the biggest coverage gap)
- Build the master from NSE `EQUITY_L.csv` + `symbolchange.csv` + BSE master
- Chain symbol renames; key on ISIN; collapse DVR/multi-series lines
- Attach AMFI market-cap bands so every later result reads by company size
- Run discovery across NSE, BSE and screener for FY2010-25
- Produce a **coverage matrix**: company × year × source

**Also, in parallel:** hand-label **60 documents** from whatever you can
download manually. Not the full 300 — just enough to catch a catastrophically
wrong threshold before you spend a week tuning against imagination.

**Also on day 1:** email the university library about Prowess or Capitaline
access. The answer takes weeks; ask now, decide later.

**Exit test:**

> The coverage matrix exists. Every empty cell is classified as either
> "not listed that year" or "genuinely missing". No cell is unexplained.

---

## WEEKS 2-3 — Download everything and triage every page

**Do:**

- Rate-limited crawl into the hash store (this runs for days — start it early)
- ZIP unwrapping, `qpdf` repair, encrypted-PDF handling
- Run triage over **every page of every document**

**Exit test:**

> A real distribution of page classes, broken down by fiscal year and
> market-cap band. **The OCR budget is no longer a guess.**

**This is the cheapest, highest-information week in the plan.** A few CPU-hours
tells you exactly what the rest will cost.

---

## WEEKS 3-4 — The labelled evaluation set

**Do:**

- Sample **300 documents**, stratified:

```
era:          FY2010-13   /   FY2014-18   /   FY2019-25
cap band:     large       /   mid         /   small
doc kind:     digital     /   mixed       /   scanned
```

- Label the true MD&A start and end page in each, plus company and year
- Build the metric harness:

| Metric | Tells you |
|---|---|
| Exact start accuracy | The strict number |
| ±1 page start accuracy | Whether a row is usable |
| Boundary IoU | Over-reach and under-reach that start accuracy hides |
| Pk / WindowDiff | Comparable with published research |
| Precision per method | Which of S1-S5 won, and how often it was wrong |
| **Accuracy by supporter count** | **Does `supporters` actually predict correctness? The KRBL FY2025 case says check.** |

**Exit test:**

> A baseline number for the current segmenter on **every stratum**.

**Nothing after this point gets tuned without it.** Tuning without a labelled
set is guessing with extra steps.

---

## WEEKS 4-6 — Segmentation and verification to target

**Do:**

- Re-fit triage thresholds and heading/end-heading patterns against the
  labelled set
- Expand the end-heading list **from observed failures**, not from imagination
- **Prototype the ESGDoc heading-tree method** and compare against the flat
  arbiter
- Wire the LLM adjudication rung; measure what it buys per stratum against
  what it costs
- Implement identity, year and era verification
- Recalibrate the three tiers so the low tier is a size you can afford to review
- **Check the Jain Irrigation `ratio_cues: 0` question** — is the ratio table
  outside the MD&A heading, or are we trimming a page too early?

**Exit test:**

> ≥95% within ±1 page on born-digital.
> ≥85% within ±1 page on scanned.
> Low tier under 6%.

---

## WEEKS 6-8 — The OCR stack

**Do:**

- Bake off PaddleOCR-VL vs MinerU2.5 vs olmOCR-2 **on your own scanned pages**
- Score on **fact-level accuracy** (numbers, units, entities), not edit
  distance — see `13_HARD_PROBLEMS.md`
- Serve the winner behind vLLM or SGLang
- Wire the quality gate, the degeneracy guard, and document anchoring
- Pick the rung-3 provider and cap its share of pages
- Add script routing so Hindi pages are labelled and dropped, not mis-read

**Exit test:**

> Measured cost per OCR page, and measured fact accuracy on a held-out set of
> scanned financial pages.

**Note:** this is the first time OCR runs on real Indian data at all. Your live
run had `ocr_pages: 0` on every document. Budget extra time for surprises here.

---

## WEEKS 8-10 — Full run and audit

**Do:**

- Process the corpus — resumable, idempotent, stage by stage
- Exact and near-duplicate detection, including the **cross-year duplicate
  audit inside each company**
- Run the three dedup assertions:

```
one row per (sha256)          -> catches the DVR double-count
one row per (CIN, fy_end)     -> catches duplicate company keys
MinHash across adjacent years -> catches mis-filed years and boilerplate
```

- Publish the coverage and quality report: extractions per year, per cap band,
  per confidence tier, per winning method

**Exit test:**

> The dataset exists, and **every row can be traced to a page range in a
> hashed PDF**.

---

## WEEKS 10-12 — Review, harden, get the next section free

**Do:**

- Work the review queue. **Every correction becomes a pattern or a threshold**,
  never just a fixed file. Then re-run the affected documents.
- Add ratio-table extraction and XBRL reconciliation
- **Generalise:** the same machinery with a different heading list and
  end-heading list yields the Directors' Report, Corporate Governance, BRSR and
  risk factors at near-zero extra cost

**Exit test:**

> A maintained corpus with a documented refresh path for each new filing
> season.

That last bullet is the real payoff of keeping per-page text.

---

## The rule that makes the review week worth doing

> **Every correction must become a pattern, a threshold, or a test — never
> just a fixed file.**

If you fix one document by hand and change nothing else, you will fix the same
class of error 400 more times.

If you turn it into a terminator string or a threshold, you fix all 400 at once.

---

## Build the review tool in 30 minutes, not 3 days

**Spreadsheet, not a UI.**

One row per document:

| company | year | pdf link | proposed pages | first 200 words | TRUE start | TRUE end | note |
|---|---|---|---|---|---|---|---|

A reviewer types the true range. That is a 30-minute build versus a 3-day
build, and it produces the same labels.
