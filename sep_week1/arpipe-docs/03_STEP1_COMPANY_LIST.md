# 03 — STEP 1: MAKE THE COMPANY LIST

`universe.py` · command: `python -m arpipe.cli universe`

---

## What it does

Builds one master table of every company we want, with stable ID numbers.

**Status: working. 2,571 NSE companies downloaded live.**

---

## Why we need it

Company names change. Ticker symbols change. Companies merge.

Real example:

```
2018:  IIFL HOLDINGS
2020:  IIFL WEALTH MANAGEMENT     (same company, new symbol)
2023:  360 ONE WAM                (same company, new symbol again)
```

If you search only for `360ONE`, you get 2023–2025 and you **silently lose**
2010–2022. Nothing errors. The data is just missing.

This is the most common quiet failure in a long panel.

---

## The choices

| ID type | Who gives it | Survives name change? | Survives symbol change? | Where to get it |
|---|---|---|---|---|
| **ISIN** | NSDL/CDSL | Yes | Yes | Both exchange master files |
| **CIN** | MCA | Yes | Yes | Printed inside the report |
| BSE scrip code | BSE | Yes | Yes (BSE only) | BSE master |
| NSE symbol | NSE | No | No | NSE master |
| Company name | nobody | No | No | Last resort only |

### Good and bad

| Option | Good | Bad |
|---|---|---|
| ISIN as key | Stable. In both exchange files. Free. | Can change on restructuring. **A company can have more than one ISIN.** (see the bug below) |
| CIN as key | Most stable of all | Not in exchange files — you must read it out of the PDF |
| Symbol as key | Easy, human readable | Breaks. Loses years. Never do this. |
| Buy a mapping (CMIE / Capitaline) | Clean and done for you | Costs money. Not needed — the free files work. |

---

## What we picked

- **ISIN is the main key.**
- **CIN is the double-check** — read from inside the PDF in Step 9.
- Symbol history is chained so old names stay searchable.

Free files:

```
https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv
    -> symbol, company name, ISIN, listing date

https://nsearchives.nseindia.com/content/equities/symbolchange.csv
    -> old symbol, new symbol, date

BSE "List of Scrips"
    -> scrip code, ISIN, name, group, status
```

### The chaining

The symbol-change file is a flat list. A company that renamed twice needs
**chaining**:

```
file says:   IIFLHOLDINGS -> IIFLWAM
file says:   IIFLWAM      -> 360ONE

we compute:  360ONE  has aliases  [IIFLWAM, IIFLHOLDINGS]
```

Our code does this. It is tested and works.

---

## BUG FOUND IN THE LIVE RUN — read this

Look at the company_id for Jain Irrigation in the real manifest:

```
"company_id": "IN9175A01010"
"declared_name": "Jain Irrigation Systems Limited"
url contains: JISLDVREQS
```

**`IN9175A01010` is not the main equity ISIN. It is the DVR ISIN.**

Indian ISIN prefixes tell you the issuer/security type:

| Prefix | Meaning |
|---|---|
| `INE` | Company, statutory corporation, banking company — the normal equity line |
| `IN9` | Also a company line — used for additional series when the INE space is used |
| `INF` | Mutual funds |

Jain Irrigation has **two listed lines**:

```
JISLJALEQS   ordinary shares      ISIN INE175A01038
JISLDVREQS   DVR shares           ISIN IN9175A01010
```

**Both point at the same annual report PDF.**

### Why this matters

| Problem | Effect |
|---|---|
| Same report processed twice | Wasted OCR budget, duplicate rows in the panel |
| Panel has two rows per company-year | Any regression double-counts Jain Irrigation |
| The "right" ISIN is ambiguous | Which one joins to the financial data? |
| CIN verification still passes | `L29120MH1986PLC042028` matches both — so verification does **not** catch this |

Note that in the live manifest, `isin_found` is **null** for all four
extractions. Only CIN was recovered. So the ISIN cross-check that would have
flagged this never ran.

### The fix — three parts

**1. Collapse ISINs to one company key.**

```
group NSE rows by CIN where known, else by normalised name
   |
   v
pick the primary line:
   prefer INE prefix over IN9
   prefer the line with the earlier listing date
   prefer the larger traded series
   |
   v
store the others as  alternate_isins: ["IN9175A01010"]
```

**2. Add a DVR / series flag.**

```
if symbol ends with  DVR / DVREQS / -RE / PP
   or ISIN starts with IN9 while an INE ISIN exists for the same CIN
      -> mark  series_type = "dvr"  and  primary = False
```

**3. Deduplicate at the report level too.**

Both lines resolve to the same PDF, so the SHA-256 hash store already keeps
one copy of the bytes. But the **manifest** will still have two rows. Add a
post-run audit: group by `sha256`, and if two rows share a hash but have
different `company_id`, keep the primary and flag the other.

### Test that would have caught it

```
assert one row per (CIN, fiscal_year) in the final manifest
```

Add this to `audit`.

---

## What else goes wrong

| Problem | Fix |
|---|---|
| Company renamed twice, early years invisible | Chain the symbol file, query every alias |
| Delisted in 2016 — not in today's master file | Keep old master snapshots; use "all scrips", not just active |
| Two companies with almost the same name | Never match on name alone; ISIN or CIN decides |
| SME board companies mixed in | Add a flag; decide later whether to include them |
| **DVR / multiple series** | **See the bug above. Collapse to one key.** |
| **BSE-only companies missing** | **Live run is NSE-only: 2,571 companies. BSE has ~5,900. You are missing ~3,000 small caps.** |

---

## The BSE gap — decide this now

Your current master is **NSE-only, 2,571 companies**.

| Choice | Companies | Effort | When to pick it |
|---|---|---|---|
| NSE only | ~2,571 | done already | A pilot, or if your research is large/mid cap only |
| NSE + BSE | ~5,900 | 1-2 days to wire the BSE master | **A full panel. Small caps are where the interesting variation is.** |

Wiring BSE means: download the BSE "List of Scrips" master, parse it, merge on
ISIN, and mark which exchange each company came from.

**Recommendation: do it.** A climate-risk or disclosure study that only covers
NSE-listed companies has a size bias baked in, and small caps are exactly where
disclosure quality varies most.

---

## Exit test for this step

> Count companies per year. If FY2012 has 3,000 and FY2013 has 900, the
> symbol-change chain is broken.

> Assert one row per (CIN, year) in the final manifest. If Jain Irrigation
> appears twice, the DVR bug is still there.
