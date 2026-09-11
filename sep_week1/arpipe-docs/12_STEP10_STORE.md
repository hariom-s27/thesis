# 12 — STEP 10: SAVE IT, GRADE IT, KEEP THE PROOF

`store.py` · one bug fixed at `store.py:121`

---

## What it does

Writes the output and the evidence.

**Status: working. JSONL and Parquet manifests written for 4 real documents.**

---

## Why we need it

A text file with no provenance is not a dataset.

The first time someone asks *"is this really FY2013 and really this company?"*,
you need the answer on disk. You cannot reconstruct it later.

---

## The folder layout

```
store/
  blobs/47/74/47744fb5b66bf...610.pdf     <- real bytes, once, immutable

dataset/
  companies/KRBL_LIMITED__INE001B01026/
    2024/
      annual_report.pdf                    <- hardlink into blobs/
      mda.txt                              <- THE DELIVERABLE
      mda.json                             <- span, method, verification, QC
      document.json                        <- source URL, sha256, pages, producer
      pages/0027.txt ...                   <- optional: text of every page
    2025/
      ...
  manifest.jsonl                           <- one line per document, append-only
  manifest.parquet                         <- snapshot for analysis
```

---

## What goes in `mda.json` — a real one

This is an actual row from your live run, annotated:

```json
{
  "company_id": "INE001B01026",
  "fy_end": 2024,
  "sha256": "47744fb5b66bf...610",          <- ties text to exact bytes
  "ok": true,
  "confidence": "high",

  "span": {
    "start_page": 27,
    "end_page": 33,
    "method": "heading+refined+trimmed",     <- WHICH method won, and that
    "heading_text": "Management Discussion   <- both refinement steps ran
                     and Analysis",
    "score": 0.99
  },

  "verification": {
    "company_ok": true,
    "year_ok": true,
    "company_evidence": [
      "cin:L01111DL1993PLC052845",
      "name:KRBL Limited:100"
    ],
    "year_evidence": ["modal_fy:2024:w59"],  <- 59 weighted mentions
    "name_similarity": 100.0,
    "cin_found": "L01111DL1993PLC052845",
    "isin_found": null,                      <- THE BUG (see 11_STEP9)
    "fy_found": 2024,
    "notes": []
  },

  "n_words": 5654,
  "ocr_pages": 0,
  "ocr_engine": null,

  "qc": {
    "alpha_ratio": 0.788,
    "digit_ratio": 0.026,
    "avg_word_len": 5.71,
    "long_token_frac": 0.0,
    "ratio_cues": 7,                         <- found the mandated ratios
    "leaks": [],                             <- no section bleed
    "diag": {
      "candidates": [                        <- what EVERY method said
        ["toc",          53, 66, 0.8],       <- TOC was wrong (53-66)
        ["heading",      27, 33, 0.92],      <- winner
        ["heading_text", 29, 33, 0.6],
        ["body_score",   27, 34, 0.72]
      ],
      "supporters": 2                        <- 2 methods agreed
    },
    "doc_kind": "digital",
    "frac_needing_ocr": 0.0129,
    "bilingual": false,
    "n_pages": 155
  },

  "pipeline_version": "0.1.0"
}
```

### Why the `diag.candidates` list is the best field in the file

Look at KRBL FY2024. The TOC method said **pages 53-66**. The winner said
**27-33**. The TOC was wrong by 26 pages.

Without `candidates`, you would never know that. With it, you can ask
across the whole corpus: *how often is the TOC method wrong, and by how much?*

That is what tells you where to spend next week. **Keep this field. Never
drop it to save space.**

---

## Three design rules

### Rule 1 — Append-only JSONL is the source of truth

Parquet is a **derived** snapshot. If the job crashes mid-run you lose one
line, not the whole manifest.

Your run already does both. Good.

### Rule 2 — Resume on `(company_id, year)`

You will re-run extraction a dozen times while the download runs once.
Every stage must skip completed work.

### Rule 3 — Keep the per-page text

This roughly doubles your text-side disk. **It is almost always worth it.**

Why: every future section you decide to extract — Directors' Report, Corporate
Governance, BRSR, risk factors — then costs a **regex pass** instead of a
**re-run of the whole OCR budget**.

```
WITHOUT per-page text            WITH per-page text
---------------------            ------------------
Want Corporate Governance too?   Want Corporate Governance too?
   |                                |
   v                                v
Re-open every PDF                Load saved page text
Re-OCR everything    <-- $$$     Run new heading pattern
   |                                |
   v                                v
Days of GPU                      Minutes of CPU
```

**This is the single highest-return storage decision in the project.**

---

## A path problem worth fixing now

Your live manifest has Windows paths with backslashes:

```json
"mda_path": "live_dataset_clean\\companies\\KRBL_LIMITED__INE001B01026\\2024\\mda.txt"
```

Two issues:

1. **Backslashes break on Linux.** If you ever move the dataset to a server or
   share it, these paths are dead.
2. **They are relative to wherever you ran the command.** Fine now, fragile
   later.

**Fix:** store paths as **forward-slash, relative to the dataset root**:

```json
"mda_path": "companies/KRBL_LIMITED__INE001B01026/2024/mda.txt"
```

One line: `str(path.relative_to(root)).replace("\\", "/")`.

Do it now, before you have 40,000 rows to migrate.

---

## Another small thing: `path` duplicates `mda_path`

Your rows carry both:

```json
"mda_path": "live_dataset_clean\\companies\\...\\mda.txt",
"path":     "live_dataset_clean\\companies\\...\\mda.txt"
```

Identical. Drop one, or give them different jobs (e.g. `mda_path` for the text,
`dir` for the folder).

---

## Deduplication audit — add this to `audit`

```
1. Group by sha256.
   Two rows, same hash, different company_id?
      -> the DVR bug (see 03_STEP1_COMPANY_LIST.md). Keep the primary.

2. Group by (CIN, fy_end).
   More than one row?
      -> duplicate company key. Investigate.

3. MinHash the mda.txt within each company across adjacent years.
   Near-identical?
      -> either a mis-filed year, or heavy boilerplate reuse.
         Both are worth knowing.
```

---

## Storage plan

| Item | Size |
|---|---|
| 40,000 PDFs | ~500 GB - 1 TB |
| After exact dedup | maybe 15-25% less |
| Per-page text | small relative to PDFs, worth every byte |
| `mda.txt` files | trivial (~15k words each) |
| Manifests | trivial |

**Decide before you start:**

| Option | Disk | Trade-off |
|---|---|---|
| Keep every PDF forever | 500 GB - 1 TB | Full reproducibility. **Recommended.** |
| Keep PDFs only for high/medium tier | ~450 GB | Cannot re-check rejects |
| Keep only MD&A page ranges as new PDFs | ~30 GB | **Trap.** You lose the ability to extract any other section, ever. |

---

## What goes wrong

| Problem | Fix |
|---|---|
| Disk fills up | Hash store dedupes; check free space before each batch |
| Manifest corrupted by a crash | Append-only JSONL, one JSON per line |
| Company renamed — folder name is stale | Folder name includes the ISIN; rebuild the tree from the manifest any time |
| Two runs write at once | One writer per manifest, or one manifest per shard |
| **Windows paths in the manifest** | **Store forward-slash relative paths — see above** |
| Parquet and JSONL disagree | Always regenerate Parquet from JSONL, never the other way |
