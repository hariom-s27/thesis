# 06 — STEP 4: LOOK AT EACH PAGE (TRIAGE)

`triage.py` · command: `python -m arpipe.cli triage`

---

## What it does

For every page in every PDF, decide: can we read this page for free, or does
it need OCR?

**Status: working. 1,275 real pages analysed across 4 documents.**

---

## Why we need it

**This is the step that controls all the cost.** Get it right and you save 90%
of the OCR budget. Get it wrong and you either waste weeks of GPU time or you
silently lose pages.

---

## The big mistake everyone makes

Most tools ask: **"Is this document scanned?"**

That is the wrong question. Real annual reports are mixed.

```
DOCUMENT-LEVEL DECISION (wrong)
+---------------------------------------------+
| digital digital digital SCAN SCAN digital .. |
+---------------------------------------------+
        "mostly digital" -> skip OCR -> lose those pages
                or
        "has scans"      -> OCR all 445 -> waste 388 pages

PAGE-LEVEL DECISION (right)
+---------------------------------------------+
| free    free    free    OCR  OCR  free   ..  |
+---------------------------------------------+
        cost = exactly the pages that need it
```

The right question is: **"Can we read THIS PAGE?"**

### Live proof this matters

Jain Irrigation FY2024, from the real manifest:

```
"doc_kind": "mixed"
"frac_needing_ocr": 0.1284
"n_pages": 445
"ocr_pages": 0
```

**12.84% of 445 pages = about 57 pages needed OCR. We OCR'd zero.**

Why: none of those 57 pages were inside the MD&A span (209–226). They were
somewhere else in the book — signed certificates, pasted subsidiary accounts,
photo spreads.

A document-level router would have either OCR'd all 445 or skipped the
document. Page-level routing cost nothing.

---

## Five page types, not two

| Type | What it looks like | What to do | Where you find it |
|---|---|---|---|
| **digital** | Lots of text, copies out fine | Read the text — free | Most reports after 2016 |
| **scanned** | Almost no text, one big image | OCR | Pre-2014, PSUs, small caps |
| **hybrid** | Some text + a big image block | Read the text, OCR the image | Certificates, pasted accounts |
| **broken-text** | Text exists but is garbage | OCR, throw the text away | 2010-2014 old design software |
| **vector-text** | No text, no image, hundreds of tiny shapes | OCR | Letters converted to outlines |

### broken-text is the dangerous one

The page **has** text. Every tool returns something. The something is garbage.

A pipeline that only asks "is there text?" accepts it and quietly poisons the
dataset. Nothing errors. Nobody notices until a paper is written.

**The test that catches it:** count replacement characters and control codes.
If more than 2% of the characters are junk, treat the text layer as if it does
not exist.

---

## The signals we use — all cheap, no rendering

```
For each page, read from the PDF's internal structure:

  1. How many characters does the text layer give?
  2. How much of the page is covered by text boxes?
  3. How much is covered by images?
  4. How many junk characters are in the text?
  5. How many tiny drawing paths are there?
  6. What script is it (Latin vs Devanagari)?
  7. Is it one column or two?
```

---

## The speed discovery that matters a lot

The obvious way to inspect a page is `page.get_text("rawdict")`.

**Do not do this.** On an image-only page it copies the whole embedded image
into Python memory.

Measured on a 29-page scanned PDF:

| Method | Time | Output |
|---|---|---|
| `get_text("rawdict")` | **29.4 seconds** | same |
| geometry only (`dict` with text flags + `get_image_info`) | **0.23 seconds** | same |

**128× faster for identical output.**

Across 9 million pages, this is the difference between a few CPU-hours and a
few CPU-weeks.

---

## Pick the right DPI

DPI = dots per inch = how big we make the picture before OCR.

Rendering a 150-DPI fax at 600 DPI gives you nothing and costs 16× the pixels.

```
read the embedded image's real pixel size
    |
    v
work out its true DPI
    |
    v
render at that DPI, clamped between 200 and 400
```

Most Indian annual report scans sit at 200-300 DPI.

---

## Good and bad of triage approaches

| Approach | Good | Bad |
|---|---|---|
| No triage, OCR everything | Simple | 25× the cost. Weeks of GPU time. |
| Document-level triage | Simple-ish | Loses pages or wastes pages. Always wrong on mixed docs. |
| **Page-level from the object model** | Cheap, exact, gives a cost forecast before you spend | Needs thresholds tuned on real data |
| Page-level by rendering every page | Accurate | Rendering 9M pages is itself expensive |

---

## What we picked

Page-level triage, from the PDF object model, **no rendering**.

And we run it over the **whole corpus first**, as its own stage, before
spending anything on OCR. It costs a few CPU-hours. It turns the OCR budget
from a guess into a real number, broken down by year and company size.

---

## What the live run tells us — and what it hides

Real `frac_needing_ocr` values:

| Report | doc_kind | frac needing OCR |
|---|---|---|
| Jain Irrigation FY2025 | digital | 0.57% |
| Jain Irrigation FY2024 | **mixed** | **12.84%** |
| KRBL FY2024 | digital | 1.29% |
| KRBL FY2025 | digital | 1.23% |

**What this proves:** the classifier distinguishes digital from mixed on real
filings, and the numbers are plausible.

**What this hides — be honest:**

| Untested | Why it matters |
|---|---|
| No fully-scanned real document | The whole OCR path has never run on real data |
| No `broken-text` page seen | The most dangerous class is unvalidated |
| No `vector-text` page seen | Same |
| No bilingual document | Script routing never fired (`"bilingual": false` × 4) |
| Only FY2024 and FY2025 | The easy era. FY2010-2014 is where scans live. |
| Only 2 companies | Both mid-size, both NSE, both English |

**Four documents from the two easiest years of the sample is not validation.**
It is a smoke test that passed. Treat it as such.

---

## What goes wrong

| Problem | Fix |
|---|---|
| Text layer is garbage but tool accepts it | Junk-character ratio test |
| Page is a scan but has a small header of real text | Image-area test catches it → "hybrid" |
| Letters drawn as shapes | Count drawing paths → "vector-text" |
| Blank divider pages counted as "scanned" | Separate "blank" class, exclude from the fraction |
| Thresholds tuned on the wrong documents | Re-fit on 300 labelled real filings |

---

## Exit test for this step

> Run triage over the **whole corpus** before spending anything on OCR.
>
> Produce a table: page class × fiscal year × market-cap band.
>
> The OCR budget is no longer a guess. This is the cheapest,
> highest-information few hours in the whole project.
