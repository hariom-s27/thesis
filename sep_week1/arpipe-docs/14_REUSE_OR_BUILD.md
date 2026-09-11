# 14 — WHAT ALREADY EXISTS, AND WHAT WE MUST BUILD

---

## 14.1 — The closest thing to our project is Chinese, not American

**`Xingyixxxx/Annual-report-to-MDA-txt`** (GitHub)

This does **exactly our job** for Chinese A-share annual reports: batch MD&A
extraction from PDFs, with OCR fallback and LLM repair.

Three ideas worth copying:

| Idea | What it does |
|---|---|
| **Tiered fallback** | Normal extraction → `ocrmypdf` if text missing or garbled → LLM only if the start/end anchors cannot be found |
| **Token budgeting** | Estimates LLM cost from the gap between contents-page folio numbers and physical page labels, **before** calling |
| **Duplicate-character cleaning** | Treats broken-font artefacts as a first-class cleaning step, not an afterthought |

**Limitation:** built for Chinese reports and Chinese section names. The
architecture transfers; the patterns do not.

**What it confirms:** our design is the standard one. We are not doing anything
exotic. That is reassuring.

---

## 14.2 — The American reference: good structure, wrong extraction logic

**`lefterisloukas/edgar-crawler`** (WWW 2025) and **EDGAR-CORPUS**

The standard for "download filings, cut named sections, emit clean JSON".

| Take from it | Do not take from it |
|---|---|
| The output JSON contract | The extraction logic |
| Config-driven structure (which items, which years) | Regex on "Item 7" |
| Skip-already-done resumability | HTML parsing |

**The core difference in one line:**

```
US 10-K:               "Item 7." is always there.   -> regex works
Indian annual report:   no numbering at all.        -> regex is not enough
```

Also relevant:
- **`rflugum/10K-MDA-Section`** — US MD&A extraction
- **`michaelewens/MD-A-10-K-data`** — a ready MD&A dataset, 2002-2018.
  Proof that *the dataset itself* is the valuable output.

---

## 14.3 — The UK attempt

**`drelhaj/CFIE-FRSE`** — CFIE Final Report Structure Extractor

Detects section start/end pages in UK annual reports and classifies section
type (0-12). Same problem, real PDFs.

**But:** Java 8 only, no published algorithm, no accuracy numbers. Use as
inspiration, not as a dependency.

---

## 14.4 — Section segmentation research

### HiPS — Hierarchical PDF Segmentation (arXiv 2509.00909, 2025)

Two pipelines: one driven by the PDF outline, one that mines heading candidates
from layout whitespace and refines them with an LLM.

Its findings match ours:

| Finding | Matches our design |
|---|---|
| Outline-driven parser: median precision > 0.9 when metadata is complete | Our S1 is highest priority when bookmarks exist |
| Recall entirely determined by metadata completeness | Which is why we need S2-S5 as well |
| Docling over-segments | We do not use a generic converter for structure |
| GROBID and markdown converters flatten hierarchy | Same reason |

**Steal its evaluation design.** Report edit-distance-tolerant title
precision/recall, normalised tree edit distance for hierarchy, and **Pk /
WindowDiff** for boundary placement. Those are standard, so your numbers are
comparable with published work.

### ESGDoc — ToC extraction from ESG annual reports (arXiv 2310.18073)

**1,093 ESG annual reports from 563 companies, 2001-2022.** Public dataset.

Their method — "construct, model, modify":

1. **Construct** an initial heading tree from text blocks using reading order
   and font sizes
2. **Model** each node independently, using context from its surrounding subtree
3. **Modify** the tree by applying Keep / Delete / Move to each node

**Why this beats our flat per-page score:** it understands that "Risks and
Concerns" is a *child* of "Management Discussion and Analysis", not a sibling.
Our S5 just counts cues; it has no idea about nesting.

They report beating the previous state of the art at a fraction of the running
time, and it scales to documents of any length.

**Recommendation: prototype in week 5**, after the labelled set exists. Their
public dataset means you could even pre-train on it.

---

## 14.5 — Document parsing and OCR, the state in September 2026

### OmniDocBench (CVPR 2025) v1.5 / v1.6 — the main benchmark

| Model | Score | Size | Licence |
|---|---|---|---|
| PaddleOCR-VL-1.6 | 96.33 | 0.9B | Apache-2.0 |
| MinerU2.5-Pro | 95.75 | 1.2B | Apache-2.0 |
| GLM-OCR | 95.22 | 0.9B | MIT |

### olmOCR-bench (harder)

| Model | Score |
|---|---|
| Chandra 2 | 85.8 |
| dots.mocr | 83.9 |
| olmOCR 2 | 82.4 |
| Gemini 2.5 Flash | 76.4 |
| Marker 2 | 76.0 |
| MinerU pipeline | 72.7 |
| Docling (default) | 50.3 |

### MDPBench (17 languages, 3,400 images)

| Model | Overall |
|---|---|
| Gemini-3-Pro | 86.4% (leads on 14 of 17 languages) |
| dots.mocr | 80.5% (best open-source) |

Key gaps found: photographed documents drop **17.8%**; non-Latin scripts drop
**14.0%**.

### But the benchmarks are saturated

LlamaIndex made a point that matters for us: at 94%+, the remaining benchmark
gap is **edge-case fixing**, measured with exact-match metrics that punish
semantically equivalent output (an HTML table vs a markdown table).

> **Pick your engine on YOUR documents, not on the leaderboard.**

### Speed and hardware, from a 2026 third-party benchmark

| Tool | Speed | VRAM | Licence |
|---|---|---|---|
| Marker | ~120 pages/sec on H100 (batch) | 3-5 GB | **GPL-3 + RAIL-M, restricted above ~$2M revenue** |
| MinerU2.5 | ~2.1 p/s A100, ~4.5 p/s H200 | ≥8 GB | Apache-2.0 |
| PaddleOCR-VL | ~45 pages/min on L40S | ~2 GB | Apache-2.0 |
| Docling | slow, CPU-only fine | none | MIT |

Self-hosting break-even vs cloud is around **50,000-100,000 pages/month**.
We have 350,000+. So self-hosting wins clearly.

### Two architecture ideas worth importing regardless of engine

**MinerU2.5's coarse-to-fine split.** Layout analysis on a small downsampled
image; content recognition on full-resolution crops. Same idea as our cheap
triage → expensive local extraction.

**olmOCR's document anchoring.** Paste the PDF's own partial text into the
prompt as a hint. Measurably reduces invented numbers.

---

## 14.6 — Parser choice, backed by an academic study

A comparative study of **10 PDF parsing tools across 6 document categories**
(arXiv 2410.09871, using DocLayNet's 80,000+ annotated pages) found:

| Category | Text winner | Table winner |
|---|---|---|
| **Financial Reports** | **PyMuPDF, pypdfium** | **TATR** |
| Manuals | PyMuPDF, pypdfium | PyMuPDF |
| Government Tenders | PyMuPDF, pypdfium | Camelot |
| Scientific | Nougat (transformer) | TATR |

**This directly validates our choices:** PyMuPDF for text, TATR for financial
tables. Not a guess — a measured result on our document category.

---

## 14.7 — Reuse vs build

### Just use it — do not write this yourself

| Need | Use | Licence |
|---|---|---|
| PDF object model, text, outline | **PyMuPDF** (or pypdfium2 if AGPL is a problem) | AGPL-3 / BSD |
| Word-level geometry | pdfplumber | MIT |
| Damaged-file fallback | pypdf | BSD |
| Repair broken PDFs | **qpdf** | Apache-2 |
| Permanent OCR text layer | **ocrmypdf** | MPL-2 |
| Cheap OCR rung | Tesseract 5 | Apache-2 |
| Main OCR rung | **PaddleOCR-VL** served by vLLM/SGLang | Apache-2 |
| Ruled tables | Camelot | MIT |
| Complex tables | TATR / gmft | MIT/Apache |
| Company-name matching | rapidfuzz | MIT |
| Near-duplicate detection | datasketch (MinHash+LSH) | MIT |
| Segmentation metrics | nltk / segeval | Apache-2 / BSD |
| Exchange session handling | read `NseIndiaApi` / `BseIndiaApi` | MIT |
| Retry policy | tenacity | Apache-2 |

### Adapt from published work

| Need | Adapt from |
|---|---|
| Heading-tree section detection | ESGDoc construct/model/modify |
| Reading order | XY-Cut++ |
| Fact-level OCR evaluation | FinCriticalED fact categories |
| Evaluation design | HiPS (Pk, WindowDiff, tree edit distance) |
| Benchmark harness shape | OmniDocBench |
| Overall pipeline shape | Annual-report-to-MDA-txt (China) |

### Must build ourselves — nobody has this

| Thing | Why nobody has it |
|---|---|
| **NSE/BSE discovery + reconciliation for FY2010-25** | No public tool covers both across our window |
| **Symbol-change chaining + DVR collapsing** | India-specific |
| **Page-level routing and cost control** | Every framework is all-or-nothing per document |
| **The 5 MD&A strategies + arbiter for SEBI Schedule V** | The sub-heading cue list is unique to Indian regulation |
| **SEBI era rules** | Nobody has encoded these |
| **CIN/ISIN identity verification** | India-specific |
| **The lakh/crore/million unit resolver** | India-specific, highest-consequence piece of the whole thing |
| **The labelled Indian evaluation set** | Does not exist. **A publishable artefact on its own.** |

### Do NOT build

| Thing | Why not |
|---|---|
| Our own OCR model | Small VLMs are already at 96% OmniDocBench. Fine-tuning is a PhD, not a step. |
| An OCR post-corrector | The Devanagari study got +1.2 chrF++ and it did not transfer between engines. |
| A Hindi extraction path | MD&A is filed in English. The Hindi is a mirror. Detect, drop, record. |
| A custom orchestration framework | Under 50k documents, a process pool + JSONL manifest is enough. Resist the platform. |
| A review UI | A spreadsheet gets the same labels in 1% of the time. |
| Buying PDFs from a paid vendor | The exchanges give them away for our window. **Proven live.** |

### Buy, maybe, later

| Thing | When |
|---|---|
| Prowess / Capitaline **financial panel** | For validating extracted numbers. Not for the PDFs. Ask the library on day 1 — the answer takes weeks. |

---

## 14.8 — The gap, stated plainly

> **Nobody has built this for India.**

China has one. The US has several. The UK has an undocumented one.

India — 5,900 listed companies, 16 years of free archives, a regulator that
prescribes the section's exact contents — has none.

That is the gap, and it is real.
