# 09 — STEP 7: OCR ONLY THE PAGES WE NEED

`ocr.py`

---

## What it does

Turns pictures of text into text — but **only** for the pages inside the MD&A
range.

**Status: written, tested on synthetic scans, NEVER RUN ON REAL DATA.**

All four live extractions had `"ocr_pages": 0` and `"ocr_engine": null`.
Tesseract is not installed on your machine. This entire path is unvalidated
against real filings.

---

## Why we need it

Roughly 10-20% of our pages are pictures, and we cannot read them any other way.

Old reports (FY2010-2014), PSUs and small caps are where they live — exactly
the part of the corpus we have not touched yet.

---

## The rule

> **Never use one OCR engine for everything. Use a ladder.**

Cheap engines handle most pages. Expensive engines handle only what the cheap
ones fail. A quality check decides when to climb.

```
                     A PAGE
                       |
                       v
             +-------------------+
             | RUNG 1: Tesseract |   free, CPU, ~0.5-3 s/page
             +-------------------+
                       |
                  good enough?
                   /       \
                YES         NO
                 |           |
              ACCEPT         v
                    +--------------------+
                    | RUNG 2: local VLM  |  ~$190 per million pages
                    | PaddleOCR-VL /     |  on your own GPU
                    | MinerU2.5 /        |
                    | olmOCR-2           |
                    +--------------------+
                             |
                        good enough?
                         /       \
                      YES         NO
                       |           |
                    ACCEPT         v
                          +------------------+
                          | RUNG 3: cloud    |  ~$1,500 per million
                          | Textract /       |  pages
                          | Google DocAI /   |
                          | Gemini           |
                          +------------------+
```

---

## The engines, compared

| Engine | Cost per 1M pages | Quality | Notes |
|---|---|---|---|
| Tesseract 5 (your CPU) | compute only | Weak on tables and columns | Fine for clean 300 DPI English |
| **PaddleOCR-VL 0.9B** | lowest GPU cost | **96.33% OmniDocBench v1.6** | ~2 GB VRAM. ~45 pages/min on an L40S. 100+ languages **including Hindi**. Apache-2.0. **Best value.** |
| MinerU2.5 1.2B | similar | text edit dist 0.047, table TEDS 88.22 | ≥8 GB VRAM. Strong on dense multi-column. Apache-2.0. |
| olmOCR-2 7B | ~$190-200 | 82.4 olmOCR-bench | 10,000 pages for under $2 on one H100 |
| dots.mocr ~1.7B | low | 80.5% MDPBench (best open) | Good multilingual |
| Marker | — | 76-83% olmOCR-bench, ~120 p/s on H100 | **GPL-3 + RAIL-M — restricted above ~$2M revenue.** Licence landmine. |
| Docling | — | CPU-friendly, TableFormer good on financial tables | MIT. Slow. |
| Gemini Flash-class | ~$140-1,000 | 76.4 olmOCR-bench, **86.3 chrF++ on Hindi** | Best measured Devanagari result |
| **AWS Textract (text)** | ~$1,500 | Mature on clean scans | **Latin scripts only — no Hindi** |
| AWS Textract (TABLES) | ~$15,000 | Strong ruled tables | Only where you need the table |
| Google Document AI | ~$1,500 | Broad languages incl. Indic | The managed option when Hindi must be read |

---

## The direct answer on AWS

**Two facts decide it.**

**1. Textract cannot read Hindi.** Amazon's structured extraction supports
English, German, French, Spanish, Italian and Portuguese. There is no
Devanagari or other Indian script. It literally cannot read the Hindi half of
a bilingual PSU report.

**2. It costs about 8× a self-hosted 1B model.** ~$1,500 per million pages for
plain text, vs ~$190. Its table model is another 10× on top (~$15,000/M).

### Verdict

| Use Textract for | Do not use Textract for |
|---|---|
| Hard **English** scans that rungs 1 and 2 both failed | The default OCR path |
| Ruled financial tables where numbers must be exact | Anything in Hindi or other Indian scripts |
| When you would rather pay per page than run a GPU | Bulk processing of 9 million pages |

**Budget it at 2-5% of your OCR pages**, not as the main road.

---

## The quality gate — how we know a rung failed

A ladder only works if you can detect failure. Five cheap checks:

| Check | Meaning |
|---|---|
| Word count far too low for the page size | OCR mostly failed |
| Mean confidence below ~0.72 (where reported) | Unreliable |
| Too many non-letter, non-number characters | Noise, not text |
| Tokens longer than 30 characters | Word boundaries collapsed |
| **Degeneracy check** (VLM only) | The model went into a loop |

**Useful baseline from the live run:** four healthy real extractions all landed
at `alpha_ratio` 0.788-0.798, `avg_word_len` 5.71-5.99, `long_token_frac` 0.0,
and 690-810 words per page. Use those bands as the "healthy" reference when
calibrating the gate on OCR'd pages.

---

## The degeneracy problem — very important

Modern AI OCR does not fail loudly any more. It fails **fluently**.

```
TESSERACT FAILS LIKE THIS          A VISION MODEL FAILS LIKE THIS
-------------------------          ------------------------------
Rev3nue rn5e 12,4B0                Revenue rose 12,480
   ^^^^^^^^^^^^^^^                    ^^^^^^^^^^^^^^^
   obviously broken                  looks perfect
   you will catch it                 the paper says 12,486
```

### Three failure modes

**1. Repetition loop.** On a dense table the model repeats a row until it runs
out of tokens. A 2026 Devanagari benchmark found one model producing output up
to **71× the correct length** on 2-3% of samples — with a median character
error rate of 100% and 89% of real-scan samples classed as catastrophic.

**2. Silent substitution.** An unusual number drifts toward a common one. The
output reads perfectly. The number is wrong.

**3. Dropped rows.** A 40-row table comes back with 38 rows. Nothing indicates
two are missing.

### How we catch it

```
if output length > 6 x the length of the PDF's own text hint
        -> reject, climb the ladder

if output has 8+ identical lines in a row
        -> reject, climb the ladder
```

**This guard is not optional.** A page that trips it escalates. It never
enters the corpus.

---

## A warning about "confidence"

A language model's confidence in `₹1,480.00` measures **how likely that string
is as language**, not whether the pixels say that.

So high confidence proves nothing about the picture. That is exactly why the
failure mode is *silent substitution* — unusual values drift toward common ones.

If you need real per-number confidence, it must come from bounding boxes and
cross-checks, not from the model's own score.

---

## Trick 1: document anchoring

From AllenAI's olmOCR.

When you send a page image to a vision model, **also paste in whatever text the
PDF already has**, even if partial or out of order, as a hint.

```
Prompt:
   "Transcribe this page exactly. Do not summarise or invent.

    Here is partial text from the PDF layer (may be incomplete,
    use only as a hint):
    <<<
    Industry Structure and Dev...ments
    The Company continu...
    >>>"

   [page image]
```

This measurably reduces made-up numbers on hybrid pages.

---

## Trick 2: write the OCR back into the PDF

`ocrmypdf` does something the others do not: it deskews, rotates, cleans, and
**writes a permanent text layer into a copy of the PDF**.

Why this matters: the next time you want to process that document — a better
segmenter, a different section — it costs **nothing**. The text is already
inside the file.

```
ocrmypdf --skip-text   ... for hybrid pages (keep existing text)
ocrmypdf --redo-ocr    ... for broken-text pages (throw old text away)
ocrmypdf --deskew      ... straighten a tilted scan
ocrmypdf --rotate-pages ... fix sideways pages
```

At 40,000 documents this pays for itself the first time you change your mind
about anything. And you will.

---

## What we picked

```
Rung 1   Tesseract           (English pages, clean scans)
Rung 2   PaddleOCR-VL        (self-hosted on a GPU, behind vLLM or SGLang)
Rung 3   Google DocAI        (when Hindi must be read)
Rung 3   Textract / Gemini   (hard English, ruled tables — 2-5% residue)

Plus     ocrmypdf            (writes the text layer back permanently)
```

**Serve rung 2 behind an OpenAI-compatible endpoint.** Then swapping
PaddleOCR-VL for MinerU2.5 or a cloud API is a config change, not a rewrite.

---

## What you must install before the full run

```powershell
winget install --exact --id tesseract-ocr.tesseract
winget install --exact --id QPDF.QPDF
```

Plus the Hindi language file `hin.traineddata` for Tesseract — though see
`13_HARD_PROBLEMS.md`: the recommendation is to **drop** Hindi pages, not read
them, so `hin` is only needed for script detection fallback.

---

## What goes wrong

| Problem | Fix |
|---|---|
| Model loops on a table | Length and repeated-line guards |
| Model invents a plausible number | Document anchoring + validate against XBRL |
| Rendering at 600 DPI is slow | Match DPI to the real image DPI |
| One page hangs forever | Timeout per page, then escalate |
| Hindi page sent to Textract | Route by script **before** choosing the engine |
| Tesseract not installed | The whole ladder silently does nothing — fail loudly instead |

---

## Exit test for this step

> Bake off PaddleOCR-VL vs MinerU2.5 vs olmOCR-2 **on your own scanned pages**.
>
> Score them on **fact-level accuracy** (numbers, units, entity names), NOT on
> edit distance. See `13_HARD_PROBLEMS.md` for why.
>
> Report measured cost per OCR page and measured fact accuracy on a held-out
> set of scanned financial pages.
