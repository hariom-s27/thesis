# 05 — STEP 3: DOWNLOAD THE PDFs

`fetch.py` · command: `python -m arpipe.cli fetch`

---

## What it does

Downloads each PDF once, stores it once, never downloads it again.

**Status: working. 4 real PDFs downloaded. One bug fixed at `fetch.py:37`.**

---

## Why we need it

40,000 files. Some are 200 MB. Some are broken. Some are ZIPs. Some are the
same file served twice. If you handle this badly you will re-download for days.

---

## The choices

| Choice | Good | Bad |
|---|---|---|
| Save as `company/year.pdf` | Simple to browse | Same file stored many times; renaming a company breaks paths |
| Save by **SHA-256 hash** | Same file stored once. Re-runs cost nothing. Hash is proof. | Filenames look ugly |
| **Both — hash store + a folder of links** | Best of both | Slightly more code |

---

## What we picked — both

Bytes live once in a hash store. The nice folder tree is **hardlinks** into it,
so it costs no extra disk and can be rebuilt any time from the manifest.

```
store/
  blobs/47/74/47744fb5b66bf...610.pdf     <- real bytes, stored once

dataset/
  companies/KRBL_LIMITED__INE001B01026/
    2024/
      annual_report.pdf                    <- hardlink to the blob above
```

Analogy: the blob store is a warehouse where every box has a barcode. The
`dataset/` tree is a set of labels pointing at boxes. Two labels can point at
one box.

The real hashes from our run:

```
4f96f92101fb16a200798e89e430a36f9325fbebc5c1f347ebd0ee8b07700a9a  Jain FY2025
a1636fb3316f693d5f65a095977e6ce9bbbd52027e70679bba689cd4698d1965  Jain FY2024
47744fb5b66bf3c5c47e8647e30f91d1243c2a671d26b580275772feca3be610  KRBL FY2024
aebce9df42a3fec535b85099546b61d94c406086e2e183220c894808554d5d07  KRBL FY2025
```

All four different — so no duplicate bytes in this small sample. At full scale
you will see collisions (the same report from NSE and BSE) and the store will
silently keep one copy. That is the point.

---

## Four things the downloader must handle

### 1. ZIP files

NSE's older rows (before ~2016) are `.zip`, and some contain several PDFs — the
report, the AGM notice, subsidiary accounts.

**We unzip, keep the biggest PDF, and record the names of the others.**

*(Untested on real data — our 4 sample reports are FY2024/25, all plain PDFs.
This path only fires on pre-2016 filings, which we have not touched yet.)*

### 2. Broken PDFs

Some files have a damaged internal index and will not open. `qpdf` repairs
most of them.

```
try to open PDF
    |
   works? --YES--> continue
    |
    NO
    |
    v
run qpdf repair
    |
   works? --YES--> continue
    |
    NO
    |
    v
mark as failed, log it, move on
```

**qpdf is not installed on your machine.** Install it before the full run:

```
winget install --exact --id QPDF.QPDF
```

### 3. Encrypted PDFs

Some are "protected" with an **empty** password. Try the empty password before
giving up. Many Indian filings are like this — it is a printing artefact, not
real security.

### 4. Rate limiting

One request per host per 1.5 seconds. Back off hard on 403 / 429 / 503.

This is a regulator's archive being provided free. Being rude gets you blocked,
and getting unblocked is not a support ticket you can file.

---

## Storage — plan for this now

| Item | Size |
|---|---|
| Average annual report PDF | ~10-20 MB |
| Jain Irrigation FY2025 (351 pages) | large — check yours |
| 40,000 documents | **~500 GB to 1 TB** |
| After exact dedup | maybe 15-25% less |
| Per-page text (optional, recommended) | roughly doubles the text side, still small vs PDFs |

**Decide before you start:**

| Option | Disk | Trade-off |
|---|---|---|
| Keep every PDF forever | 500 GB - 1 TB | Full reproducibility. Recommended. |
| Keep PDFs only for high/medium tier | ~450 GB | Cannot re-check rejects |
| Keep only MD&A page ranges as new PDFs | ~30 GB | **Do not do this.** You lose the ability to extract any other section later. |

The third option looks tempting and is a trap. See `12_STEP10_STORE.md`.

---

## What goes wrong

| Problem | Fix |
|---|---|
| Same PDF served by NSE and BSE | Hash store keeps one copy |
| A 400 MB PDF blows up memory | Stream to disk, cap file size |
| Download dies halfway | Retry with backoff; hash check catches partial files |
| ZIP has 5 PDFs | Keep the largest, log the rest |
| Re-running the crawl | Skip anything already in the manifest |
| Disk fills at 3am on day 4 | Check free space before each batch; fail loudly, not silently |

---

## Exit test for this step

> Re-run `fetch`. It should download **nothing**.
>
> If it re-downloads, resumability is broken and the full crawl will take
> twice as long as it should.
