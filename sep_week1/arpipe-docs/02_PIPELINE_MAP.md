# 02 — THE WHOLE PIPELINE IN ONE PICTURE

---

## The map

```
                      START
                        |
                        v
        +-------------------------------+
        |  STEP 1 : COMPANY LIST        |   universe.py
        |  Who are we collecting for?   |
        +-------------------------------+
                        |
                  ISIN, CIN, symbol, aliases
                        |
                        v
        +-------------------------------+
        |  STEP 2 : FIND LINKS          |   discover.py
        |  Where is each report?        |
        +-------------------------------+
              |         |         |
             NSE       BSE     Screener
              |         |         |
              +---------+---------+
                        |
                        v
        +-------------------------------+
        |  STEP 3 : DOWNLOAD            |   fetch.py
        |  Get the PDF, store once      |
        +-------------------------------+
                        |
                        v
        +-------------------------------+
        |  STEP 4 : TRIAGE EACH PAGE    |   triage.py
        |  Can we read this page free?  |   <-- COST DECIDED HERE
        +-------------------------------+
         |        |        |        |        |
      digital  scanned  hybrid  broken   vector
         |        |        |        |        |
         v        v        v        v        v
       free     OCR    text+OCR   OCR      OCR
         |
         v
        +-------------------------------+
        |  STEP 5 : READ FREE PAGES     |   textlayer.py
        +-------------------------------+
                        |
                        v
        +-------------------------------+
        |  STEP 6 : FIND THE MD&A       |   segment.py
        |  5 methods vote               |   <-- THE PRODUCT
        +-------------------------------+
         |      |      |      |      |
        S1     S2     S3     S4     S5
      book-  contents big   OCR    body
      marks   page   bold  heading clues
         |      |      |      |      |
         +------+------+------+------+
                        |
                     ARBITER
                (best score + agreement)
                        |
                 "pages 209 to 226"
                        |
                        v
        +-------------------------------+
        |  STEP 7 : OCR ONLY THOSE      |   ocr.py
        |  ladder: cheap -> costly      |
        +-------------------------------+
              |         |         |
         Tesseract    VLM     Cloud API
              |         |         |
              +---------+---------+
                        |
                        v
        +-------------------------------+
        |  STEP 8 : FIX ORDER + CLEAN   |   textlayer.py
        |  columns, headers, hyphens    |
        +-------------------------------+
                        |
                        v
        +-------------------------------+
        |  STEP 6b : RE-TRIM EDGES      |   segment.py
        |  now that text is good        |   <-- CATCHES OVER-REACH
        +-------------------------------+
                        |
                        v
        +-------------------------------+
        |  STEP 9 : VERIFY              |   verify.py
        |  right company? right year?   |
        +-------------------------------+
                        |
                  +-----+-----+
                  |           |
                PASS        FAIL
                  |           |
                  v           v
              DATASET     REVIEW QUEUE
                  |         (human)
                  v
        +-------------------------------+
        |  STEP 10 : SAVE + PROOF       |   store.py
        |  mda.txt + mda.json           |
        +-------------------------------+
                        |
                       END
```

---

## The one thing that matters about this map

> **Step 6 (find MD&A) comes BEFORE Step 7 (OCR).**

That is the trick. Everything else is normal engineering.

And **Step 6b** — re-trimming after OCR — is the step people skip and regret.
Before we added it, our scanned test document over-ran by 8 pages and swallowed
the auditor's report.

---

## The commands that match the map

```bash
python -m arpipe.cli universe   # Step 1
python -m arpipe.cli discover   # Step 2
python -m arpipe.cli fetch      # Step 3
python -m arpipe.cli triage     # Step 4        (cost forecast, no OCR)
python -m arpipe.cli extract    # Steps 5-9
python -m arpipe.cli audit      # coverage and quality report
```

Each is a **separate command over a shared manifest**, not one monolith.

Why: the stages have completely different bottlenecks.

| Stage | Bottleneck | Wants |
|---|---|---|
| discover | Network, rate-limited | 1 process, patient |
| fetch | Network + disk | 4-8 workers |
| triage | CPU, cheap | all cores |
| extract | GPU, expensive | GPU batch |
| audit | trivial | 1 process |

If you couple them, **the GPU sits idle behind a politeness delay.** That is
the most expensive mistake in the whole build.

---

## Where the money goes

```
9,000,000 pages
       |
       v
   TRIAGE  (a few CPU-hours, ~$0)
       |
       +-- 7-8M pages readable free  ------> text, $0
       |
       +-- 1-2M pages need OCR
                |
                v
        but only ~350,000 pages are inside an MD&A span
                |
                v
        of those, maybe 300k-1M need OCR
                |
                v
        self-hosted VLM at ~$190/M  ------>  ~$60-200 total
```

**The compute is nearly free. The expensive line is human review.**
~1,500 documents × 2-3 minutes = 60-75 person-hours.

And that number is a direct function of how good Steps 6 and 9 are.
