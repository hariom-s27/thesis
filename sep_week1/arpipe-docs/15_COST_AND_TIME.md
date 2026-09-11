# 15 — MONEY AND TIME

---

## 15.1 — How big is this really

| Thing | Number |
|---|---|
| Companies listed on BSE | ~5,900 |
| Companies listed on NSE | ~2,870 |
| **Your current master (NSE only)** | **2,571** |
| Companies with usable 2010-25 history | ~2,500 after survivorship |
| Documents (16 years, minus gaps) | ~40,000 |
| Pages (at a ~220-page average) | **~9,000,000** |
| Raw PDF storage | 500 GB - 1 TB |
| **MD&A pages — what we actually want** | **~350,000 (about 4%)** |

That last line is the whole argument for the design.

### The 4% is confirmed on real data

From your live run:

| Report | Pages | MD&A pages | Share |
|---|---|---|---|
| Jain Irrigation FY2025 | 351 | 22 | 6.3% |
| Jain Irrigation FY2024 | 445 | 18 | 4.0% |
| KRBL FY2024 | 155 | 7 | 4.5% |
| KRBL FY2025 | 324 | 7 | 2.2% |
| **Average** | **319** | **13.5** | **4.3%** |

The planning assumption holds.

### Reports have grown

A 2010 filing is 90-150 pages. A 2024 filing is 250-450 pages.

Why: BRR (FY2013), CSR (FY2015), the ratio table (FY2020) and BRSR (FY2023)
each added sections.

**Consequence:** your average-pages estimate should be year-weighted, not flat.
Later years cost more per document.

---

## 15.2 — What the ordering saves

Per fully-scanned 300-page report:

| Approach | OCR pages | Comment |
|---|---|---|
| OCR everything, then segment | **300** | The default in most parse frameworks |
| Front matter + 1-in-6 sample, then span | **~70** | 14 front + ~48 sampled + ~15 span |
| Same, but bookmarks or contents page hit | **~20** | The sample is skipped entirely |

### Live proof, on a real filing

Jain Irrigation FY2024:

```
n_pages:            445
frac_needing_ocr:   0.1284    -> about 57 pages are scanned
ocr_pages:          0         -> we OCR'd none of them
```

None of the 57 scanned pages fell inside the MD&A span (209-226).

```
Locate-then-OCR:     0 OCR pages
OCR-then-locate:    57 OCR pages, plus processing all 445
```

**Honest caveat:** on a *short* scanned document the fixed front-matter cost
dominates. Our 29-page fully-scanned synthetic test cost 25 OCR pages — no
saving at all. The saving is real on the 150-450 page documents that make up
the actual corpus. And triage tells you which those are **before** you commit.

---

## 15.3 — Budget

Full corpus: 40,000 documents, ~9M pages.

| Stage | Scale | Cost | What drives it |
|---|---|---|---|
| Discovery + download | ~1 week wall clock | bandwidth + 500 GB - 1 TB disk | **Politeness delay, not compute** |
| **Triage (all pages)** | ~9M pages | **a few CPU-hours** | ~0.01 s/page, no rendering |
| Text-layer extraction | ~7-8M pages | CPU-days | Parallelises trivially |
| OCR, self-hosted VLM | ~0.3-1M pages | **~$60-200 GPU** | At the ~$190/M reference |
| OCR residue, cloud API | 2-5% of the above | ~$25-75 | Textract / DocAI list prices |
| LLM adjudication | 5-10% of documents | ~$40-150 | 2-6k tokens per adjudicated doc |
| **Human review** | ~1,500 documents | **60-75 person-hours** | ~2-3 min each |

### The conclusion

> **The compute is nearly free. The expensive line is human review.**

Total machine cost is plausibly **under $500**. Total human cost is **two
working weeks of someone's attention**.

And human review is a direct function of how good segmentation and verification
are.

**Which is why the labelled 300-document evaluation set is the
highest-leverage week in the entire plan.** Every point of accuracy you gain
there removes person-hours later.

---

## 15.4 — Wall-clock time, realistically

| Stage | Time | Can it run overnight? |
|---|---|---|
| Universe | minutes | n/a |
| Discovery (40,000 lookups at 1.5s) | **~17 hours minimum** | yes, and it must |
| Download (40,000 files) | 2-5 days | yes |
| Triage (9M pages) | 4-12 hours on all cores | yes |
| Extract, no OCR (~85% of docs) | 1-2 days | yes |
| Extract, with OCR (~15%) | 2-5 days on one GPU | yes |
| Audit | minutes | n/a |

**The politeness delay dominates discovery and download.** You cannot compress
it without risking a ban. Plan for a week of mostly-waiting at the front.

**Start discovery and download first, on day 1**, and do all your threshold
work while it runs.

---

## 15.5 — Orchestration

Run stages as **separate commands** over a shared manifest, not one monolith.

Why: the stages have completely different resource profiles.

| Stage | Bottleneck | Wants |
|---|---|---|
| Discovery | Network, rate-limited | 1 patient process |
| Download | Network + disk | 4-8 workers |
| Triage | CPU, cheap | all cores |
| Extract / OCR | GPU, expensive | GPU batching |
| Audit | Trivial | 1 process |

If you couple them, **the GPU sits idle behind a politeness delay.** That is
the single most expensive mistake in the whole build.

| Scale | Use |
|---|---|
| Under ~50,000 documents | A process pool per stage + JSONL manifest. **Genuinely enough. Resist the platform.** |
| Beyond that, or with a GPU fleet | Ray Data for the OCR stage, Prefect or Airflow for sequencing and retries |
| The VLM itself | Serve behind an OpenAI-compatible endpoint (vLLM or SGLang), so swapping engines is a config change |

---

## 15.6 — Decide these three things before you start

### 1. NSE only, or NSE + BSE?

| Choice | Companies | Documents | Extra effort |
|---|---|---|---|
| NSE only | 2,571 | ~25,000 | 0 — already done |
| NSE + BSE | ~5,900 | ~40,000 | 1-2 days to wire the BSE master |

**Recommendation: NSE + BSE.** Small caps are where disclosure quality varies
most, and an NSE-only panel has a size bias baked in.

### 2. All 16 years, or a shorter window?

| Window | Documents | Scanned share | Difficulty |
|---|---|---|---|
| FY2019-2025 | ~15,000 | low | easy — mostly digital |
| FY2015-2025 | ~28,000 | medium | moderate |
| FY2010-2025 | ~40,000 | high | hard — this is where OCR matters |

**If your research question needs a long panel, do all 16.** If it needs
post-BRSR climate disclosure, FY2019+ is enough and half the work.

### 3. How much disk?

Plan for **1 TB**. You can prune later; you cannot un-delete.
