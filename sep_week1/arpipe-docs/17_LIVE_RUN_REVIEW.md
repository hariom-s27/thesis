# 17 — THE LIVE RUN: WHAT IT PROVED AND WHAT IT HID

**Read this before you trust the pipeline.**

---

## 17.1 — What you ran

```
Environment:     .venv, all dependencies installed
Tests:           24 passed
Company master:  2,571 NSE companies (live download)
Companies tried: 3
Reports found:   4
Pages analysed:  1,275
MD&A extracted:  4 of 4
Confidence:      high on all 4
Manifests:       JSONL + Parquet written
Bugs fixed:      fetch.py:37, cli.py:80, store.py:121, segment.py:445
Boundaries:      manually checked and corrected
```

---

## 17.2 — The results

| Company | FY | Total pages | MD&A pages | Words | Words/page | Method | Supporters |
|---|---|---|---|---|---|---|---|
| Jain Irrigation | 2025 | 351 | 103-124 (22) | 15,195 | 691 | heading+refined+trimmed | 2 |
| Jain Irrigation | 2024 | 445 | 209-226 (18) | 13,031 | 724 | heading+refined+trimmed | 1 |
| KRBL | 2024 | 155 | 27-33 (7) | 5,654 | 808 | heading+refined+trimmed | 2 |
| KRBL | 2025 | 324 | 33-39 (7) | 5,261 | 752 | toc+refined+trimmed | **0** |

---

## 17.3 — What this genuinely proves

### 1. The exchange route works, for free

You got real annual reports from NSE with no subscription, no scraping tricks,
no vendor. The `discover` → `fetch` path is real.

### 2. The 4% assumption is correct

```
Average: 319 pages per document, 13.5 pages of MD&A = 4.3%
```

The entire cost model rests on this number. It is now measured, not assumed.

### 3. Locate-then-OCR works on a real filing

Jain Irrigation FY2024:

```
n_pages:             445
frac_needing_ocr:    12.84%   -> about 57 scanned pages exist
ocr_pages:           0        -> none of them were inside the MD&A span
```

A document-level router would have OCR'd 445 pages or skipped the document.
Page-level routing plus locate-first cost **zero**.

**This is the single most important result in the run.**

### 4. CIN verification works on real documents

```
L29120MH1986PLC042028   Jain Irrigation   MH = Maharashtra, 1986
L01111DL1993PLC052845   KRBL              DL = Delhi, 1993
```

Both structurally consistent. Both matched at 100% name similarity.

### 5. The heading pattern is doing real work

Three different spellings across two companies and two years:

```
MANAGEMENT DISCUSSION AND ANALYSIS      Jain, both years
Management Discussion and Analysis      KRBL FY2024
Management Discussion & Analysis        KRBL FY2025
```

A literal string matcher catches at most one of these.

### 6. Both boundary fixes are firing

Every row shows `+refined+trimmed`. The forward-walk and the post-OCR re-trim
are both running on real data.

### 7. The text quality signals are consistent

```
alpha_ratio:      0.788 - 0.798
digit_ratio:      0.021 - 0.026
avg_word_len:     5.71  - 5.99
long_token_frac:  0.0 on all four
leaks:            [] on all four
words per page:   691 - 808
```

Four documents, two companies, two years, and these numbers barely move.
**That is now your healthy baseline.** Anything in the full run far outside
these bands deserves a look.

---

## 17.4 — What this does NOT prove

Be honest with yourself about this list.

| Untested | Why it matters |
|---|---|
| **No scanned document** | `ocr_pages: 0` on all four. **The entire OCR ladder has never run on real data.** Tesseract is not even installed. |
| **No broken-text page** | The most dangerous page class is unvalidated |
| **No vector-text page** | Same |
| **No bilingual document** | `bilingual: false` × 4. Script routing never fired. |
| **No pre-2016 document** | ZIP unwrapping, `qpdf` repair, empty-password handling — all untested |
| **Only FY2024 and FY2025** | The two easiest years in the whole window |
| **Only 2 companies** | Both mid-cap, both NSE, both English, both manufacturing |
| **No BSE company** | ~3,000 small caps are outside your master entirely |
| **Boundaries were corrected by hand** | You checked them yourself. That is not automated accuracy. |

### The honest summary

> Four documents from the two easiest years, from one exchange, in one
> language, with no OCR, with human-corrected boundaries, is a **smoke test
> that passed**.
>
> It is not validation. Treat it as proof the plumbing connects, not proof the
> method works.

---

## 17.5 — FIVE REAL BUGS THE RUN EXPOSED

### BUG 1 — Jain Irrigation is being tracked under its DVR ISIN

```
"company_id": "IN9175A01010"
url contains: JISLDVREQS
```

`IN9175A01010` is the **differential voting rights** line, not the ordinary
equity line (`INE175A01038`).

Both lines point at the **same annual report PDF**.

| Consequence | Effect |
|---|---|
| Same report processed twice | Wasted budget |
| Two rows per company-year in the panel | Any regression double-counts Jain Irrigation |
| Which ISIN joins to financial data? | Ambiguous |
| CIN verification does not catch it | `L29120MH1986PLC042028` matches both lines |

**Fix:** group NSE rows by CIN (or normalised name); prefer `INE` over `IN9`;
store the others as `alternate_isins`; flag `series_type: dvr`.

**Test:** assert one row per `(CIN, fy_end)` in the final manifest.

---

### BUG 2 — ISIN was never extracted from any PDF

```
"isin_found": null    on all four documents
```

You are running identity verification on **one leg** instead of two.

Three possible causes:

1. The pattern hardcodes `INE` and misses `IN9`, `INF`, `INC`, `IND`
2. ISIN genuinely is not printed in these reports (possible — CIN is legally
   required, ISIN is convention)
3. The search is scoped to the MD&A span, and MD&A prose rarely quotes the ISIN

**Right now you cannot tell which.** That is the real problem.

**Fix, in order:**

```
1. Log WHERE the search looked and what it found (or did not)
2. Widen the pattern to  IN[EF9CD] + 9 alphanumerics
3. Search the cover page, "Corporate Information", and
   "General Shareholder Information" - not just the span
4. Add a test: isin_found is not null on >=80% of documents
```

Note that a working ISIN check would have caught **Bug 1** immediately.

---

### BUG 3 — `supporters: 0` graded as `high` confidence

KRBL FY2025:

```
"confidence": "high"
"diag": { "supporters": 0 }
```

**Zero methods agreed with the winner, and it was graded highest confidence.**

The whole design says *agreement between independent weak signals IS the
confidence measure.* The grading rule is not using it.

Across all four:

| Report | supporters | graded | should be |
|---|---|---|---|
| Jain FY2025 | 2 | high | high |
| Jain FY2024 | 1 | high | medium |
| KRBL FY2024 | 2 | high | high |
| **KRBL FY2025** | **0** | **high** | **medium at best** |

**Fix — make it a hard gate:**

```
supporters >= 2  and score >= 0.8   ->  high
supporters == 1  and score >= 0.6   ->  medium
supporters == 0                     ->  medium, never high
                                        (low if score < 0.7)
```

**Why this matters at scale:** with 40,000 documents and a target of 3-6% in
the review queue, a grading rule that ignores disagreement will hide exactly
the documents you most need to look at.

---

### BUG 4 — The terminator was a body word

KRBL FY2025:

```
"terminator_text": "trademarks"
```

"Trademarks" is not a section heading. It is a word in body text — almost
certainly from a cautionary statement or a brand-names note.

Either the terminator list is too loose, or the matcher is looking for the
string anywhere on the page instead of in a heading position.

**Fix:** a terminator must match a **heading shape**:

```
- short line (under ~80 characters)
- on its own line
- in the top third of the page, or preceded by whitespace
- title case or ALL CAPS
```

---

### BUG 5 — The TOC method won while being 7 pages wrong

KRBL FY2025:

```
"method": "toc+refined+trimmed"
diag candidates:
   ["toc",        26, 28, 0.8]     <- what TOC said
   ["body_score", 33, 42, 0.658]
final answer:      33, 39
```

The winning method said pages **26-28**. The answer is **33-39**.
The TOC was wrong by 7 pages and 4 pages too short. The refine and trim steps
rescued it.

Compare KRBL FY2024, where TOC said **53-66** and the answer was **27-33** —
wrong by 26 pages, and there the `heading` method correctly won instead.

**So the TOC method is unreliable on this company in both years.** That is the
folio→physical-page offset problem, and either the offset solver did not run or
it got the wrong offset.

**Fix:**

```
1. Log the solved page offset in the manifest
2. If the offset solver is not confident, do not let `toc` win the arbitration
3. On the labelled set, measure TOC precision separately - it may deserve
   a lower weight than it currently has
```

---

### Minor issues also worth fixing

| Issue | Where | Fix |
|---|---|---|
| Windows backslash paths | manifest | Store forward-slash, relative to dataset root |
| `mda_path` and `path` are identical | manifest | Drop one |
| `span_words: 515` vs `n_words: 5261` | diag | Recompute after refinement, or rename to `candidate_span_words` |
| `configs/default.yaml` not read | cli | Wire it or delete it — a config that lies is worse than none |

---

## 17.6 — One thing worth investigating, not clearly a bug

```
KRBL FY2024:  ratio_cues: 7
KRBL FY2025:  ratio_cues: 7
Jain FY2025:  ratio_cues: 0
Jain FY2024:  ratio_cues: 0
```

All four are FY2024/25 — well after the FY2020 mandate. All four *should*
carry the mandated key-financial-ratios table.

KRBL has it. Jain Irrigation apparently does not.

**Three possible explanations:**

| Explanation | How to check | If true |
|---|---|---|
| Jain puts the ratio table in the Board's Report, not MD&A | Search the whole document for the ratio names | `ratio_cues` is not a reliable era signal |
| Our span is short and cut the table off the end | Look at pages 227-230 of Jain FY2024 by hand | **We have a systematic boundary bias** |
| Jain genuinely omits it | Compare against the filed XBRL | A compliance finding, interesting in itself |

**Do this check before the full run.** It is five minutes of looking and it
could reveal that boundaries are systematically one page short.

---

## 17.7 — What to do with this

### Immediately (2 hours)

```
1. Install Tesseract and qpdf
2. Fix Bug 3 (supporter gate) - it is a five-line change
3. Fix Bug 5's logging (record the solved offset)
4. Fix the manifest paths
```

### This week

```
5. Fix Bug 1 (DVR collapsing) and Bug 2 (ISIN extraction)
6. Fix Bug 4 (terminator heading shape)
7. Re-run the 4 samples. KRBL FY2025 should become `medium`.
   Jain should appear once, not twice.
8. Check the Jain ratio_cues question by hand
```

### Then, and only then

```
9. Wire the BSE master
10. Pick 20 documents spread across FY2010-2014 - the SCANNED era -
    and run them. That is the first real test of the OCR path.
11. Build the labelled 300
```

---

## 17.8 — The one-sentence read

> **The plumbing works. The method is unproven. Four easy documents with
> hand-corrected boundaries and five real bugs is exactly where a good
> prototype should be after week one — provided you now go and test the hard
> cases, not more easy ones.**
