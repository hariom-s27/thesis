# Climate Change Exposure — Reproduction & Extended Validation

Reproduces the **CCExposure** measure of Sautner, van Lent, Vilkov & Zhang (2023,
*Journal of Finance*) from real earnings-call transcripts, using the authors'
own released bigram dictionaries, then extends it with additional validation
checks (TF-IDF weighting, sentiment, risk framing, robustness, event studies,
external validity).

## What's here

| File | Purpose |
|---|---|
| `week1_thesis/exact_reproduction.py` | Phase 1 — reproduces CCExposure (Eq. 1) on a small set of local PDF transcripts, validated against ExxonMobil's official published score. |
| `week1_thesis/exact_reproduction_api.py` | Same as above, but reading `.txt` transcripts pulled from the Alpha Vantage API instead of local PDFs. |
| `week1_thesis/phase2_sentiment_risk.py` / `phase2_api.py` | Phase 2 — adds CCSentiment (Eq. 2) and CCRisk (Eq. 3); the `_api` version runs on API-sourced transcripts. |
| `week1_thesis/phase3_tfidf.py` | Phase 3 — TF-IDF-weighted exposure (Eq. 4); unvalidated against the official CSV (no TF-IDF column published), so validated indirectly (see Phase 4). |
| `week1_thesis/phase4_tfidf_and_risk.py` | Phase 4 — validates Eq. 4 indirectly via its published correlation with Eq. 1, and runs a train/test split-sample check on the risk-synonym list (Eq. 3) to avoid overfitting an unpublished vocabulary. |
| `week1_thesis/phase5_validation_suite.py` | Phase 5 — replicates the authors' own validation exercises (measure correlations, seed-vs-discovery comparison, bigram perturbation test). |
| `week1_thesis/phase6_analysis_suite.py` | Phase 6 — reruns the authors' *validation logic* (not number-matching) on our own data: firm profiles, cross-firm ranking, time trends, industry variation, variance decomposition. |
| `week1_thesis/phase7_extended_validation.py` | Phase 7 — placebo/negative-control test, split-half reliability, preprocessing robustness, a Paris-Agreement (2015) event study, a human-audit export, and external validity vs. 10-K MD&A scores. |
| `week1_thesis/phase8_inference.py` | Phase 8 — statistical inference: firm-clustered bootstrap confidence intervals, a permutation test against a scrambled-word-order null, and split-stability of the risk-synonym list. |
| `week1_thesis/audit_bigrams.py` | Opens the black box: shows exactly which dictionary bigrams matched, dictionary coverage, and sample matched sentences for manual review. |
| `week1_thesis/gap_analysis.py` | Diagnoses *where* the reproduction falls short of the official numbers — systematic (one shared cause) vs. scattered (small-denominator noise) error. |
| `week1_thesis/analyze_trends.py` | Scores every transcript on disk (exposure + sentiment/risk) and aggregates to firm-year, for trend analysis across firms and years. |
| `week1_thesis/collect_bulk_transcripts.py` | Original Alpha Vantage transcript collector (single API key, resumes across daily quota resets). |
| `week1_thesis/collect_multi_provider.py` | Extended collector — supports a pool of API keys, per-minute pacing backoff, a persisted confirmed-empty skip-list, and network-error retries. |
| `week1_thesis/fetch_transcripts_fmp.py` / `fetch_transcripts_alphavantage.py` | One-off scripts used to test each transcript API's coverage/quality before committing to it for bulk collection. |
| `week1_thesis/climate_exposure_full_algorithm.ipynb` | Notebook version of the core algorithm. |

## Pipeline order

All result files land in one place: `outputs/` at the repo root.

1. Collect transcripts — `collect_multi_provider.py` (writes transcripts to `api_transcripts/`, logs to `outputs/download_log.csv` and `outputs/confirmed_empty.json`).
2. Score exposure — `exact_reproduction_api.py` or `score_and_correlate.py` → `outputs/validation_results.csv`.
3. Add sentiment/risk — `phase2_api.py`.
4. TF-IDF + risk-list validation — `phase3_tfidf.py`, `phase4_tfidf_and_risk.py` → `outputs/phase4_results.csv`.
5. Full validation suite — `phase5_validation_suite.py` → `outputs/phase5_validation.csv`.
6. Analysis suite — `phase6_analysis_suite.py` → `outputs/phase6_firm_profiles.csv`, `outputs/phase6_firmyear_analysis.csv`.
7. Extended validation — `phase7_extended_validation.py` → `outputs/c1_placebo.csv`, `outputs/c5_splithalf.csv`, `outputs/c6_robustness.csv`, `outputs/audit_coding_sheet.csv`, `outputs/c7_external_validity.csv`.
8. Inference — `phase8_inference.py` → `outputs/phase8_bootstrap_ci.csv`, `outputs/phase8_permutation.csv`.
9. Audit — `audit_bigrams.py` → `outputs/audit_matched_bigrams.csv`, `outputs/audit_sentences.csv`.

## Setup

```
python -m venv .venv
.venv\Scripts\activate
pip install pdfplumber spacy nltk scikit-learn pandas requests pysentiment2
python -m spacy download en_core_web_sm
```

Create `week1_thesis/.env` (never committed — see `.gitignore`) with:
```
AV_API_KEY=your_alphavantage_key
# or a pool of keys for collect_multi_provider.py:
AV_API_KEYS=key1,key2,key3
```

## Data notes

- `api_transcripts/`, `old _work/` (the authors' released bigram dictionaries
  and official score CSVs), and `*.pkl` files are **not** committed — they're
  either large, regenerable, or licensed replication data that shouldn't be
  redistributed. Re-download/re-run to regenerate them locally.
- Result CSVs/JSON all live in `outputs/` (`validation_results.csv`,
  `phase4_results.csv`, `phase5_validation.csv`, `phase6_*.csv`,
  `phase8_*.csv`, `firm_year_trends.csv`, `download_log.csv`,
  `confirmed_empty.json`, `ticker_isin_map.json`, audit/`c1`–`c7` CSVs) *are*
  committed, since they're the actual output of the pipeline and small enough
  to track directly.
