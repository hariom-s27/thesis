# 10 — STEP 8: FIX READING ORDER AND CLEAN THE TEXT

`textlayer.py`

---

## What it does

Puts the words in the right order and removes junk.

---

## Why we need it

Text in the wrong order is useless for research. Repeated headers pollute every
analysis — the company name would dominate any word-frequency study.

---

## Problem 1 — Two columns

### The choices

| Method | How it works | Good | Bad |
|---|---|---|---|
| Sort by (y, x) | Top to bottom | Trivial | **Wrong on every two-column page** |
| **XY-cut** (Nagy's algorithm) | Find the widest empty vertical gap, split, repeat | Free, deterministic, **never invents text** | Struggles on magazine-style spreads |
| **XY-Cut++** (arXiv 2504.10258) | Pre-mask + multi-granularity + cross-modal matching | 98.8 BLEU, up to +24% over baseline | Newer, less battle-tested |
| LayoutReader / PP-DocLayoutV2 | Trained model predicts order | Handles odd layouts | Needs a GPU, more setup |
| Document VLM | Outputs order as part of OCR | Best quality | You pay for it anyway on OCR pages |

### What we picked

**XY-cut** for the free path, **VLM order** for OCR'd pages.
Upgrade to **XY-Cut++** once the labelled set exists and can measure the gain.

### How XY-cut works

```
+---------------------------+
| heading spans full width  |
+-------------+-------------+
| left col    | right col   |
| line 1      | line 1      |
| line 2      | line 2      |
+-------------+-------------+

Step 1: find the widest empty vertical band  ->  the gutter
Step 2: split into LEFT and RIGHT
Step 3: inside each half, find horizontal gaps, split again
Step 4: read LEFT fully, then RIGHT fully
```

Analogy: it is like slicing a cake along the gaps in the icing.

**One important property:** a geometric cut can be wrong, but it can never
*invent* text. A VLM can. For a research corpus that matters.

---

## The threshold that broke everything

Two-column academic papers have a wide gutter — about 5% of page width. Code
tuned for papers looks for that.

**Indian annual reports on A4 use an 18-30 point gutter, which is only 3-5% of
a 595-point page.**

We hit this in testing:

| Gutter threshold | Two-column pages correctly detected |
|---|---|
| 5% (academic default) | **0 of 28** |
| 2.5% with a 120-bin histogram | **24 of 28** |

**One number, copied from the wrong domain, silently broke a whole document
class.** Assume there are more of these.

### The second trap

Measure gaps using **line** boxes, not **block** boxes.

A two-column page is often just two big blocks — which carries **no gutter
signal at all**. If you histogram block boundaries you will find nothing.

---

## Problem 2 — Repeated headers and footers

Every page carries something like:

```
ACME INDUSTRIES LIMITED | Annual Report 2019-20        <- top of every page
                        47                              <- bottom of every page
```

If you leave these in:

- the company name dominates any "is this the right company" check
- word counts are wrong
- the text reads badly
- any word-frequency analysis is contaminated

**Fix:** collect the first two and last two lines of every page. Any line that
appears on more than ~35% of pages is furniture. Delete it.

**Guard:** only delete lines that are (a) repeated on many pages AND (b) short.
Otherwise you will delete a real heading that happens to recur.

---

## Problem 3 — Hyphenated words

```
"... the manage-
ment believes ..."     ->    "... the management believes ..."
```

Join a line ending in `-` with the next line **if** the next word starts
lowercase. If it starts uppercase, the hyphen is probably real (a compound
name).

---

## Problem 4 — Odd characters

```
ﬁ ﬂ ﬀ    ->  fi fl ff
' ' " "  ->  ' ' " "
– —      ->  -
•        ->  *
₹        ->  keep! this one is meaningful
```

Do **not** normalise `₹` away. The currency symbol is evidence.

---

## Why we know the cleaning is working

From the real manifest, all four documents:

```
"long_token_frac": 0.0
"avg_word_len":    5.71 - 5.99
"alpha_ratio":     0.788 - 0.798
```

`long_token_frac: 0.0` means **no token longer than 28 characters** in 39,000+
words across four documents.

That is the signature of clean word boundaries. If de-hyphenation or column
handling were broken, you would see run-on tokens here.

`avg_word_len` of 5.7-6.0 is right for English business prose. Damaged text
drifts up (concatenation) or down (fragmentation).

**These four documents give you a healthy baseline.** Anything in the full run
that falls far outside deserves a look.

---

## What goes wrong

| Problem | Fix |
|---|---|
| Three-column page | XY-cut recurses; cap at 3 columns |
| A sidebar next to body text | Learned reading-order model, or accept the imperfection |
| Header removal deletes a real heading | Only delete short lines that repeat on many pages |
| A table gets scrambled by XY-cut | Detect tables first and pass them through whole |
| Pull-quote in the middle of a column | XY-cut will split around it — usually fine, sometimes reorders |
| Rotated page | `ocrmypdf --rotate-pages` before extraction |

---

## Exit test for this step

> Take a known two-column page. Extract with naive order and with XY-cut.
>
> Both must give the **same word count**.
>
> But naive order must interleave sentences and XY-cut must not.
>
> Assert: a sentence from column 1 does not appear between two sentences of
> column 2.
