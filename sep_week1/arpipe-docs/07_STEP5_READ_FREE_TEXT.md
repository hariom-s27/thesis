# 07 — STEP 5: READ THE PAGES WE CAN READ FOR FREE

`textlayer.py`

---

## What it does

Pulls the text out of the pages triage marked as `digital`.

**Status: working on real data. All 4 live extractions used this path only —
zero OCR pages.**

---

## Why we need it

It is free and instant. On a modern report this is 95%+ of the pages.

And it gives us the raw material for Step 6 (finding the MD&A) **without
spending a rupee on OCR**. That ordering is the whole design.

---

## The choices

| Library | Good | Bad | Licence |
|---|---|---|---|
| **PyMuPDF** | Fastest. Gives font size, position, images, bookmarks. | AGPL — check before commercial use | AGPL-3.0 |
| pdfplumber | Great word/table geometry. Easy API. | Slower | MIT |
| pdfminer.six | Pure Python, no binaries | Slow | MIT |
| pypdfium2 | Fast, permissive licence | Less layout detail | BSD/Apache |
| pdftotext (poppler) | Very fast, simple | Little structure info | GPL |

An academic comparison of 10 parsers across 6 document types found **PyMuPDF
and pypdfium won on Financial Reports** for text extraction. So this is not
just a speed choice — it is the right choice for our document type.

---

## What we picked

**PyMuPDF** as the main engine, because:

1. We need **font sizes and positions** for Step 6 (strategy S3 — typographic
   headings). Most simpler libraries do not give this.
2. We need **bookmarks** for strategy S1.
3. We need **speed** for 9M pages.

**The AGPL warning:** PyMuPDF is AGPL-3.0. For a university thesis this is
fine. If this ever ships as a product, either buy the Artifex commercial
licence or swap to **pypdfium2 + pdfminer.six**, which does the same job more
slowly.

Write the parser behind a thin interface now so that swap is a config change,
not a rewrite.

---

## The trap: reading order

This is important and easy to miss.

Most libraries sort text blocks top-to-bottom, left-to-right. On a two-column
page that **mixes the two columns together**:

```
WHAT'S ON THE PAGE                 WHAT NAIVE SORTING GIVES YOU
+-------------+-------------+
| The company | Revenue     |      "The company Revenue"
| grew fast   | rose 12%    |      "grew fast rose 12%"
| this year   | over last   |      "this year over last"
+-------------+-------------+
```

The text looks fine to a computer. It is nonsense to a human and to a language
model.

**MD&A and Corporate Governance are the two most commonly two-column sections
in an Indian annual report.** So this hits us exactly where it hurts.

Fix: see `10_STEP8_CLEAN_TEXT.md`.

---

## A quality signal worth adding: words per page

From the live run:

| Report | MD&A pages | Words | Words per page |
|---|---|---|---|
| Jain Irrigation FY2025 | 22 | 15,195 | 691 |
| Jain Irrigation FY2024 | 18 | 13,031 | 724 |
| KRBL FY2024 | 7 | 5,654 | 808 |
| KRBL FY2025 | 7 | 5,261 | 752 |

**Range: 691 to 808 words per page. Very tight.**

That is a useful free check. Add it to QC:

```
words_per_page = n_words / (end_page - start_page + 1)

if words_per_page < 250   -> suspicious: mostly graphics, or OCR failed
if words_per_page > 1200  -> suspicious: span may include dense tables
                             or the page count is wrong
```

Our four real reports all sit comfortably in a 690-810 band. A document that
came back at 120 words per page would be worth looking at by hand — and right
now nothing would flag it.

---

## Other quality signals already in the manifest

The live rows carry these:

```
"alpha_ratio":      0.788 - 0.798     letters as a share of characters
"digit_ratio":      0.021 - 0.026     digits as a share
"avg_word_len":     5.71 - 5.99       average word length
"long_token_frac":  0.0               share of tokens > 28 chars
```

**All four documents are almost identical on these.** That is what healthy
extraction looks like:

| Signal | Healthy | Warning sign | Means |
|---|---|---|---|
| `alpha_ratio` | 0.75-0.85 | below 0.65 | too much punctuation or noise |
| `digit_ratio` | 0.02-0.05 | above 0.25 | you captured a financial statement, not prose |
| `avg_word_len` | 5.5-6.5 | below 4 or above 8 | OCR damage or wrong language |
| `long_token_frac` | 0.0 | above 0.02 | word boundaries collapsed |

Because these four are so consistent, they make a good **baseline**. Anything
in the full run that falls far outside these bands deserves a look.

---

## What goes wrong

| Problem | Fix |
|---|---|
| Two columns interleaved | XY-cut — see `10_STEP8_CLEAN_TEXT.md` |
| Header/footer repeated on every page | Strip lines that repeat on many pages |
| Words broken across lines with a hyphen | Re-join them |
| Weird characters (ﬁ ﬂ ' ") | Normalise them |
| Text layer is present but garbage | Triage should have caught it — if not, the mojibake threshold is wrong |

---

## Exit test for this step

> On a known two-column page, extract with naive order and with XY-cut.
>
> Both must have the **same word count**.
>
> But naive order must interleave sentences and XY-cut must not. Assert that a
> sentence from column 1 does not appear between two sentences of column 2.
