# 04 — STEP 2: FIND THE REPORT LINKS

`discover.py` · command: `python -m arpipe.cli discover`

---

## What it does

For each company and each year, find the URL of the annual report PDF.

**Status: working on NSE. Tested on 3 companies, found 4 reports.**

---

## Why we need it

There is no single place that has all of them. You must ask several places and
combine the answers.

---

## Option A — NSE API

```
https://www.nseindia.com/api/annual-reports?index=equities&symbol=TCS
```

Returns one row per year:

```json
{
  "companyName": "Tata Consultancy Services Limited",
  "fromYr": "2024",
  "toYr": "2025",
  "fileName": "https://nsearchives.nseindia.com/annual_reports/AR_26456_TCS_2024_2025_A_27052025233502.pdf",
  "attFileSize": "16.62 MB"
}
```

Verified live: TCS gave 16 years. Suprajit Engineering (small cap) gave 17
years, starting FY2009-10. Coverage is real, for big and small.

### The filename is free metadata — use it

Look at the real URLs from our run:

```
AR_24651_JISLDVREQS_2023_2024_25072024112050.pdf
   |     |          |    |    |
   |     |          |    |    +-- upload timestamp: 25 Jul 2024, 11:20:50
   |     |          |    +------- to year
   |     |          +------------ from year
   |     +---------------------- NSE symbol
   +---------------------------- NSE internal ID
```

```
AR_28538_JISLDVREQS_2024_2025_A_12115605_05092025125221.pdf
                                |  |
                                |  +-- extra numeric token (file size or seq)
                                +----- "A" marker on newer uploads
```

**Two useful things fall out of this:**

1. **A free cross-check.** The symbol and years in the filename must match what
   the API row claims. If they disagree, the row is suspect. Cheap to add,
   catches mis-filed attachments before you download.

2. **A format change to handle.** Newer files (FY2025) have the extra `_A_` and
   a numeric token; older ones (FY2024) do not. If you parse the filename by
   position, FY2025 breaks. Parse by **pattern**, not by counting underscores.

---

## Option B — BSE API

```
https://api.bseindia.com/BseIndiaAPI/api/AnnualReport_New/w?scripcode=500325
```

Needs `Referer: https://www.bseindia.com/` and `Origin` headers, or it returns
403.

**BSE has ~5,900 listed companies. NSE has ~2,870.**
So BSE is the **only** route to about 3,000 small and micro caps.

**Status: not wired yet.** This is the biggest coverage gap in the project
right now.

---

## Option C — screener.in

```
https://www.screener.in/company/RELIANCE/
```

Its Documents section lists annual reports by year, pointing at whichever
exchange holds each one. Good as a cross-check. Be polite — it is a third
party, not a regulator's archive.

---

## Option D — the company's own IR website

Only route to pre-2010. Different for every company. Slow to build. Save for
the companies you really care about.

---

## Option E — paid databases

CMIE Prowess, Capitaline, ACE Equity, LSEG.

---

## Good and bad

| Source | Good | Bad |
|---|---|---|
| NSE API | Clean JSON. Year + symbol in filename. Back to FY2009-10. | NSE-listed only. Needs cookies. Old years are `.zip`. |
| BSE API | Covers the ~3,000-company small cap tail | Needs special headers. Two URL formats by era. |
| screener.in | Union of both exchanges, easy to read | Third party. Do not make it primary. |
| Company IR site | Only route to pre-2010 | 5,000 different websites |
| Paid databases | Clean, restated, ready | Costs money. **Not needed for the PDFs.** |

---

## What we picked — the cascade

```
Try NSE first
    |
   found? --YES--> use it
    |
    NO
    |
    v
Try BSE
    |
   found? --YES--> use it
    |
    NO
    |
    v
Try screener.in
    |
   found? --YES--> use it
    |
    NO
    |
    v
Company IR site (only for companies we really care about)
```

Record **which source** gave each URL. It goes in the manifest — see the
`"source": "nse"` field in the real rows.

---

## On paid databases — the honest answer

**Do NOT buy them for the PDFs.** The exchanges give the PDFs away for exactly
our window (2010 onwards). We proved this live.

**But one thing IS worth paying for later:** a clean audited financial panel
(Prowess or Capitaline). Not for the text — for **checking numbers** in Step 9
and in table extraction. Rebuilding that panel from PDFs is a harder project
than the one we are doing.

Ask the university library on day 1. The answer takes weeks to arrive anyway.

---

## Free structured data to also grab

XBRL is machine-readable financial data. It is free.

| What | Where | From when |
|---|---|---|
| Financial results XBRL | NSE + BSE | April 2017 |
| BRSR XBRL (ESG, top 1,000) | NSE | FY2023 |
| Integrated Filing (Financial) | NSE | Q4 FY2024-25 |
| MCA XBRL | mca.gov.in | varies |

This gives tagged revenue, profit, EPS and ratios. We use it as **truth** to
check numbers pulled out of the PDFs.

---

## What goes wrong

| Problem | Fix |
|---|---|
| NSE returns 401 / empty | Load `nseindia.com` first for cookies, reuse the session |
| BSE returns 403 | Send `Referer` and `Origin` headers |
| Same year found on 2 sources | Keep both, rank NSE > BSE > screener, try in order |
| A year genuinely missing everywhere | Mark it "missing" — do not silently skip. The coverage report must show it. |
| Crawling too fast gets you blocked | 1 request per host per 1.5 seconds. This is a regulator's archive. Be polite. |
| Filename format changed between years | Parse by pattern, not by underscore position (see above) |
| **DVR line queried separately** | See `03_STEP1_COMPANY_LIST.md` — collapse to one company key first, or you download the same report twice |

---

## Exit test for this step

> Build a **coverage matrix**: company × year × source.
>
> Every empty cell must be classified as either "not listed that year" or
> "genuinely missing". No cell may be unexplained.
