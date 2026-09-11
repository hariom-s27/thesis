# ARPipe — project rules for Claude

## What this project is

ARPipe collects annual reports of Indian listed companies (FY2010–FY2025) and
extracts the **Management Discussion & Analysis (MD&A)** section from each one.

Output per company-year: `mda.txt` plus an `mda.json` holding the evidence for
why we believe it.

Downstream use: climate-risk and disclosure text analysis. That means
**paragraph order and sentence integrity matter as much as coverage.**

---

## The one design idea that must never be broken

**Locate the MD&A section BEFORE running OCR. Then OCR only the pages inside
that span.**

The MD&A is about 4.3% of the pages — measured, not assumed. Across four real
filings: 319-page average document, 13.5-page average span.

Verified twice on real data: a run over 1,275 real pages found **65 pages
needing OCR and OCR'd zero of them**, because none fell inside a located span.

If a change would OCR pages outside the located span, that change is wrong.

---

## Second rule: page-level, never document-level

Never ask "is this document scanned?". Ask "can I read THIS PAGE?".

Real annual reports are mixed. Jain Irrigation FY2024 has 445 pages, ~57 of
them scanned, and zero of those fell inside the MD&A span. A document-level
router would have OCR'd 445 pages or skipped the document entirely.

Five page classes, not two:

```
digital       good text layer            -> read it, free
scanned       no text, one big image     -> OCR
hybrid        some text + big image      -> read text, OCR the image
broken-text   text exists but is garbage -> OCR, discard the text layer
vector-text   letters drawn as shapes    -> OCR
```

`broken-text` is the dangerous one. Every tool returns something; the something
is junk. Test: junk-character ratio above 2% means the text layer is dead.

---

## Third rule: failures produce rows, never absences

Every failure writes a manifest row with a `reason` code and tier `low`.

A missing row is invisible. A `low` row with a reason is a work item.

Never `try/except: pass`. Never skip a document silently.

---

## Fourth rule: agreement is the confidence measure

Five independent methods locate the section:

```
S1  PDF outline / bookmarks
S2  printed contents page (needs a folio->physical offset solver)
S3  typographic heading (font size + position)
S4  OCR-text heading (works on scans)
S5  Schedule V body cues (the workhorse)
```

When several agree, that agreement **is** the confidence. It costs nothing to
compute and it is the most honest signal we have.

`supporters == 0` can never be graded `high`.

---

## Fifth rule: green metrics are necessary, not sufficient

**Read the output text, not just the metrics about it.**

Four documents were graded `high` with score 0.99, `leaks: []`, and every
character-ratio band in range — and at least one of them has its paragraphs in
the wrong order.

Every quality check we have measures *what characters are present*. None of
them measures *whether the characters are in the right order*. Fix that gap
before trusting any tier.

---

## Performance rule that costs 128×

Never call `page.get_text("rawdict")` on an image page. It copies the embedded
image bytes into Python.

```
rawdict on a 29-page scanned PDF              29.4 seconds
dict with TEXTFLAGS_TEXT + get_image_info      0.23 seconds
```

Identical output. Use the second one.

---

## Repo layout

```
arpipe/
  cli.py         entry point, one command per stage
  models.py      dataclasses that move between stages
  universe.py    company master, ISIN keying, symbol chaining
  discover.py    NSE / BSE / screener adapters -> candidate URLs
  fetch.py       download, ZIP unwrap, qpdf repair, hash store
  triage.py      the five page classes, script, columns
  textlayer.py   XY-cut reading order, de-hyphenation, header stripping
  ocr.py         the ladder + quality gate + degeneracy guard
  segment.py     five location methods, arbiter, refine, trim
  patterns.py    all regexes (headings, terminators, cues, CIN, ISIN, FY)
  verify.py      identity, year, era rules, section QC, grading
  store.py       output tree, manifests, resumability
  pipeline.py    the locate-then-OCR ordering
configs/
  default.yaml   thresholds  (NOTE: not yet read by the code — bug 9)
tests/
  make_fixtures.py  synthetic annual reports
  test_pipeline.py
```

---

## Stages — each is a separate command, never merged

```
preflight   check tools, disk, LINK CAPABILITY, network
universe    build the company master
discover    find report URLs           ~17-36 hours, start it early
fetch       download PDFs              2-5 days
triage      classify every page        THE BUDGET GATE
extract     locate + OCR + verify + write
audit       dedup, coverage, quality
review      human queue -> patterns -> re-run
```

They must never be merged. The stages have different bottlenecks (network,
disk, CPU, GPU). Coupling them makes the GPU wait behind a politeness delay.

Every stage must be **resumable** and **idempotent**.

---

## Known state as of 9 September 2026

### Working, verified on real data

- 24 tests pass
- NSE company master downloads: 2,571 companies
- 4 real annual reports extracted (Jain Irrigation FY2024/25, KRBL FY2024/25)
- 1,275 real pages triaged; 65 flagged for OCR; **0 OCR'd** (correct)
- CIN verification matched at 100% name similarity on both companies
- Spans are correct — Jain FY2025 runs from `ANNEXURE V / MANAGEMENT
  DISCUSSION AND ANALYSIS` to its Cautionary Statement, exactly right
- Heading variation handled: `MANAGEMENT DISCUSSION AND ANALYSIS`,
  `Management Discussion and Analysis`, `Management Discussion & Analysis`
  all matched

### Open bugs — fix before any large run

**1. Reading order is broken (HIGHEST PRIORITY).**
Two-column pages are interleaved at paragraph level. Jain FY2025 `mda.txt`
opens with the fragment `"formulation, while posing direct threats to..."`
whose first half appears far later in the file. Passes every QC metric.
Likely cause: the gutter threshold is still the academic 5% rather than the
Indian-A4 2.5%, and/or gaps are measured on block boxes not line boxes.

**2. No metric can detect wrong order.** Word count, alpha_ratio, digit_ratio,
long_token_frac and leaks were all green on the scrambled document. Need
`orphan_start_frac` (paragraphs starting lowercase / mid-sentence).

**3. Tables and charts flatten into number-soup inside `mda.txt`.**
`looks_like_tables: false` on all four, because a few hundred table characters
are diluted inside a 15,000-word section. Needs **per-block** digit ratio, and
quarantining to a sidecar file.

**4. `supporters` ignored in grading.** KRBL FY2025 graded `high` with
`supporters: 0`.

**5. ISIN never extracted.** `isin_found` is null on all four. Identity runs on
one leg. Likely the pattern hardcodes `INE` and misses `IN9`/`INF`/`INC`/`IND`.

**6. DVR ISIN not collapsed.** Jain Irrigation is stored under `IN9175A01010`
(DVR line) instead of `INE175A01038` (ordinary). Both point at the same PDF, so
the panel double-counts. CIN does not catch it — it is correct for both lines.

**7. Terminator matched a body word.** `terminator_text: "trademarks"`.
Terminators must match a heading *shape*, not a string anywhere on the page.

**8. TOC method wins while wrong.** KRBL FY2025: TOC said 26–28, truth 33–39.
KRBL FY2024: TOC said 53–66, truth 27–33. The folio-offset solver fails
silently.

**9. Cross-drive symlink crashes the run.**
`ValueError: path is on mount 'D:', start on mount 'C:'` — `store.py` uses
`os.symlink` with a relative path. Needs an `os.link` → `os.symlink` →
`shutil.copy2` fallback, recording which one ran.

**10. Blob paths are relative to the cwd, not the store root.** The pipeline
only runs from `arpipe/` with `PYTHONPATH=..` set. Store paths relative to the
store root, forward slashes.

**11. `mda_path` is null** on a successful extraction in the latest run, while
an earlier manifest had it populated. Drop the duplicate — keep `path` — and
assert it is never null when `ok` is true.

**12. Ratio patterns are not tolerant.** KRBL's MD&A carries all 8 mandated
ratios; `ratio_cues` reported 7. Likely `"Debtors Turnover"` vs KRBL's
`"Debtor turnover ratio"` — singular. Allow singular/plural, optional "ratio"
suffix, case, hyphen-vs-space, optional "(%)".

**13. `configs/default.yaml` is not read by the code.**

### Answered, not a bug

**Jain's `ratio_cues: 0` is NOT a boundary bias.** Checked against the real
text: Jain's MD&A ends correctly at its Cautionary Statement, and its financial
section carries 14 tables — none of which is the mandated ratio table. The
ratios are genuinely outside the MD&A, probably in the Board's Report.

**Consequence:** era rules (FY≥2020 from the ratio table) must run over the
**full document**, not the extracted span.

### Never exercised on real data

- The entire OCR ladder (`ocr_pages: 0` everywhere; tesseract not installed)
- broken-text pages
- vector-text pages
- bilingual documents
- anything before FY2016
- ZIP unwrapping, qpdf repair, empty-password handling
- any BSE-only company (~3,000 small caps outside the master)

### Also not done

- LLM adjudication rung has an injection point but no provider
- No table extraction
- Every threshold is hand-set, validated only on synthetic documents plus four
  easy real ones

---

## Health bands from the four known-good documents

Treat drift outside these as suspicious — **but remember all four passed every
band while at least one had scrambled paragraph order.**

```
words per page      691 – 808
alpha_ratio       0.788 – 0.798
digit_ratio       0.021 – 0.026
avg_word_len       5.71 – 5.99
long_token_frac     0.0 on all four
leaks               []  on all four
mda as % of pages   4.3% average
frac_needing_ocr  0.006 – 0.128
```

---

## Rules for changes

### Do

- One change at a time, with a diff I can read
- Add a test for every fix, using real values from the four sample documents
- Move thresholds into config; never invent new hardcoded constants
- Log **where** a value came from, not just the value
- Write `low`-tier rows with reason codes when something fails
- **Read the extracted text**, not only the metrics about it
- Say when something is unverified

### Do not

- Refactor unrelated code "while you are here"
- Add `try/except` that swallows a failure
- Tune a threshold so a test passes — thresholds get re-fit against the
  labelled 300, not against 4 documents
- Skip documents that fail
- Write a new OCR engine (use PaddleOCR-VL / MinerU2.5 / Tesseract)
- Build a web UI where a CSV would do
- Process the full corpus to "test at scale" — 20 documents from FY2010–2014
  first
- Conclude a document is fine because its metrics are green

---

## Reading order — the rules

Most libraries sort text blocks by (y, x). On a two-column page that
**interleaves the columns**. MD&A and Corporate Governance are the two most
commonly two-column sections in an Indian annual report.

```
XY-cut: find the widest empty vertical band (the gutter), split, recurse,
        then split horizontally. Read LEFT fully, then RIGHT fully.
```

Two thresholds that matter, and both have burned us:

```
gutter fraction     2.5%   <- Indian A4 uses an 18-30pt gutter on a 595pt page
                              the ACADEMIC default of 5% detected 0 of 28
                              two-column pages; 2.5% detected 24 of 28
histogram bins      120    <- and measure on LINE boxes, not BLOCK boxes.
                              A two-column page is often just two blocks,
                              which carries no gutter signal at all.
```

A geometric cut can be wrong but can never *invent* text. A VLM can. For a
research corpus that difference matters.

---

## OCR ladder — the rules

```
rung 1   Tesseract                       free, CPU, English pages
rung 2   PaddleOCR-VL                    self-hosted, ~$190 per million pages
rung 3   Google Document AI or Gemini    ~$1,500/M, the 2-5% residue
```

**AWS Textract:** supports English, German, French, Spanish, Italian,
Portuguese only. **No Devanagari.** It cannot read a bilingual PSU report. At
~$1,500/M pages it is ~8× a self-hosted 1B model. Rung 3 only, never default.

**Quality gate between every rung.** Escalate on: word count far below page
area, mean confidence under 0.72, high non-alphanumeric ratio, tokens over 30
characters, or degeneracy.

**Degeneracy guard on every VLM output:**

```
output longer than 6x the anchor text   -> reject, escalate
8 or more identical consecutive lines   -> reject, escalate
```

A published Devanagari benchmark found one model producing output up to **71×**
the reference length on 2–3% of samples. This guard is not optional.

**Document anchoring:** always paste the PDF's own partial text into the VLM
prompt as a hint. It measurably reduces invented numbers.

**Token log-probabilities are not visual confidence.** A model's confidence in
`₹1,480.00` measures how likely that string is as *language*, not whether the
pixels say it.

---

## Numbers must carry provenance, not a score

FinCriticalED (859 financial pages, 9,481 annotated facts) found MinerU2.5 at
**95.71 ROUGE-1 but 54.05% monetary-unit accuracy**. A 0.12-point ROUGE-1
difference matched a 7.22-point fact-accuracy drop.

So for any extracted figure, record:

```
value, currency, unit (lakh/crore/million/'000), period, entity,
page, bbox, engine, validated_against
```

**The Indian unit trap:** the same table can be in ₹ lakh, ₹ crore, ₹ million
or ₹ '000, and the unit is printed once in small type. Wrong unit = 10× to 100×
error. **Reject any table where no unit can be found. Do not guess.**

---

## Verification — prove it from inside the document

Filenames and exchange metadata can be wrong. The document is the truth.

```
CIN     [LU] + 5 digits + 2 letters + 4 digits + 3 letters + 6 digits
        exact match = conclusive
        real examples:  L29120MH1986PLC042028  (Jain, Maharashtra, 1986)
                        L01111DL1993PLC052845  (KRBL, Delhi, 1993)

ISIN    IN[EF9CD] + 9 alphanumerics
        exact match = conclusive
        INE = ordinary company line;  IN9 = additional series, often DVR

Name    fuzzy, after stripping suffixes, against canonical + all former names
        >=88 accept, 72-88 flag, <72 reject

Year    weighted: "year ended 31st March, 2015" = 5
                  "2014-15"                     = 3
                  "as at 31 March 2015"         = 2
                  "FY2015"                      = 2
        below a total weight of 15, the year is thinly attested -> downgrade
```

**Era rules** — regulation dates a document independently of what it claims.
**Run these over the FULL DOCUMENT, not the extracted span** (see the Jain
finding above):

```
8 mandated financial ratios present  -> FY >= 2020
BRSR present                         -> FY >= 2023
"Ind AS"                             -> FY >= 2016
"Companies Act, 2013" / CSR          -> FY >= 2015
Business Responsibility Report       -> FY >= 2013
```

The 8 mandated ratios (match tolerantly — singular/plural, case, optional
"ratio" suffix):

```
Debtors Turnover        Current Ratio            Net Profit Margin
Inventory Turnover      Debt Equity Ratio        Return on Net Worth
Interest Coverage       Operating Profit Margin
```

---

## Grading

```
supporters >= 2  AND score >= 0.80  AND no leaks   -> high
supporters == 1  AND score >= 0.60  AND <=1 leak   -> medium
supporters == 0                                    -> medium at best
                                                      (low if score < 0.70)

any leak, identity unproven, word count out of band,
or orphan_start_frac above threshold                -> low
```

Targets: high tier ≥ 75%, low tier ≤ 6%.

---

## When you are unsure

Say so. Write the uncertainty into the manifest as a reason code and grade the
row `low`.

A wrong row that looks confident is worse than a `low` row that says "I do not
know". At 40,000 documents, silent errors are the only errors that matter.
