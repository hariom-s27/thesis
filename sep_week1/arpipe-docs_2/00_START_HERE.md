# 00 — START HERE

**Project:** ARPipe — Indian annual report → MD&A text, FY2010 to FY2025
**Status:** working on real NSE data. 4 real reports extracted. 24 tests pass.
**Date:** 9 September 2026

---

## What this folder is

One file per section. Read in order, or jump to what you need.

| File | What is inside |
|---|---|
| `00_START_HERE.md` | This file. The map. |
| `01_THE_PROBLEM.md` | What MD&A is, why this is hard, what "done" looks like |
| `02_PIPELINE_MAP.md` | The whole thing in one picture |
| `03_STEP1_COMPANY_LIST.md` | Who are we collecting for |
| `04_STEP2_FIND_LINKS.md` | Where is each report |
| `05_STEP3_DOWNLOAD.md` | Get the PDF, store it once |
| `06_STEP4_TRIAGE.md` | Can we read this page for free? |
| `07_STEP5_READ_FREE_TEXT.md` | Pull text out of the easy pages |
| `08_STEP6_FIND_MDA.md` | Find where the section starts and ends |
| `09_STEP7_OCR_LADDER.md` | OCR only the pages we need |
| `10_STEP8_CLEAN_TEXT.md` | Fix column order, strip headers |
| `11_STEP9_VERIFY.md` | Right company? Right year? |
| `12_STEP10_STORE.md` | Save it with the proof |
| `13_HARD_PROBLEMS.md` | Scans, Hindi, OCR quality, columns, tables, broken PDFs |
| `14_REUSE_OR_BUILD.md` | What already exists vs what we must build |
| `15_COST_AND_TIME.md` | Money, storage, hours |
| `16_TWELVE_WEEK_PLAN.md` | Week by week |
| **`17_LIVE_RUN_REVIEW.md`** | **The 4 real extractions — what they prove and what they hide** |
| **`18_FINAL_PIPELINE.md`** | **The production run design. Read this before the full crawl.** |
| `19_GLOSSARY.md` | Every word explained in one line |
| `20_SOURCES.md` | Everything I read |

---

## If you only read two files

Read **`17_LIVE_RUN_REVIEW.md`** and **`18_FINAL_PIPELINE.md`**.

The first says what your 4 real extractions actually proved (less than it
looks) and what they hid (three real bugs). The second is the concrete run
design for the full crawl.

---

## The whole project in ten lines

```
 1. Use ISIN as the key. Chain old symbols, or you lose years silently.
 2. Get PDFs free from NSE, then BSE, then screener. Both start ~FY2010.
 3. Store by file hash. Download once, keep once, never re-download.
 4. Classify EVERY PAGE, not every document. Five classes, not two.
 5. Never use rawdict on a scanned page. 29.4s becomes 0.23s. 128x.
 6. FIND THE MD&A BEFORE YOU OCR. This is the whole trick.
 7. Five weak location methods + an arbiter beat one strong regex.
 8. OCR as a ladder: Tesseract -> local VLM -> cloud. Never one engine.
 9. AWS Textract: no Hindi, 8x the cost. Rung 3 only, 2-5% of pages.
10. Prove company and year from INSIDE the document. Grade everything.
    Quarantine what you do not believe.
```

---

## The one big idea

> **Find the MD&A first. Then OCR only those pages.**

Almost every existing tool does it backwards: OCR the whole document, then look
for the section. The MD&A is about **4% of the paper**. Doing it backwards
costs 25× more for no benefit.

```
WRONG                              RIGHT
-----                              -----
300-page scan                      300-page scan
      |                                  |
      v                                  v
OCR all 300 pages   <-- expensive   Look at pages cheaply (no OCR)
      |                                  |
      v                                  v
Find MD&A                          Find MD&A (pages 120-134)
      |                                  |
      v                                  v
Keep 15 pages                      OCR only those 15 pages
                                         |
Cost: 300 OCR pages                      v
                                   Cost: ~20-70 OCR pages
```

---

## Where the code stands today

**Working, on real data:**

- Local venv, all dependencies installed
- 24 tests pass
- NSE company master downloaded: 2,571 companies
- 4 real annual reports found, downloaded, extracted
- 1,275 real PDF pages analysed
- JSONL + Parquet manifests written
- 4 bugs found and fixed in `fetch.py`, `cli.py`, `store.py`, `segment.py`

**Not working yet:**

- Tesseract and qpdf not installed → no OCR path at all
- No Hindi language file
- BSE master is not wired → 2,571 NSE companies only, missing ~3,000 BSE-only
- No LLM adjudication provider
- No table extraction
- `configs/default.yaml` still not read by the code
- **Every threshold is still hand-set and unvalidated**

See `17_LIVE_RUN_REVIEW.md` for the honest read on what the 4 successes mean.

---

## The one thing to do next

> **Label 300 real annual reports, spread across era × company size ×
> document type. Re-fit every threshold against them.**

Every number in the code — the 120-character cutoff, the 55% image area, the
2% garbage ratio, the 2.5% gutter, the 0.72 confidence floor — was chosen by
hand and checked only against synthetic PDFs and four easy real ones.

That one week turns a prototype into a research instrument.
