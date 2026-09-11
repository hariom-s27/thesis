# 08 — STEP 6: FIND WHERE THE MD&A STARTS AND ENDS

`segment.py` · **the heart of the project**

---

## What it does

Works out: "the MD&A is pages 209 to 226".

**Status: working on real data — 4 of 4 correct. But see the KRBL FY2025
warning below. One bug fixed at `segment.py:445`.**

---

## Why we need it

This is the actual product. And doing it **before** OCR is what makes the whole
thing affordable.

---

## Why one method is not enough

Every single signal fails on some documents:

| Signal | Fails when |
|---|---|
| PDF bookmarks | Report has no bookmarks (almost all pre-2013) |
| Contents page | OCR damaged it, or folio numbers ≠ page numbers |
| Big bold heading | Page is scanned (no font info at all) |
| Text heading | Contents page also has the words → false hit |
| Body clues | Gives roughly the right pages, not exact edges |

So: **use all five, and let them vote.**

---

## The five methods

```
                    THE DOCUMENT
                          |
      +--------+----------+----------+---------+
      |        |          |          |         |
      v        v          v          v         v
    S1        S2         S3         S4        S5
 bookmarks  contents   big bold   OCR       body
            page       heading    heading   clues
      |        |          |          |         |
      +--------+----------+----------+---------+
                          |
                          v
                      ARBITER
              (best score + agreement bonus)
                          |
                    +-----+-----+
                    |           |
              confident?      not sure?
                    |           |
                    v           v
              use it       ask an LLM
```

### S1 — PDF bookmarks (outline)

The PDF's own table of contents. Cheapest and most precise.
Available in roughly 35-55% of post-2016 filings. Almost never before 2013.

**Known failure:** the bookmark often points at the *divider* page, not the
first page of text. Add a "walk forward until real prose starts" step.

### S2 — The printed contents page

Look for lines with dot leaders:

```
Management Discussion and Analysis .......... 42
```

**The offset problem:** a printed page number (folio 42) is not the physical
page index. Covers and inserts push it. So we must **solve for the offset** —
read the folio printed in the margin of ~40 sampled pages and take the most
common difference.

### S3 — Typographic heading (born-digital only)

A heading is text that is:
(a) bigger than the body font, (b) near the top of the page, (c) on a line of
its own, (d) often bold.

*(This is the method that won on 3 of our 4 real documents.)*

### S4 — Text heading (works on scans)

Scanned pages have no font info. So instead: is there a short line among the
first 4-5 lines of the page that matches the MD&A pattern?

Must suppress the contents page, or it fires there.

### S5 — Body clues (the workhorse for scans)

Score every page by how many Schedule V sub-headings it contains, then pick the
best run of pages.

```
Industry Structure and Developments
Opportunities and Threats
Segment-wise or Product-wise Performance
Outlook
Risks and Concerns
Internal Control Systems and their Adequacy
Discussion on Financial Performance
Material Developments in Human Resources / Industrial Relations
Details of Significant Changes in Key Financial Ratios   (FY2020+)
Cautionary Statement
```

**This list survives bad OCR better than a fancy title page does.**

---

## Writing the heading pattern

Do not write a list of exact strings. Write one tolerant pattern:

```
Manage(ment|rial)  ('s)?  [optional punctuation]
    Discussion  [optional "and" or "&"]  Analysis
    [optional "Report" / "Statement" / "Section"]
```

Plus separate handling for:
- the short form `MD&A`
- the merged form `Directors' Report and Management Discussion & Analysis`

**Live proof this matters:** our four real documents used

```
MANAGEMENT DISCUSSION AND ANALYSIS        (Jain, both years — all caps, "AND")
Management Discussion and Analysis        (KRBL FY2024 — title case, "and")
Management Discussion & Analysis          (KRBL FY2025 — ampersand)
```

Three variants from **two companies over two years**. A literal string matcher
would have caught at most one.

---

## Finding the END of the section

The MD&A stops at the next big section. That list is short and stable:

```
Report on Corporate Governance
Business Responsibility (and Sustainability) Report
Independent Auditor's Report
Standalone / Consolidated Financial Statements
Balance Sheet as at ...
Notice of the Annual General Meeting
Secretarial Audit Report
General Shareholder Information
```

---

## Two fixes that mattered more than the first guess

Getting the **start** page right was the easy half. Both our errors came from
the **end**.

### Fix 1 — walk forward

If we found the section using a 1-in-6 page sample, the "end" is just the last
sampled page. So: read pages forward one at a time until an end-heading appears.

### Fix 2 — re-trim after OCR

Once every page in the range has been read properly, work out **both** edges
again.

Without Fix 2, our scanned test document ran from page 15 to page 23 and
swallowed the Corporate Governance report and part of the auditor's report.

```
BEFORE re-trim                 AFTER re-trim
pages 10 ---------- 23         pages 10 --- 15
       [MD&A][CG][AUDIT]              [MD&A]
       WRONG                          RIGHT
```

**All four live extractions used `method: "heading+refined+trimmed"` or
`"toc+refined+trimmed"`.** Both fixes are firing on real data.

---

## THE KRBL FY2025 WARNING — read this carefully

Look at the real manifest row for KRBL FY2025:

```json
"span": {
  "start_page": 33, "end_page": 39,
  "method": "toc+refined+trimmed",
  "heading_text": "Management Discussion & Analysis",
  "terminator_text": "trademarks",
  "score": 0.8
},
"confidence": "high",
"qc": { "diag": {
  "candidates": [["toc", 26, 28, 0.8], ["body_score", 33, 42, 0.658]],
  "supporters": 0,
  "span_words": 515
}}
```

**Four things are wrong here.**

### Problem 1 — `supporters: 0`, but graded `high`

Zero methods agreed with the winner. The whole design says *agreement between
independent weak signals IS the confidence measure*. With zero supporters, the
confidence must not be `high`.

Compare the other three rows:

| Report | supporters | confidence | Correct? |
|---|---|---|---|
| Jain FY2025 | 2 | high | yes |
| Jain FY2024 | 1 | high | borderline |
| KRBL FY2024 | 2 | high | yes |
| **KRBL FY2025** | **0** | **high** | **no — should be medium at best** |

**Fix:** make supporters a hard gate in the grading rule.

```
supporters >= 2  and score >= 0.8   ->  high
supporters == 1  and score >= 0.6   ->  medium
supporters == 0                     ->  medium, never high
                                        (and low if score < 0.7)
```

### Problem 2 — the terminator is `"trademarks"`

That is not a section heading. It is a word in body text — almost certainly
from a cautionary statement or a brand-names note.

The forward-walk stopped on a word that happens to appear in the terminator
list, or the list is too loose.

**Fix:** terminators must match a **heading shape**, not any occurrence of the
string. Require: short line, own line, near the top of the page, and
title-case or all-caps. Add `"trademarks"` to a blocklist if it is in the
terminator list at all.

### Problem 3 — the TOC candidate is 7 pages off

```
toc said:      pages 26-28
final answer:  pages 33-39
```

The winning method was `toc`, yet the TOC's own page range was wrong by 7 pages
and 4 pages too short. The refine-and-trim steps rescued it.

That is the offset problem from S2. It means the folio→physical offset solver
either did not run or got the wrong offset for this document.

**Fix:** log the solved offset in the manifest. If the offset solver is not
confident, do not let `toc` win.

### Problem 4 — `span_words: 515` vs `n_words: 5261`

The diagnostic says the winning candidate span had 515 words. The final
extraction has 5,261. A 10× difference.

This is probably `span_words` being computed on the pre-refinement candidate.
But it means **the diagnostic does not describe the answer**, which makes it
useless for exactly the case where you need it.

**Fix:** recompute `span_words` after refinement, or rename the field to
`candidate_span_words` so nobody is misled.

---

## Why KRBL FY2025 still came out right

The answer *is* correct — 7 pages, 5,261 words, 752 words per page, matching
KRBL FY2024 almost exactly. The refine and trim steps did their job.

**But it came out right despite the confidence system, not because of it.**

If this document had been wrong, nothing would have flagged it. That is the
part to fix — not the answer, the grading.

---

## Good and bad of segmentation approaches

| Approach | Good | Bad |
|---|---|---|
| One regex on the heading | Simple, fast | ~70% hit rate. Dies on scans. |
| Bookmarks only | Very precise when present | Absent in most old reports |
| ML layout model | Handles odd designs | Needs training data we do not have |
| Send the whole PDF to an LLM | Handles anything | Very expensive at 40,000 docs. Can hallucinate page numbers. |
| **Five weak methods + arbiter + LLM for disputes** | Cheap. Agreement measures confidence. | More code. **And the grading must actually use the agreement — see above.** |

---

## An upgrade worth prototyping

The **ESGDoc** paper (arXiv 2310.18073) built a table-of-contents extractor for
1,093 ESG annual reports from 563 companies, 2001-2022.

Their method: build a **heading tree** from reading order + font size, then
apply Keep / Delete / Move to each node.

**Why it is better than our flat per-page score:** it understands that "Risks
and Concerns" is a *child* of "Management Discussion and Analysis", not a
sibling. Our S5 just counts cues; it has no idea about nesting.

They report beating the previous state of the art at a fraction of the running
time, and their dataset is public — so we could pre-train on it.

**Recommendation: prototype this in week 5, after the labelled set exists.**

---

## How to know if it actually works

We must label real documents. There is no shortcut.

Take **300 documents**, spread across:

```
era:          2010-13   /   2014-18   /   2019-25
company size: large     /   mid       /   small
document:     digital   /   mixed     /   scanned
```

Write down the true start and end page of MD&A in each.

Then measure:

| Metric | What it tells you |
|---|---|
| Exact start accuracy | Did we get the first page right? |
| ±1 page start accuracy | The number that decides if a row is usable |
| Boundary IoU | How much of the span overlaps truth (catches over-reach) |
| Pk / WindowDiff | Standard segmentation metrics, comparable with published research |
| **Precision per method** | Which of S1-S5 won, and how often it was wrong |
| **Accuracy by supporter count** | **Does `supporters` actually predict correctness? Right now we assume it does and the KRBL case says we should check.** |

Targets: **95% within ±1 page on digital, 85% on scanned.**
Everything else goes to the review queue, not into the dataset.

---

## What goes wrong

| Problem | Fix |
|---|---|
| MD&A merged into the Directors' Report | Merged-heading pattern + body clues; treat "only S5 fired" as its own known case |
| Contents page triggers a false start | Penalise pages that mention 3+ end-headings |
| Span runs into the auditor's report | Re-trim after OCR + leak-phrase check |
| Dot leaders OCR into letters | Widen the separator pattern to "any run of non-alphanumerics" |
| Folio numbers ≠ page indices | Solve the offset from margin folios; **log it** |
| **Terminator matches a body word** | **Require heading shape, not just string presence — see KRBL FY2025** |
| **Zero supporters graded high** | **Make supporters a hard gate — see KRBL FY2025** |
| No MD&A at all (some tiny companies skip it) | Return "not found" honestly; do not force a guess |
