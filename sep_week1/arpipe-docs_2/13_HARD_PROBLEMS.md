# 13 — THE SIX HARD PROBLEMS

Each explained on its own.

---

# 13.1 — SCANNED COPIES

## The problem
The PDF is a photo of paper. There is no text inside. Copying gives nothing.

## How to detect it
Ask three things about the page:

1. How many characters does the text layer give? (fewer than ~120 = suspicious)
2. How much of the page is covered by one image? (more than 55% = a scan)
3. Are there hundreds of tiny drawing paths instead? (= vector text)

All three come from the PDF structure. **No rendering needed.**

## How common
Concentrated in **FY2010-FY2014**, in **PSUs**, and in the **bottom two
market-cap quartiles**. Post-2018 filings are nearly all born-digital.

**But measure this, do not assume it.** The triage stage gives you the real
distribution by year and company size in a few CPU-hours, before you spend
anything.

Your live run: 4 documents, all FY2024/25, `frac_needing_ocr` between 0.57%
and 12.84%. **That tells you nothing about FY2011.** Do not extrapolate.

## How to handle it
The ladder in `09_STEP7_OCR_LADDER.md`. And the crucial part: **find the
section before you OCR**, so you OCR ~20-70 pages instead of 300.

---

# 13.2 — BILINGUAL REPORTS (HINDI + ENGLISH)

## The problem
Public-sector companies must publish in Hindi and English under the Official
Languages Act. Some others carry regional-language sections.

## The good news — this is smaller than it looks

Two facts make it easy:

1. **MD&A is a SEBI filing. It is written in English.**
2. In a bilingual report, the Hindi part is almost always a **mirror** of the
   English part — the same content, not extra content.

So:

> **Detect Hindi pages and DROP them. Do not OCR them.**

```
                    A PAGE
                      |
              what script is it?
             /        |          \
        Latin      Devanagari    Mixed
            |          |            |
            v          v            v
      normal path    DROP      Indic-capable
                   (record      engine only
                    the fact)
```

## How to detect script

Count Unicode blocks in the text. No language model needed:

```
Devanagari block:  U+0900 to U+097F
Bengali:           U+0980 to U+09FF
Tamil:             U+0B80 to U+0BFF
Gujarati:          U+0A80 to U+0AFF

if indic_chars / total_chars < 0.05   ->  Latin
if indic_chars / total_chars > 0.85   ->  Indic
else                                  ->  Mixed
```

**Do the script check AFTER you have decided the text layer is trustworthy.**
A broken-encoding English page can produce weird code points too, and you do
not want to mistake mojibake for Hindi.

## If you DO need to read Hindi

A 2026 benchmark tested 10 OCR systems on 300 real printed Devanagari scans.
The results are brutal and non-obvious:

| System | chrF++ on real Hindi scans |
|---|---|
| Gemini 2.5 Flash | **86.3** |
| Claude Opus 4.7 | 82.2 |
| Mistral OCR | 77.6 |
| Qwen3-VL-8B | 75.2 |
| GPT-5.5 | 58.5 |
| EasyOCR | 58.3 |
| Qwen2.5-VL-3B | 45.4 |
| olmOCR-7B | 40.5 |
| Unlimited-OCR | 24.7 |
| DeepSeek-OCR | **10.4** |

### Three lessons

**Lesson 1 — English leaderboard rank does not transfer.**
GPT-5.5 and olmOCR-7B both top English benchmarks and both collapse on Hindi.

**Lesson 2 — Watch for repetition.**
DeepSeek-OCR produced output up to **71× the correct length** on 2-3% of
samples, with a median character error rate of 100% and 89% of real scans
classed as catastrophic. The median looked fine; the mean was destroyed.

**Lesson 3 — Post-correction does not save you.**
A ByT5 corrector trained on EasyOCR's errors gained only **+1.2 to +1.5
chrF++**, and applying it to a different engine was **neutral or harmful**.
Do not build one. Spend the week on the labelled set instead.

A separate benchmark (MDPBench, 3,400 images, 17 languages) found non-Latin
scripts drop **14.0%** on average versus Latin, and that models "omit crucial
vowel diacritics" in Hindi.

## The concrete recommendation

| For Hindi pages | Use | Never use |
|---|---|---|
| Best quality | Gemini 2.5 Flash-class, or Google Document AI | AWS Textract (no Devanagari at all) |
| Best value | PaddleOCR-VL (109 languages incl. Devanagari) | olmOCR, DeepSeek-OCR |

**Record the decision.** Put a script label on every page in the manifest. Then
you can come back later and process the Hindi corpus deliberately — that is a
legitimate research asset on its own.

Your live run has `"bilingual": false` on all four documents. **The script
routing has never fired on real data.** It is untested.

---

# 13.3 — TEXT RECOGNITION QUALITY: THE SILENT KILLER

## The problem
Modern OCR does not fail loudly any more. It fails **fluently**.

```
TESSERACT FAILS LIKE THIS          A VISION MODEL FAILS LIKE THIS
-------------------------          ------------------------------
Rev3nue rn5e 12,4B0                Revenue rose 12,480
   ^^^^^^^^^^^^^^^                    ^^^^^^^^^^^^^^^
   obviously broken                  looks perfect
   you will catch it                 the paper says 12,486
```

## The research finding that should change your acceptance criteria

**FinCriticalED** (arXiv 2511.14998) is a benchmark of **859 real financial
document pages** with **9,481 expert-annotated facts** across five categories:
numeric values, temporal information, monetary units, reporting entities and
financial concepts. It tested 13 systems.

The headline result:

| System | ROUGE-1 (text similarity) | Monetary unit accuracy |
|---|---|---|
| MinerU2.5 | **95.71** | **54.05** |

Read that twice. Nearly 96% on text similarity. **Barely half** on getting the
currency unit right.

And across the field: a **0.12-point difference in ROUGE-1** corresponded to a
**7.22-point drop in fact accuracy**.

The paper's own summary: numeric values and monetary units emerged as "the most
vulnerable fact types," and critical errors concentrate in visually complex,
mixed-layout documents — which is exactly what an Indian annual report is.

## What this means for us

> **Never accept a number because the text score was high.**

Text similarity metrics measure the wrong thing for financial data. Character
accuracy hides exactly the errors that matter.

## What to do instead

For **prose** (which MD&A mostly is): text metrics are fine.

For **numbers**: carry **provenance**, not a score.

```
BAD                          GOOD
---                          ----
value: 52000                 value:        52000
confidence: 0.97             currency:     INR
                             unit:         lakh
                             period:       FY2024
                             entity:       KRBL Limited
                             page:         78
                             bbox:         [120, 340, 280, 356]
                             engine:       PaddleOCR-VL
                             validated:    yes (XBRL match)
```

That answers the real question: *where did this number come from, and how do we
know what it means?*

---

# 13.4 — TWO-COLUMN REPORTS

Covered fully in `10_STEP8_CLEAN_TEXT.md`. The short version:

| Point | Detail |
|---|---|
| Why it matters | MD&A and Corporate Governance are the most two-column sections |
| The failure | Naive sorting interleaves columns; text looks fine but is nonsense |
| The fix | XY-cut (free) or a reading-order model (better, costs a GPU) |
| **The threshold trap** | **Academic 5% gutter → 0 of 28 correct. Indian 2.5% gutter → 24 of 28 correct.** |
| The second trap | Measure gaps on **line** boxes, not **block** boxes |
| The upgrade | XY-Cut++ (arXiv 2504.10258) — 98.8 BLEU, up to +24% over baseline |

---

# 13.5 — TABLES AND FINANCIAL NUMBERS

## The problem
The MD&A carries the mandated ratio table. And beyond MD&A, you may want
financial figures from the whole report.

**This is a different problem with a different acceptance bar.** A 1% word
error in prose is invisible. A 1% number error is a wrong paper.

## Routing table extraction by page type

| Page type | Tool | Why |
|---|---|---|
| Digital, ruled table (lines drawn) | **Camelot `lattice`** | Uses the drawn lines directly. Near-exact. |
| Digital, unruled table | Camelot `stream` / pdfplumber | Infers columns from whitespace. Needs tuning. |
| Digital, complex or nested | **TATR / gmft** | Won on Financial tables in a 10-parser academic study |
| Scanned | Document VLM (HTML table output) | PaddleOCR-VL reports table TEDS 89.76 |
| Scanned, ruled, high stakes | AWS Textract TABLES | Mature. Expensive. Only where numbers must be right. |

## THE UNIT TRAP — specific to Indian filings

**This is the single biggest numeric risk in Indian annual reports.**

The same table can be in:

```
₹ lakh       (1 lakh   = 100,000)
₹ crore      (1 crore  = 10,000,000)
₹ million    (1,000,000)
₹ '000       (1,000)
```

And the unit is usually printed **once**, in small type, above the table or in
a footnote.

```
                        (₹ in lakh)          <- easy to miss
+--------------------+------------+
| Revenue            |   52,000   |
+--------------------+------------+

52,000 lakh  = ₹520 crore        CORRECT
52,000 crore = ₹520,000 crore    WRONG BY 100x
```

Given that FinCriticalED found monetary-unit accuracy as low as **54%**, this
must be handled explicitly:

1. Treat the unit as a **first-class extracted field** with its own confidence
2. Resolve it from the nearest preceding unit declaration on the page
3. **Reject any table where no unit can be found** — do not guess

> **A number with no unit is not data.**

## Validate against something independent

This is where free XBRL earns its keep.

```
   Annual Report PDF                    XBRL filing (free)
          |                                    |
          v                                    v
   OCR extracts:                        Tagged value:
   Revenue = ₹52,000 lakh               Revenue = 5,200,000,000
          |                                    |
          +----------------+-------------------+
                           |
                           v
                   convert and compare
                           |
                    +------+------+
                    |             |
                  MATCH        MISMATCH
                    |             |
                    v             v
                 accept    the parse OR the
                           unit resolution failed
                              -> investigate
```

Available from FY2018 onward on both exchanges. For earlier years, fall back to
internal consistency (does the ratio table's stated change agree with the two
years of figures it shows?) or a licensed financial panel.

## Is this in scope for v1?

**Honestly, no.** The deliverable is MD&A *text*.

Do only the **ratio table**, because it is mandated, standard-shaped, and dates
the document. Everything else waits for v2.

---

# 13.6 — DAMAGED AND AWKWARD PDFs

| Problem | What it looks like | Fix |
|---|---|---|
| Broken xref table | PDF will not open at all | `qpdf` repair pass |
| Empty-password encryption | "Protected" but opens with `""` | Try the empty password first |
| ZIP instead of PDF | NSE pre-2016 rows | Unzip, keep the largest PDF, log the rest |
| Rotated pages | Text sideways | `ocrmypdf --rotate-pages` |
| Skewed scan | Text at a slight angle | `ocrmypdf --deskew` |
| Huge file (200 MB+) | Memory blowup | Stream to disk, cap size |
| Pages in the wrong order | Rare but happens | Detect via folio numbers |
| Mixed page sizes in one PDF | A4 body with A3 foldout | Normalise before rendering |

**qpdf is not installed on your machine.** Nothing in this list works until it
is:

```powershell
winget install --exact --id QPDF.QPDF
```
