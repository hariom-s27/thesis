# 20 — SOURCES

Everything I read, grouped by why it mattered.

---

## Indian data sources

- [NSE — Corporate Filings: Annual Reports](https://www.nseindia.com/companies-listing/corporate-filings-annual-reports)
- [NSE — XBRL Filing Information](https://www.nseindia.com/static/companies-listing/xbrl-information)
- [BSE — About XBRL](https://www.bseindia.com/static/about/xbrl_info.aspx)
- [India XBRL Filings Explained — NSE/BSE filing types (TIGZIG)](https://www.tigzig.com/vigil/india-xbrl-filings)
- [XBRL in India: journey of XBRL reporting (DataTracks)](https://datatracks.com/in/blog/journey-of-xbrl-reporting-in-india/)
- [Screener — annual reports](https://www.screener.in/annual-reports/)
- [BennyThadikaran/NseIndiaApi](https://github.com/BennyThadikaran/NseIndiaApi) — unofficial NSE Python API
- [BennyThadikaran/BseIndiaApi](https://github.com/BennyThadikaran/BseIndiaApi) — unofficial BSE Python API
- [captn3m0/india-isin-data](https://github.com/captn3m0/india-isin-data/) — **ISIN prefix meanings: INE / IN9 / INF. This is what identified the DVR bug.**
- [VishwaGauravIn/screener-scraper-pro](https://github.com/VishwaGauravIn/screener-scraper-pro)
- [sahiljani/screener-india](https://github.com/sahiljani/screener-india)

---

## Regulation

- [SEBI LODR Schedule V](https://ca2013.com/schedule/lodr-schedule-v-2/) — **the exact MD&A content requirement and the 7+1 mandated ratios**
- [ICSI deck on MD&A, June 2023](https://www.icsi.edu/media/filer_public/21/a7/21a72c94-c540-4b07-9b1b-fcec707eedda/icsi_deck_on_mda_june23_.pdf)
- [SEBI LODR Regulation 34](https://ca2013.com/lodr-regulation-34)

---

## Projects that solved this problem elsewhere

| Project | Country | Link |
|---|---|---|
| Annual-report-to-MDA-txt | China (A-share) | [github](https://github.com/Xingyixxxx/Annual-report-to-MDA-txt) |
| edgar-crawler (WWW 2025) | US | [github](https://github.com/lefterisloukas/edgar-crawler) |
| EDGAR-CORPUS dataset | US | [huggingface](https://huggingface.co/datasets/eloukas/edgar-corpus) |
| rflugum/10K-MDA-Section | US | [github](https://github.com/rflugum/10K-MDA-Section) |
| michaelewens/MD-A-10-K-data | US | [github](https://github.com/michaelewens/MD-A-10-K-data) |
| CFIE-FRSE | UK | [github](https://github.com/drelhaj/CFIE-FRSE) |

**None for India.** That is the gap.

---

## Section segmentation research

- [A Scalable Framework for Table of Contents Extraction from Complex ESG Annual Reports](https://arxiv.org/abs/2310.18073) — **ESGDoc: 1,093 reports, 563 companies, 2001-2022. The construct/model/modify heading-tree method. The best upgrade available to our Step 6.**
- [HiPS — Hierarchical PDF Segmentation](https://arxiv.org/html/2509.00909v2) — outline-driven vs layout-mined pipelines; steal its evaluation design
- [NLTK segmentation metrics (Pk, WindowDiff)](https://www.nltk.org/_modules/nltk/metrics/segmentation.html)
- [segeval — segmentation evaluation package](https://github.com/cfournie/segmentation.evaluation)

---

## Reading order

- [XY-Cut++: Advanced Layout Ordering via Hierarchical Mask Mechanism](https://arxiv.org/abs/2504.10258) — 98.8 BLEU, up to +24% over baseline
- [LayoutReader: Pre-training of Text and Layout for Reading Order Detection](https://arxiv.org/abs/2108.11591)

---

## Document parsing and OCR

- [OmniDocBench (CVPR 2025)](https://github.com/opendatalab/OmniDocBench) · [paper](https://arxiv.org/abs/2412.07626)
- [OmniDocBench is saturated — what's next for OCR benchmarks (LlamaIndex)](https://www.llamaindex.ai/blog/omnidocbench-is-saturated-what-s-next-for-ocr-benchmarks)
- [PaddleOCR-VL: 0.9B multilingual document parsing](https://arxiv.org/html/2510.14528v1)
- [MinerU2.5](https://arxiv.org/abs/2509.22186)
- [olmOCR — document anchoring, ~$190/M pages](https://allenai.org/blog/olmocr)
- [olmOCR 2 — unit-test rewards](https://allenai.org/blog/olmocr-2)
- [Best Open-Source OCR and Document VLMs to Self-Host on GPU Cloud in 2026 (Spheron)](https://www.spheron.network/blog/best-open-source-ocr-vlm-self-host-gpu-cloud-2026/) — VRAM, throughput, break-even numbers
- [Docling vs Marker vs MinerU benchmark 2026](https://adityamangal98.medium.com/docling-vs-marker-vs-mineru-the-ultimate-open-source-pdf-parser-benchmark-2026-which-is-best-a36ecbb6c6b1) — speed, licences, **the Marker GPL-3 + RAIL-M restriction**
- [A Comparative Study of PDF Parsing Tools Across Diverse Document Categories](https://arxiv.org/pdf/2410.09871) — **10 parsers, 6 categories, DocLayNet. PyMuPDF/pypdfium won on Financial Reports; TATR won on financial tables. This validates our parser choice.**
- [OCRmyPDF](https://github.com/ocrmypdf/ocrmypdf)
- [Camelot — comparison with other table tools](https://camelot-py.readthedocs.io/en/latest/user/comparison.html)
- [Amazon Textract FAQs](https://aws.amazon.com/textract/faqs)
- [AWS Textract Guide: Features, Limits & Alternatives, Aug 2026](https://www.extend.ai/resources/aws-textract-when-to-use-alternative) — **confirms the six supported languages and the per-page pricing**

---

## The quality findings that shaped the design

- [FinCriticalED: A Visual Benchmark for Financial Fact-Level OCR](https://arxiv.org/abs/2511.14998) — **859 pages, 9,481 expert-verified facts, 13 systems. 95.71 ROUGE-1 with 54% monetary-unit accuracy. This is why text metrics are the wrong acceptance test.**
- [Can OCR-VLMs Read Devanagari? A Stress-Test Benchmark and Post-Correction Study](https://arxiv.org/html/2606.29213v1) · [code](https://github.com/Aditya-PS-05/devanagari-ocr-benchmark) — **10 systems on real Hindi scans. DeepSeek-OCR at 71x reference length. The ByT5 post-corrector that did not transfer.**
- [MDPBench: Multilingual Document Parsing in Real-World Scenarios](https://arxiv.org/html/2603.28130v1) — 3,400 images, 17 languages. Non-Latin scripts drop 14.0%. Hindi diacritics dropped.
- [LLM OCR — why the errors got harder to spot (LlamaIndex)](https://www.llamaindex.ai/blog/llm-ocr)

---

## Scale and orchestration

- [Scalable document processing with Ray Data (Anyscale)](https://www.anyscale.com/blog/ray-data-docling-rag-document-processing)

---

## Indian MD&A research

- [Development of a domain-specific dictionary for analysing MD&A reports: an Indian perspective](https://link.springer.com/article/10.1057/s41310-025-00313-3) — *International Journal of Disclosure and Governance*, 2025

---

## A note on confidence

Figures marked as estimates are order-of-magnitude planning numbers, to be
replaced by the triage pass (Stage 4) and the labelled set (weeks 3-4).

Benchmark scores are as published by the cited papers and vendors. The
Docling/Marker/MinerU throughput comparison and the Spheron GPU cost figures
are third-party blog benchmarks, **not controlled bake-offs** — treat them as
directional.

The pricing figures for Textract and Google Document AI are list prices as
documented in September 2026 and will change.
