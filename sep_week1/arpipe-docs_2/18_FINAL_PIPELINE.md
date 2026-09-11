# 18 — THE FINAL PIPELINE (PRODUCTION RUN DESIGN)

**This is the answer to "give me the pipeline for the final code."**

Read `17_LIVE_RUN_REVIEW.md` first. Fix the five bugs. Then follow this.

---

## 18.1 — The shape

Seven stages. Each is a **separate command**. Each reads and writes a shared
manifest. Each is **resumable** and **idempotent** — run it twice, nothing
breaks, nothing is done twice.

```
  STAGE 0   preflight     check tools, disk, network        minutes
  STAGE 1   universe      company master                    minutes
  STAGE 2   discover      find URLs                         ~17 hours
  STAGE 3   fetch         download PDFs                     2-5 days
  STAGE 4   triage        classify every page               4-12 hours
  STAGE 5   extract       locate + OCR + verify + write      3-7 days
  STAGE 6   audit         dedup, coverage, quality report    minutes
  STAGE 7   review        human queue -> patterns -> re-run  2 weeks
```

**Never merge stages.** The GPU must not wait behind a politeness delay.

---

## 18.2 — Run order and gates

```
                         STAGE 0
                        preflight
                            |
                    tools present?
                    disk >= 1 TB?
                    NSE reachable?
                            |
                           YES
                            |
                            v
                         STAGE 1
                        universe
                            |
                +-----------+-----------+
                |                       |
       companies.csv              GATE 1
       ~5,900 rows                one row per CIN?
                |                 DVR collapsed?
                +-----------+-----------+
                            |
                            v
                         STAGE 2
                        discover          <-- START THIS ON DAY 1
                            |                 it runs for ~17 hours
                +-----------+-----------+
                |                       |
        reports.jsonl              GATE 2
        ~40,000 rows               coverage matrix built?
                |                  every gap explained?
                +-----------+-----------+
                            |
                            v
                         STAGE 3
                          fetch           <-- 2-5 days
                            |
                +-----------+-----------+
                |                       |
         store/blobs/              GATE 3
         ~500 GB - 1 TB            re-run downloads nothing?
                |                  failure rate < 5%?
                +-----------+-----------+
                            |
                            v
                         STAGE 4
                         triage           <-- THE BUDGET GATE
                            |
                +-----------+-----------+
                |                       |
       page class table            GATE 4
       by year x cap band          OCR page count known?
                |                  is it affordable?
                +-----------+-----------+
                            |
                    +-------+-------+
                    |               |
              affordable      too expensive
                    |               |
                    v               v
                 STAGE 5      narrow the window
                extract       (see 15_COST_AND_TIME 15.6)
                    |
        +-----------+-----------+
        |                       |
   mda.txt x 40,000        GATE 5
   manifest.jsonl          high tier >= 75%?
        |                  low tier <= 6%?
        +-----------+-----------+
                    |
                    v
                 STAGE 6
                  audit
                    |
        +-----------+-----------+
        |                       |
  coverage report          GATE 6
  quality report           one row per (CIN, year)?
        |                  no cross-year duplicates?
        +-----------+-----------+
                    |
                    v
                 STAGE 7
                 review
                    |
              corrections
                    |
                    v
            re-run STAGE 5
            on affected docs
```

---

## 18.3 — STAGE 0: preflight

**New stage. Add it.** Five minutes of checking saves days of a run dying at
3am on day four.

```bash
python -m arpipe.cli preflight
```

What it must check:

| Check | Fail loudly if |
|---|---|
| `tesseract --version` | missing → the OCR ladder silently does nothing |
| `qpdf --version` | missing → every damaged PDF is lost |
| Tesseract language packs | `eng` missing |
| Free disk on the store volume | under 1 TB |
| NSE reachable, cookies obtainable | 401 or timeout |
| BSE reachable with headers | 403 |
| Write permission on `store/` and `dataset/` | read-only |
| Python package versions | pinned versions do not match |
| GPU present and VRAM (if using rung 2) | under 4 GB |

Output a one-page green/red table. Refuse to proceed on any red.

---

## 18.4 — STAGE 1: universe

```bash
python -m arpipe.cli universe \
    --nse-equity   EQUITY_L.csv \
    --nse-changes  symbolchange.csv \
    --bse-master   bse_scrips.csv \
    --amfi-bands   amfi_categorisation.csv \
    --out          companies.csv
```

**Output columns:**

```
company_id        primary ISIN (INE preferred over IN9)
cin               if known from a prior run, else blank
canonical_name
former_names      pipe-separated
nse_symbol
nse_aliases       pipe-separated, from the chained symbolchange file
bse_scrip
alternate_isins   pipe-separated  <- DVR and other series live here
series_type       ordinary | dvr | partly_paid
exchange          nse | bse | both
cap_band          large | mid | small | micro
first_listed
delisted_on       blank if active
```

**GATE 1 — do not proceed unless:**

```
[ ] Row count is ~5,900 (NSE+BSE) or ~2,571 (NSE only) - and you know which
[ ] Every company_id is unique
[ ] No two rows share a CIN
[ ] Jain Irrigation appears ONCE, with IN9175A01010 in alternate_isins
[ ] Companies delisted mid-window are present, not dropped
```

---

## 18.5 — STAGE 2: discover

```bash
python -m arpipe.cli discover \
    --companies    companies.csv \
    --from-year    2010 \
    --to-year      2025 \
    --sources      nse,bse,screener \
    --rate         1.5 \
    --out          reports.jsonl \
    --resume
```

**Start this on day 1.** It is the long pole. ~40,000 lookups at 1.5s is
**17 hours minimum**, and you should expect 24-36 hours with retries.

**Do all your threshold work while it runs.**

**Row shape** (this matches what you already produce):

```json
{
  "company_id": "INE001B01026",
  "fy_end": 2025,
  "source": "nse",
  "url": "https://nsearchives.nseindia.com/annual_reports/AR_27875_KRBL_2024_2025_A_34429015_29082025160935.pdf",
  "discovered_at": "2026-09-09T20:50:45Z",
  "declared_name": "KRBL Limited",
  "declared_fy": "2024-2025",
  "priority": 10
}
```

**Add two fields:**

```json
"filename_symbol": "KRBL",        <- parsed from the URL
"filename_years":  "2024_2025",   <- parsed from the URL
```

Then assert they match `declared_name`'s symbol and `declared_fy`. A mismatch
is a mis-filed attachment, caught before you download it.

**Parse the filename by pattern, not by underscore position.** FY2024 URLs and
FY2025 URLs have different token counts.

**GATE 2 — do not proceed unless:**

```
[ ] Coverage matrix built: company x year x source
[ ] Every empty cell classified: "not listed that year" or "genuinely missing"
[ ] Missing-rate under 15% for FY2015-2025
[ ] You have accepted the missing-rate for FY2010-2014 (it will be worse)
```

---

## 18.6 — STAGE 3: fetch

```bash
python -m arpipe.cli fetch \
    --manifest  reports.jsonl \
    --root      store \
    --workers   6 \
    --rate      1.5 \
    --max-mb    400 \
    --resume
```

**Runs for 2-5 days.** Let it. Check on it once a day.

Per file:

```
   download (stream to disk, cap at --max-mb)
        |
   is it a ZIP? --YES--> unwrap, keep largest PDF, log the rest
        |
   opens as PDF? --NO--> qpdf repair --> still no? mark failed
        |
   encrypted? --YES--> try empty password
        |
   sha256 the bytes
        |
   already in store/blobs/? --YES--> skip write, just link
        |
   write blob, hardlink into dataset tree
        |
   append to fetch manifest
```

**GATE 3 — do not proceed unless:**

```
[ ] Re-running fetch downloads NOTHING
[ ] Hard-failure rate under 5%
[ ] Free disk still above 100 GB
[ ] Failure log reviewed - are the failures a pattern or random?
```

---

## 18.7 — STAGE 4: triage — THE BUDGET GATE

```bash
python -m arpipe.cli triage \
    --root     store \
    --workers  all \
    --out      triage.parquet \
    --resume
```

**This is the cheapest, most important stage.** A few CPU-hours turns the OCR
budget from a guess into a number.

**No rendering. Object model only.** Never `get_text("rawdict")` on an
image page — 29.4s vs 0.23s for identical output.

**Output, one row per page:**

```
sha256, page_index, page_class, char_count, image_area_frac,
junk_char_ratio, path_count, script, n_columns, est_dpi
```

**Then produce this table and look at it before spending anything:**

```
                  digital  scanned  hybrid  broken  vector  blank
FY2010-2013         ?        ?        ?       ?       ?       ?
FY2014-2018         ?        ?        ?       ?       ?       ?
FY2019-2025         ?        ?        ?       ?       ?       ?

large cap           ?        ?        ?       ?       ?       ?
mid cap             ?        ?        ?       ?       ?       ?
small cap           ?        ?        ?       ?       ?       ?
```

**GATE 4 — the money decision:**

```
estimated_ocr_pages = (pages needing OCR) x (fraction inside an MD&A span)
                    ~ use 4.3% as the span fraction, measured live

estimated_cost = estimated_ocr_pages / 1e6 x $190     (self-hosted VLM)
```

```
[ ] Is the estimated cost affordable?
[ ] If not: narrow the year window (see 15_COST_AND_TIME 15.6)
[ ] Is the scanned share in FY2010-2013 what you expected?
    If it is 60%+, the early years are a project of their own.
```

**Do not skip this gate.** It is the only point where you can still change
scope cheaply.

---

## 18.8 — STAGE 5: extract — the core

```bash
python -m arpipe.cli extract \
    --root       store \
    --companies  companies.csv \
    --triage     triage.parquet \
    --out        dataset \
    --vlm-url    http://gpu-box:8000 \
    --vlm-model  PaddlePaddle/PaddleOCR-VL \
    --ocr-budget 500000 \
    --resume
```

**The inner order — this is the whole design:**

```
   1. load triage for this document
           |
   2. read the FREE pages (digital) via textlayer
           |
   3. LOCATE the MD&A using S1-S5 + arbiter
           |         (no OCR spent yet)
           |
      found?  --NO--> if the doc is mostly scanned:
           |             OCR front matter + 1-in-6 sample
           |             retry locate
           |             still no? -> tier LOW, stop
          YES
           |
   4. is any page in the span not readable?
           |
          YES -> OCR ladder, ONLY those pages
           |       rung 1 -> gate -> rung 2 -> gate -> rung 3
           |       degeneracy guard on every VLM output
           |
   5. clean: XY-cut order, strip furniture, de-hyphenate
           |
   6. RE-TRIM both boundaries on the now-good text
           |         <-- the step people skip and regret
           |
   7. verify: CIN, ISIN, name, year, era rules
           |
   8. QC: leaks, digit ratio, word count, words-per-page,
          long tokens, supporter count
           |
   9. grade: high / medium / low
           |
  10. write mda.txt, mda.json, document.json, pages/*.txt
      append to manifest.jsonl
```

**Batching for the GPU:** collect OCR page requests across many documents into
batches of 8-32 before hitting the VLM. One page at a time wastes the GPU.

**Budget enforcement:** `--ocr-budget` is a hard cap on OCR pages for the run.
When it is hit, remaining documents are written as tier `low` with reason
`ocr_budget_exhausted` — never silently skipped.

**GATE 5 — do not proceed unless:**

```
[ ] high tier >= 75%
[ ] low tier <= 6%
[ ] No document has confidence=high with supporters=0
[ ] words-per-page between 250 and 1200 on >= 95% of high tier
[ ] leaks == [] on 100% of high tier
```

---

## 18.9 — STAGE 6: audit

```bash
python -m arpipe.cli audit \
    --out      dataset \
    --report   audit_report.html
```

**Six assertions that must pass:**

```
1.  One row per sha256
        two rows, same hash, different company_id  ->  DVR double-count

2.  One row per (CIN, fy_end)
        more than one  ->  duplicate company key

3.  No cross-year near-duplicates within a company
        MinHash + LSH over mda.txt shingles
        near-identical adjacent years  ->  mis-filed year, or boilerplate

4.  Every mda.txt traces to a page range in a hashed PDF
        span + sha256 + page count all present and consistent

5.  Era rules consistent
        no FY2013 document containing the FY2020 ratio table

6.  No confidence=high row with supporters=0
```

**Six reports to publish:**

```
- Coverage:      extractions per year x cap band x exchange
- Quality:       tier distribution per year x doc kind
- Method:        which of S1-S5 won, and per-method precision
- Cost:          OCR pages used per rung, total spend
- Failures:      what failed, grouped by reason
- Gaps:          company-years with no source found, split by cause
```

---

## 18.10 — STAGE 7: review

```bash
python -m arpipe.cli review-queue \
    --out       dataset \
    --tier      low \
    --format    csv \
    --out-file  review_queue.csv
```

**Spreadsheet, not a UI.** One row per document:

| company | year | pdf path | proposed pages | first 200 words | last 200 words | TRUE start | TRUE end | reason code |

A reviewer types the true range and a reason code.

**Then — and this is the rule that makes the week worth it:**

> **Every correction becomes a pattern, a threshold, or a test. Never just a
> fixed file.**

```bash
python -m arpipe.cli review-apply \
    --corrections review_queue_done.csv \
    --patterns    arpipe/patterns.py \
    --rerun
```

If you fix one document by hand and change nothing else, you will fix the same
class of error 400 more times. If you turn it into a terminator string or a
threshold, you fix all 400 at once.

---

## 18.11 — Config: one file, actually read

Right now `configs/default.yaml` exists and the code ignores it. **A config
file that lies is worse than no config file.** Wire it or delete it.

```yaml
run:
  from_year: 2010
  to_year:   2025
  exchanges: [nse, bse]
  rate_per_host_seconds: 1.5

triage:
  min_chars_digital:      120      # below this, suspect a scan
  image_area_scan_frac:   0.55     # above this, it is a scan
  junk_char_ratio_max:    0.02     # above this, text layer is broken
  vector_path_count_min:  300      # above this, letters are drawn as shapes
  gutter_frac_min:        0.025    # INDIAN reports, not academic papers
  gutter_histogram_bins:  120
  dpi_min:                200
  dpi_max:                400

segment:
  index_sample_every:     6        # 1-in-6 page sample when scanned
  front_matter_pages:     14
  forward_walk_max:       15       # hard cap so it cannot run away
  arbiter_agreement_bonus: 0.15
  agreement_window_pages:  2
  llm_when_score_below:    0.55

ocr:
  rung1: tesseract
  rung2: paddleocr-vl
  rung3: google-documentai
  gate_confidence_min:     0.72
  gate_long_token_chars:   30
  degeneracy_length_mult:  6.0     # reject if > 6x the anchor text
  degeneracy_repeat_lines: 8       # reject if 8+ identical lines
  budget_pages:            500000

verify:
  name_accept:             88
  name_flag:               72
  fy_weight_min:           15      # below this, year is thinly attested
  isin_pattern:            "IN[EF9CD][A-Z0-9]{9}"

grade:
  high:   { supporters: 2, score: 0.80, leaks: 0 }
  medium: { supporters: 1, score: 0.60, leaks: 1 }
  # supporters == 0 can never be high

qc:
  words_per_page_min:      250
  words_per_page_max:      1200
  digit_ratio_max:         0.25
  alpha_ratio_min:         0.65
  min_words:               250
  max_words:               40000

store:
  keep_per_page_text:      true    # doubles text disk, saves the next section
  path_style:              posix   # forward slashes, relative to root
```

**Every one of these numbers is currently a guess.** They get re-fit against
the labelled 300 in weeks 3-6. Until then, treat the config as a hypothesis,
not a setting.

---

## 18.12 — Failure policy

| Failure | Policy |
|---|---|
| URL 404 | Retry once after 24h, then mark `source_dead` |
| PDF will not open after qpdf | Mark `unreadable`, keep the bytes |
| No MD&A found, document is digital | Tier `low`, reason `not_found_digital` |
| No MD&A found, document is scanned | Tier `low`, reason `not_found_scanned` |
| OCR budget exhausted | Tier `low`, reason `ocr_budget_exhausted` — **never silently skip** |
| Degeneracy guard tripped 3× on one page | Tier `low`, reason `ocr_degenerate` |
| Company or year unverified | Tier `low`, reason `identity_unproven` |
| Era rule conflict | Tier `low`, reason `era_conflict` |

**The rule:** every failure produces a **row with a reason**, never an absence.
A missing row is invisible. A `low` row with a reason code is a work item.

---

## 18.13 — What to run first, in order

```
DAY 1        Stage 0 preflight. Install tesseract + qpdf.
             Fix the 5 bugs in 17_LIVE_RUN_REVIEW.md.
             Email the library about Prowess/Capitaline.

DAY 1        Stage 1 universe, WITH the BSE master.
             Gate 1.

DAY 1 pm     Stage 2 discover. START IT AND LEAVE IT.
             It runs ~24 hours.

DAY 2-3      While discover runs: hand-label 60 documents.

DAY 3        Gate 2. Stage 3 fetch. START IT AND LEAVE IT.
             It runs 2-5 days.

DAY 4-7      While fetch runs: build the metric harness.

DAY 8        Gate 3. Stage 4 triage. 4-12 hours.

DAY 8        GATE 4 - THE MONEY DECISION.
             Look at the page-class table. Decide the scope.

DAY 9        Pick 20 documents from FY2010-2014 - the SCANNED era.
             Run extract on just those.
             This is the FIRST REAL TEST of the OCR path.

WEEK 3-4     Label the full 300. Re-fit every threshold.

WEEK 5-6     Segmentation to target. Prototype ESGDoc tree method.

WEEK 6-8     OCR bake-off on real scanned pages.

WEEK 8-10    Stage 5 full run. Stage 6 audit.

WEEK 10-12   Stage 7 review. Then generalise to the next section.
```

---

## 18.14 — The single most important line in this document

> **After Stage 4 triage, stop and look at the numbers before you spend
> anything.**

That gate is the only point where changing scope is still cheap. Everything
after it is committed.
