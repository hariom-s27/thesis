# 01 — THE PROBLEM IN SIMPLE WORDS

---

## 1. What is an annual report?

Every listed Indian company must publish one book every year. It has:

- A cover page
- A contents page
- The Board's Report (what the directors say)
- **The MD&A** ← this is what we want
- The Corporate Governance Report
- The Auditor's Report
- The financial statements (all the numbers)
- The AGM notice

It is a PDF. It is 100 to 450 pages long.

*(Real numbers from our live run: KRBL FY2024 was 155 pages. Jain Irrigation
FY2024 was 445 pages. Same year, same country, 3× the size.)*

---

## 2. What is MD&A?

MD&A = **Management Discussion and Analysis**.

It is the part where management explains, in normal words:

- How the industry is doing
- What opportunities and threats they see
- How each business segment performed
- What they expect next year (outlook)
- What risks worry them
- How their internal controls work
- How the money performed
- What happened with employees

SEBI forces every listed company to write it. The rule is **LODR Regulation
34(2)(e)** read with **Schedule V Part B**.

### Why this rule is our best friend

Schedule V Part B lists the exact sub-headings companies must use:

```
Industry Structure and Developments
Opportunities and Threats
Segment-wise or Product-wise Performance
Outlook
Risks and Concerns
Internal Control Systems and their Adequacy
Discussion on Financial Performance with respect to Operational Performance
Material Developments in Human Resources / Industrial Relations Front
Details of Significant Changes in Key Financial Ratios    (FY2020 onwards)
Cautionary Statement
```

Companies copy these almost word for word. They survive bad OCR. They identify
the section even when the title page is unreadable.

**This list is the single most valuable asset in the whole problem.**

---

## 3. What we want at the end

For every company and every year, one clean text file plus the proof:

```
dataset/companies/KRBL_LIMITED__INE001B01026/
  2024/
    annual_report.pdf     the original file
    mda.txt               the answer
    mda.json              the proof
    document.json         where it came from
  2025/
    ...
manifest.jsonl            one line per report
```

**The important word is proof.**

A folder of `.txt` files is not a dataset. A folder of `.txt` files where each
one can say *"I am pages 27 to 33 of this exact PDF, this company's CIN matched
exactly, this year is confirmed by 59 weighted mentions"* — that is a dataset.

---

## 4. Why this is hard — six reasons

### Reason 1 — Some PDFs are pictures, not text

A digital PDF has text inside it. You can copy it.
A scanned PDF is just a photo of paper. There is no text.
You must use OCR (software that reads pictures of letters).

Old reports (2010–2014) and small companies are often scanned.

### Reason 2 — Some PDFs lie about having text

A PDF can have a text layer that looks fine but copies out as garbage
(`Ã¾Ã¿â–¡â–¡`). This happens when the font is embedded badly.

Most tools accept this garbage. **This silently ruins a dataset.**

### Reason 3 — The section has no fixed name

In the US, the same section is always "Item 7". A regex finds it.
In India there is no numbering. The same section is called 40 different things:

```
Management Discussion and Analysis
Management's Discussion & Analysis Report
MANAGEMENT DISCUSSION AND ANALYSIS (MD&A)
Management Discussion & Analysis Report (Annexure C to the Board's Report)
Directors' Report and Management Discussion & Analysis   <- merged in
MD&A                                                     <- short form only
```

*(Our live run hit two of these already: `MANAGEMENT DISCUSSION AND ANALYSIS`
for Jain Irrigation, `Management Discussion & Analysis` — with an ampersand —
for KRBL FY2025.)*

### Reason 4 — Layouts change every year

One year single column. Next year two columns. New designer, new fonts, new
section order. Sixteen years × 5,000 companies = a lot of variety.

*(Live proof: KRBL put MD&A on pages 27–33 in FY2024 and pages 33–39 in
FY2025. Jain Irrigation moved it from page 209 to page 103 between the same
two years.)*

### Reason 5 — It is not even in the same PART of the book

There is no rule about where MD&A sits. Our four real reports:

| Report | Total pages | MD&A at | Position |
|---|---|---|---|
| KRBL FY2024 | 155 | 27–33 | 17% in |
| KRBL FY2025 | 324 | 33–39 | 10% in |
| Jain FY2025 | 351 | 103–124 | 29% in |
| Jain FY2024 | 445 | 209–226 | 47% in |

**From 10% to 47% of the way through.** Any rule like "look in the first
third" would have failed on Jain FY2024.

### Reason 6 — Volume

About 40,000 PDFs. About 9,000,000 pages. If you OCR all of them, you waste
enormous time and money — because the MD&A is only about **4% of the pages**.

---

## 5. Real evidence the 4% number is right

From our live run:

| Report | Pages in doc | Pages in MD&A | Share |
|---|---|---|---|
| Jain Irrigation FY2025 | 351 | 22 | 6.3% |
| Jain Irrigation FY2024 | 445 | 18 | 4.0% |
| KRBL FY2024 | 155 | 7 | 4.5% |
| KRBL FY2025 | 324 | 7 | 2.2% |

**Average: 4.3%.**

That matches the planning assumption exactly. The cost model holds.

---

## 6. And one number that proves the ordering works

Jain Irrigation FY2024 was a **mixed** document — 12.84% of its 445 pages
needed OCR (that is about 57 pages).

**But we OCR'd zero pages.**

Why: none of those 57 scanned pages were inside pages 209–226. The scanned
pages were somewhere else in the book — probably signed certificates and
pasted subsidiary accounts.

```
Locate-then-OCR:     0 OCR pages
OCR-then-locate:    57 OCR pages   (and 445 pages of processing)
```

That is the whole design, working on a real filing.
