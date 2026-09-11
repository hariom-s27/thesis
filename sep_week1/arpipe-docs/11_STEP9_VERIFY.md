# 11 — STEP 9: CHECK IT IS THE RIGHT COMPANY AND THE RIGHT YEAR

`verify.py`

---

## What it does

Proves, from **inside the document**, that this text belongs to the company and
year we think it does.

**Status: working on real data. CIN matched exactly on all 4. But ISIN
extraction did not fire once — see the bug below.**

---

## Why we need it

Filenames and exchange metadata **can be wrong**. It happens:

- an attachment mis-filed under the wrong company
- a redirect serves a different file
- a merged entity's report filed under the old company
- the exchange labels the year wrong
- a company files two years at once after falling behind

If you trust the filename, these errors enter your dataset silently. Then
someone builds a paper on it.

---

## The rule

> **The filename tells you what someone claimed. The document tells you the
> truth.**

---

## The four checks

```
                THE DOCUMENT
                     |
     +-------+-------+-------+--------+
     |       |       |       |        |
     v       v       v       v        v
   CIN     ISIN    NAME    YEAR    ERA RULES
   found?  found?  match?  found?  consistent?
     |       |       |       |        |
     +-------+-------+-------+--------+
                     |
                     v
              company_ok?  year_ok?
```

### Check 1 — CIN (Corporate Identity Number)

Every Indian company has one, 21 characters, printed in the report:

```
L 29120 MH 1986 PLC 042028      <- Jain Irrigation, from our real run
|   |    |    |    |    |
|   |    |    |    |    +-- registration number (6 digits)
|   |    |    |    +------- ownership type (3 letters)
|   |    |    +------------ year of incorporation (4 digits)
|   |    +----------------- state code (2 letters)
|   +---------------------- industry code (5 digits)
+-------------------------- L = listed, U = unlisted
```

An exact match is **conclusive**.

**This worked on all four live documents:**

```
L29120MH1986PLC042028   Jain Irrigation  (MH = Maharashtra, 1986)
L01111DL1993PLC052845   KRBL             (DL = Delhi, 1993)
```

Both are internally consistent — Jain Irrigation was indeed incorporated in
Maharashtra, KRBL in Delhi. **The structure itself is a free sanity check.**

### Check 2 — ISIN

`INE` + 9 characters. Also conclusive.

### Check 3 — Fuzzy name match

Strip the noise words first:

```
"Reliance Industries Limited"  ->  "reliance"
"RELIANCE INDUSTRIES LTD."     ->  "reliance"
```

Compare against the canonical name **and every former name**.

```
score >= 88   ->  accept
72 to 88      ->  flag for review
below 72      ->  reject
```

Live results: `name_similarity: 100.0` on all four. Perfect matches.

### Check 4 — Fiscal year

Weight the evidence, because some phrasings are stronger than others:

| Text found | Weight | Why |
|---|---|---|
| "year ended 31st March, 2015" | 5 | The statutory Indian year end. Strongest. |
| "2014-15" or "2014-2015" | 3 | Clear range |
| "as at 31 March 2015" | 2 | Balance sheet date |
| "FY2015" | 2 | Common but sometimes sloppy |

Take the year with the most weight.

**Live results:**

```
Jain FY2025:  modal_fy:2025:w39     39 weighted points
Jain FY2024:  modal_fy:2024:w21     21 weighted points
KRBL FY2024:  modal_fy:2024:w59     59 weighted points
KRBL FY2025:  modal_fy:2025:w60     60 weighted points
```

All four correct.

**But notice the spread: 21 to 60.** Jain FY2024 has only 21 points — half of
Jain FY2025 and a third of KRBL. That is thin.

**Add a floor.** If the weight is below, say, 15, the year is not well
attested and should downgrade confidence — or trigger the era rules as a
tie-breaker.

---

## BUG FOUND IN THE LIVE RUN — ISIN never extracted

All four rows say:

```json
"isin_found": null
```

The ISIN extractor did not fire on a single real document.

### Why this matters

| Consequence | Detail |
|---|---|
| Lost a conclusive check | ISIN is as strong as CIN. We are running on one leg. |
| The DVR bug went undetected | Jain Irrigation's DVR ISIN (`IN9175A01010`) vs its ordinary ISIN (`INE175A01038`) — an ISIN match would have flagged the mismatch immediately |
| Scanned documents will suffer most | On a scan, CIN and ISIN are both OCR'd off the cover. Having only one halves your chance. |

### Likely causes

1. **The pattern is too strict.** `INE` + 9 alphanumerics is right for most
   equity, but the real world also has `IN9`, `INF`, `INC`, `IND`. If the regex
   hardcodes `INE`, it misses Jain Irrigation entirely — which is exactly what
   a DVR line would look like.

2. **ISIN is not printed in these reports.** Possible. CIN is legally required
   on letterheads and filings; ISIN is a convention, usually in the
   "General Shareholder Information" section of the Corporate Governance report.

3. **We only searched the MD&A pages.** If the search is scoped to the extracted
   span rather than the front matter and the shareholder-information section,
   it will find nothing — MD&A prose rarely quotes the ISIN.

### The fix

```
1. Widen the pattern:   IN[EF9CD] + 9 alphanumerics
2. Search the RIGHT pages:
      - first 5 pages (cover, corporate information)
      - any page whose heading matches "General Shareholder Information"
      - any page matching "Corporate Information"
   not just the MD&A span
3. Log WHERE it was found, so you can tell "not printed" from "not searched"
4. Add a test: assert isin_found is not null on at least 80% of documents
```

**Diagnostic value:** right now you cannot tell whether ISIN is missing because
the report does not print it or because the code did not look. Fix the logging
first, then decide.

---

## Era rules — regulation as a free date check

SEBI added disclosure requirements on known dates. That dates a document
independently of what it claims about itself.

| If the text contains... | Then the year cannot be before | Because |
|---|---|---|
| The 8 mandated financial ratios | **FY2020** | LODR amendment May 2018, effective FY2019-20 |
| BRSR / "Business Responsibility and Sustainability Report" | **FY2023** | Replaced BRR for the top 1,000 companies |
| "Ind AS" | **FY2016** | Phased mandatory adoption from FY2016-17 |
| "Companies Act, 2013" or CSR disclosure | **FY2015** | Act commenced FY2014-15 |
| "Business Responsibility Report" | **FY2013** | Top 100 companies, FY2012-13 |

The 8 mandated ratios:

```
Debtors Turnover        Current Ratio            Net Profit Margin
Inventory Turnover      Debt Equity Ratio        Return on Net Worth
Interest Coverage       Operating Profit Margin
```

**Example catch:** a file labelled FY2013 that has the mandated ratio table is
**not** an FY2013 report. No amount of filename parsing would catch this.

### Something odd in the live data — worth checking

```
KRBL FY2024:  "ratio_cues": 7      <- found 7 of the mandated ratios
KRBL FY2025:  "ratio_cues": 7      <- found 7
Jain FY2025:  "ratio_cues": 0      <- found ZERO
Jain FY2024:  "ratio_cues": 0      <- found ZERO
```

All four are FY2024 or FY2025 — **well after** the FY2020 mandate. All four
should carry the ratio table.

**KRBL has it. Jain Irrigation apparently does not.**

Three possible explanations, and you should find out which:

| Explanation | How to check |
|---|---|
| Jain puts the ratio table in the Board's Report, not the MD&A | Search the whole document for the ratio names, not just the span |
| Our span is slightly short and cut the ratio table off the end | The span ends at 226 of 445 — look at pages 227-230 by hand |
| Jain genuinely omits it (a compliance gap) | Would be a finding in itself |

**Why this matters beyond one company:** if the ratio table often sits just
*outside* the MD&A heading, then `ratio_cues` is not a reliable era signal, and
the boundary detection may be systematically trimming a page too early.

Check this on the labelled set. It is a five-minute look that could reveal a
systematic boundary bias.

---

## Section quality checks — is this even MD&A?

Separately from identity, ask: does this text look like MD&A?

| Test | What it catches | Live values |
|---|---|---|
| Leak phrases: "we have audited the accompanying", "basis for opinion", "notice is hereby given that", "composition of the board of directors" | Span ran into the wrong section | `leaks: []` on all 4 — clean |
| Digits ÷ letters above 25% | You captured a financial statement, not prose | 0.021-0.026 — very clean |
| Fewer than 250 words | Span too short | 5,261-15,195 — fine |
| More than 40,000 words | Span too long | fine |
| Many tokens longer than 28 characters | OCR collapsed word boundaries | 0.0 — clean |
| **Words per page outside 250-1200** | Graphics-heavy, or bad page count | **691-808 — add this check, it is free** |

---

## Three tiers — and the third one must exist

| Tier | Condition | Where it goes | Expected share |
|---|---|---|---|
| **high** | Identity + year confirmed, **2+ supporters**, span score ≥0.8, no leaks, no era conflict | Clean dataset | ~80% |
| **medium** | Identity + year confirmed, ≥1 supporter, span score ≥0.6, at most one leak | Dataset, flagged | ~15% |
| **low** | Identity unproven, **0 supporters**, too short, garbled, or era conflict | **Human review queue** | 3-6% |

**Note the change from the original design:** supporter count is now a hard
gate, because KRBL FY2025 was graded `high` with `supporters: 0`. See
`08_STEP6_FIND_MDA.md`.

### Why the low tier must exist

> A pipeline that only writes text files has no way to say *"I found something
> but I do not believe it"* — so it writes the something.

That is how a corpus quietly poisons a research paper. The low tier must exist
and must be visible.

---

## Deduplication — two kinds

**Exact:** SHA-256 of the PDF bytes. The same report is served by both
exchanges. Download twice, keep once.

**Near-duplicate:** MinHash + LSH (`datasketch`) over word shingles. Catches:

- the same report re-served with different compression
- a corrected re-filing
- **the same PDF filed against two different years** ← this one damages a panel

Run a **cross-year duplicate check inside each company**. If two adjacent years
give near-identical MD&A text, either one year is wrong, or the company
copy-pasted. Both are worth knowing.

**Quick check on the live data:** KRBL FY2024 (5,654 words) vs FY2025 (5,261
words). Different lengths, so not a straight copy — but a MinHash comparison
would tell you how much was recycled. That itself is a research variable:
*disclosure boilerplate ratio*.

---

## What goes wrong

| Problem | Fix |
|---|---|
| CIN not printed anywhere | Fall back to ISIN, then fuzzy name |
| OCR mangled the CIN (0 vs O, 1 vs l) | Allow near-matches with a warning; the structure is rigid so most are recoverable |
| Company renamed — name match fails | Match against all aliases |
| Two years mentioned equally often | Weighted counting; prefer "year ended 31 March" |
| **Year weight is thin (under 15)** | **Downgrade confidence; use era rules as tie-breaker** |
| Report covers 18 months (transition year) | Flag it; these are real and rare |
| **ISIN never found** | **Widen the pattern, search the right pages, log where — see the bug above** |
