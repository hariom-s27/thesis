# 23 — REVIEW OF THE ACTUAL EXTRACTED TEXT

**This file reviews the real `mda.txt` output, not the metrics about it.**

Every finding below is evidence you can see with your own eyes in the text.

---

## 23.1 — What the run produced

```
triage:  { "documents": { "digital": 3, "mixed": 1, "scanned": 0 },
           "pages": 1275, "pages_needing_ocr": 65, "ocr_fraction": 0.051 }

extract: ok=4/4

audit:   { "documents": 4, "ok": 4,
           "by_confidence": { "high": 4 },
           "by_method": { "heading+refined+trimmed": 3,
                          "toc+refined+trimmed": 1 },
           "mean_words": 9785.2, "ocr_pages_total": 0 }
```

**65 pages needed OCR. Zero were OCR'd.** Locate-then-OCR working, confirmed
a second time.

---

## 23.2 — FINDING 1: THE COLUMN ORDER IS BROKEN

**This is the most important finding in the whole project so far.**

The XY-cut reading order is **not working** on Jain Irrigation FY2025. Column 1
and column 2 are being interleaved at the paragraph level.

### The evidence — read this

Here is the very start of the extracted `mda.txt`:

```
ANNEXURE V
MANAGEMENT DISCUSSION AND ANALYSIS

GLOBAL ECONOMY

formulation, while posing direct threats to agricultural
productivity, inflation management, and long-term
economic output.

As per its latest assessment, the International Monetary
Fund (IMF) projects global growth at 3.2 per cent in
2024 and 2025...
```

**"formulation, while posing direct threats to..."** is a sentence fragment. It
begins mid-sentence. It is the *second half* of a sentence whose first half
appears **much later** in the same file:

```
...the RBI emphasized that
frequent weather shocks triggered by climate change
present persistent challenges to monetary policy
```

Put them together and you get the real sentence:

> "…present persistent challenges to monetary policy **formulation, while
> posing direct threats to agricultural productivity, inflation management,
> and long-term economic output.**"

The bottom of one column has been printed at the **top of the document**,
hundreds of lines away from where it belongs.

### It happens again, and again

Second example. These two paragraphs are obviously consecutive — same subject,
same voice:

```
At Jain Irrigation Systems Ltd., we recognize the
critical implications of climate change...
```
```
Our micro-irrigation systems-which include drip and
sprinkler solutions-enable precise and efficient water
usage...
```

But in the extracted file, **this paragraph sits between them**:

```
The global financial system displayed continued
resilience amidst moderation in economic activity, rising
policy uncertainty and elevated geopolitical tensions...
(Source - RBI, Financial Stability Report Dec 2024)
```

That is a paragraph from the *other column*, spliced into the middle of a
two-paragraph thought.

Third example, in the segment tables:

```
i)	 Hi Tech Agri Input Products Division:
Revenue from sales of Company's Hi-Tech Agri Input
Products has decreased by 3.6%...
```

appears **after** the raw-material and other-expenses tables, not with the
other segment discussion. The page is three-column-ish (table + prose) and the
cut is wrong.

### Why this is so dangerous

Look at what the QC metrics said about this exact document:

```
"confidence":       "high"
"score":            0.99
"leaks":            []
"alpha_ratio":      0.798
"digit_ratio":      0.021
"long_token_frac":  0.0
"n_words":          15195
"words_per_page":   691
```

**Every single metric is green.** Word count is right. Character ratios are
right. No leakage. No long tokens.

And the text is **out of order**.

> Every quality check we have measures *what characters are present*.
> None of them measures *whether the characters are in the right order*.

For a research corpus this is worse than a scanning error. A garbled OCR page
is obviously broken and gets caught. Interleaved columns read fluently, pass
every gate, and quietly corrupt:

- any sentence-level sentiment analysis
- any bigram or n-gram dictionary count (Sautner, Li et al., ClimateBERT — all
  of them)
- any transformer embedding, which is order-sensitive by construction
- any LLM asked to summarise or classify a paragraph

### Why the word-count test did not catch it

The document `07_STEP5_READ_FREE_TEXT.md` proposes this test:

> "Both must have the same word count. But naive order must interleave
> sentences and XY-cut must not."

The word count **is** the same — that is exactly the point. Interleaving
preserves every word. The test as written can only detect *missing* text, not
*misplaced* text.

### The fix — three parts

**Part 1: a real order test.** Sentence-continuity, not word count.

```
Count "orphan starts": lines that begin with a lowercase word or a comma,
   where the previous line ended with a complete sentence (. ! ?).

In correctly ordered prose this is near zero.
In the Jain FY2025 output it is high.
```

Add `orphan_start_frac` to QC. Set the band from a document you have manually
confirmed is correct. Anything above it goes to `medium` or `low`.

**Part 2: find out why XY-cut is not firing.**

Likely causes, in order of probability:

| Cause | How to check |
|---|---|
| The gutter threshold is still the academic 5%, not 2.5% | print the detected column count per page |
| Column detection runs on **block** boxes, not **line** boxes | a two-column page will report `n_columns: 1` |
| The page has a full-width heading on top, so the first cut is horizontal and the vertical cut never happens | log the cut sequence |
| XY-cut is implemented but not actually called on this path | grep for the call site |

The manifest already carries a column count from triage. **Print it for the
Jain FY2025 MD&A pages.** If it says 1 column on a visibly two-column page, you
have your answer in thirty seconds.

**Part 3: re-check the KRBL output.** KRBL FY2024's text reads more cleanly —
its layout is different. So this may be per-document, not universal. Measure it
per document, do not assume.

---

## 23.3 — FINDING 2: THE JAIN RATIO QUESTION IS ANSWERED

`09_STEP7` and `17_LIVE_RUN_REVIEW` flagged this:

```
KRBL FY2024: ratio_cues = 7
KRBL FY2025: ratio_cues = 7
Jain FY2025: ratio_cues = 0     <- why?
Jain FY2024: ratio_cues = 0
```

Three possibilities were listed. **The extracted text settles it.**

### The answer: (b) — not a boundary bias. Good news.

Jain Irrigation's MD&A ends with:

```
Disclaimer

The Management cautions that certain statements made
herein are forward-looking and represent directional
guidance or estimates based on current expectations...
```

That is the **Cautionary Statement** — the canonical, mandated last element of
an Indian MD&A. The section is **complete**. The span is not short.

And Jain's financial discussion (its section 6, "Analysis of the Standalone
financial performance") contains fourteen tables — Net Sales, Raw material
consumption, Other Expenses, Employee Benefit Expenses, Finance Costs, Fixed
Assets, Investments, Inventories, Trade Receivables, Short Term Loans, Current
Liabilities, Long Term Borrowing, Shareholder's Fund, Dividend.

**None of them is the mandated key-financial-ratios table.** No Debtors
Turnover. No Interest Coverage. No Debt Equity Ratio. No Return on Net Worth.

So: the ratio table is genuinely not inside Jain's MD&A. It is either in the
Board's Report or omitted.

### What this means

| Conclusion | Action |
|---|---|
| **There is no systematic boundary bias.** The span is correct. | Relief. This was the scariest of the three options. |
| **`ratio_cues` is NOT a reliable era signal.** | Demote it. Search the whole document for the era rule, not just the span. |
| Jain may have a disclosure gap | Interesting on its own. Compare against their XBRL filing. |

**Change to make:** era rules (FY≥2020 from the ratio table) must run over the
**full document text**, not the extracted span. Otherwise a company that files
its ratios in the Board's Report gets wrongly dated.

---

## 23.4 — FINDING 3: THE RATIO PATTERN MISSES ONE

KRBL's MD&A carries a section literally headed **"Key Financial Ratios"**, and
it contains all eight mandated items:

```
Operating profit margin (%)        <- mandated
Net profit margin (%)              <- mandated
Return on net worth (%)            <- mandated
Return on Capital Employed (%)     (extra, not mandated)
Inventory turnover ratio           <- mandated
Debtor turnover ratio              <- mandated
Debt Equity ratio                  <- mandated
Current ratio                      <- mandated
Interest Coverage ratio            <- mandated
```

That is **8 of 8**. But `ratio_cues` reported **7**.

### The likely culprit: singular vs plural

```
SEBI Schedule V says:   "Debtors Turnover"
KRBL writes:            "Debtor turnover ratio"
                            ^ no 's'
```

If the pattern is a literal `Debtors Turnover`, it misses.

**Fix:** make every ratio pattern tolerant of:

```
- singular / plural       Debtor(s)?
- "ratio" suffix present or absent
- case                    Return on net worth  /  Return on Net Worth
- hyphen / space          Debt Equity  /  Debt-Equity
- the "(%)" suffix
```

Small fix, but this is a cue used for both segmentation (S5) and era dating.
A 12.5% miss rate on a signal you rely on twice is worth twenty minutes.

---

## 23.5 — FINDING 4: TABLES AND CHARTS ARE FLATTENED INTO GARBAGE

`looks_like_tables: false` is reported on all four documents. Look at what is
actually in the text.

**A bar chart's axis labels, dumped as a word list:**

```
Gross Value Added by Agriculture and Allied sectors
(US $ billion) (at constant 2011-12 prices)
350.00
300.00
250.00
283.68
200.00
267.90
276.37
279.00
259.71
288.78
239.73
150.00
100.00
50.00
0.00
FY 18
FY 19
FY 20
FY 21
FY 22
FY 24
FY 23
```

Note `FY 24` before `FY 23` — the axis labels themselves are out of order,
which is the same reading-order bug showing up in a different guise.

**Another chart, from the KRBL text:**

```
513.10
514.42 515.53
517.63
519.64 521.35
-4.53
-5.22
-5.82
```

Numbers with no labels at all. Meaningless.

**A financial table, headers detached from values:**

```
Particulars 31st Mar
31st Mar
Change
absolute
Change
%
Employees
benefit
expenses
3,525.13
3,218.21
306.92
9.54%
```

The reader cannot tell which year `3,525.13` belongs to.

### Why `digit_ratio` did not catch it

```
digit_ratio: 0.021 - 0.026
```

The threshold is 0.25. But these tables are a few hundred characters inside a
15,000-word section. **The signal is diluted below detection.**

A document-level digit ratio cannot find a table. You need a **per-page** or
**per-block** digit ratio.

### What to do about it — a decision, not a bug

| Option | Effect | Recommendation |
|---|---|---|
| Leave the numbers inline | Corpus contains number-soup that pollutes any text model | **No** |
| **Detect table/chart blocks and strip them from `mda.txt`, saving them separately as `mda_tables.json`** | Clean prose for NLP; tables preserved for later | **Yes** |
| Strip and discard | Simple, loses the ratio table which is a real research variable | No |
| Try to reconstruct the tables now | Correct, but that is the v2 table-extraction project | Later |

**Recommendation for v1:** detect and *quarantine*. A block with digit ratio
above ~0.4 and fewer than ~6 words per line is a table or chart. Move it to a
sidecar file, note its page in `mda.json`, and keep `mda.txt` as prose.

Your downstream work is climate-language analysis. Number-soup in the middle of
the text is pure noise for that, and it inflates `n_words`.

---

## 23.6 — FINDING 5: TWO NEW BUGS FROM RUNNING IT

### Bug 6 — `store.py` uses a cross-drive symlink

```
ValueError: path is on mount 'D:', start on mount 'C:'
```

`os.symlink` with a relative path fails when `--out` is on a different volume
from `store/`. On Windows, symlinks also need Developer Mode or admin rights.

The design docs say **hardlink**. Hardlinks also fail across volumes, but for a
different reason.

**Fix — a three-step fallback:**

```
try   os.link(blob, dest)        # hardlink, free, same volume
except OSError:
   try   os.symlink(...)          # needs privileges on Windows
   except (OSError, ValueError):
         shutil.copy2(blob, dest) # always works, costs disk
         log "copied instead of linked: <reason>"
```

And **record which one happened** in `document.json`. Otherwise a run that
silently copied 40,000 PDFs will double your disk and you will not know why.

### Bug 7 — `mda_path` is null

The fresh `mda.json` says:

```json
"mda_path": null
```

but the earlier manifest had it populated. Something regressed between runs, or
`mda_path` is only set on one code path.

`17_LIVE_RUN_REVIEW.md` recommended dropping one of the duplicate
`mda_path` / `path` fields. **Drop `mda_path`, keep `path`** — and add a test
asserting the kept field is never null on a successful extraction.

### Bug 8 — the run only works from one directory

```
must run from  arpipe/  with  PYTHONPATH=..
```

because the package imports as `arpipe` from the parent, but stored blob paths
are relative to `arpipe/`.

Blob paths in the manifest are stored **relative to the wrong root**:

```json
"path": "live_store\\blobs\\47\\74\\4774...610.pdf"
```

That is relative to the current working directory, not to the store root.

**Fix:** store blob paths relative to **the store root**, and resolve them
against `--root` at read time. Then the dataset is portable and the command
works from anywhere. (Same forward-slash fix as `12_STEP10_STORE.md`.)

---

## 23.7 — WHAT THE TEXT DOES PROVE

Not everything is bad. Three things are confirmed working, from the text
itself:

**1. The span boundaries are right.**
Jain FY2025 starts at `ANNEXURE V / MANAGEMENT DISCUSSION AND ANALYSIS` and
ends at the Cautionary Statement. That is exactly the section, start to end. No
Corporate Governance leakage, no auditor's report.

**2. This is genuinely useful research text.**
The Jain MD&A contains, in its own words:

> "According to the RBI, in the absence of adequate climate mitigation efforts,
> India's long-term economic output could decline by as much as 9% by 2050"

> "Climate change also affects the natural rate of interest and may undermine
> the effectiveness of monetary policy transmission over time."

> a full **Climate Factor / Key Issues / Solutions** table covering heat waves,
> cold waves, drought, soil degradation and methane emissions

That is exactly the climate-exposure language the thesis is about. The pipeline
is surfacing real signal.

**3. Heading variation is handled.**
`ANNEXURE V / MANAGEMENT DISCUSSION AND ANALYSIS` — the heading is preceded by
an annexure label. The pattern still matched. That is the tolerant-pattern
design working.

---

## 23.8 — REVISED PRIORITY ORDER

The reading-order bug outranks everything previously listed.

| Rank | Issue | Why |
|---|---|---|
| **1** | **Column interleaving** | Silently corrupts every downstream NLP task. Passes every existing gate. |
| **2** | Add an order-quality metric (`orphan_start_frac`) | Without it you cannot even measure #1 |
| 3 | Quarantine tables/charts out of `mda.txt` | Number-soup pollutes the corpus |
| 4 | Supporter gate (Bug 3) | Grading is wrong at scale |
| 5 | Blob paths relative to store root (Bug 8) | Dataset is not portable |
| 6 | Link fallback (Bug 6) | Run dies on a different drive |
| 7 | ISIN extraction (Bug 2) | Identity on one leg |
| 8 | DVR collapsing (Bug 1) | Panel double-counts |
| 9 | Ratio pattern tolerance | 1 in 8 missed |
| 10 | Era rules over full document, not span | The Jain finding |
| 11 | Terminator heading shape (Bug 4) | — |
| 12 | TOC offset gate (Bug 5) | — |

---

## 23.9 — THE ONE-LINE READ

> **The pipeline found the right pages. It is not yet delivering the right
> text.** Four documents graded `high` with score 0.99, and at least one of
> them has its paragraphs in the wrong order — with every quality metric
> green, because nothing measures order.
