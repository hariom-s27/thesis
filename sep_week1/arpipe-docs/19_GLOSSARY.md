# 19 — WORD LIST

Every term in one line.

---

## The domain

| Word | Simple meaning |
|---|---|
| **MD&A** | Management Discussion and Analysis — the section where management explains the business in words |
| **SEBI** | The Indian markets regulator |
| **LODR** | Listing Obligations and Disclosure Requirements — SEBI's rulebook for listed companies |
| **Regulation 34(2)(e)** | The rule that makes MD&A compulsory |
| **Schedule V Part B** | The exact list of what MD&A must contain |
| **Annual report** | The yearly book a listed company must publish |
| **Board's Report** | The directors' section — MD&A is sometimes folded inside it |
| **AGM notice** | Annual General Meeting notice, usually at the back |
| **BRR** | Business Responsibility Report — ESG disclosure, top 100 companies, FY2013+ |
| **BRSR** | Business Responsibility and Sustainability Report — replaced BRR, top 1,000, FY2023+ |
| **Ind AS** | Indian accounting standards, mandatory in phases from FY2016-17 |
| **PSU** | Public sector undertaking — government-owned company, must publish bilingually |
| **AMFI** | Association of Mutual Funds in India — publishes the large/mid/small cap bands |

## Identifiers

| Word | Simple meaning |
|---|---|
| **ISIN** | 12-character code identifying a security. Survives name changes. `INE175A01038` |
| **INE prefix** | Normal company equity line |
| **IN9 prefix** | Also a company line — used for extra series such as DVR |
| **INF prefix** | Mutual fund |
| **CIN** | 21-character company ID from the Ministry of Corporate Affairs. `L29120MH1986PLC042028` |
| **DVR** | Differential Voting Rights — a second share class, listed separately, **same annual report** |
| **Scrip code** | BSE's own numeric company ID |
| **Symbol** | NSE's short ticker. Changes when a company renames. |

## PDF and pages

| Word | Simple meaning |
|---|---|
| **Born-digital** | A PDF made by software; it has real text inside |
| **Scanned** | A PDF that is just photos of paper |
| **Hybrid page** | A page with some real text and some picture |
| **Broken text** | Text that exists in the PDF but copies out as garbage |
| **Mojibake** | The garbage characters you get from a broken font encoding |
| **Vector text** | Letters drawn as shapes instead of stored as letters |
| **Text layer** | The invisible text inside a PDF that you can copy |
| **xref table** | The PDF's internal index. If broken, the file will not open. |
| **Outline / bookmarks** | The PDF's own clickable table of contents |
| **Folio** | The page number printed on the paper — **not** the same as the PDF page index |
| **DPI** | Dots per inch — how detailed a rendered image is |
| **Gutter** | The empty vertical strip between two columns |

## The pipeline

| Word | Simple meaning |
|---|---|
| **Triage** | Sorting pages by how they must be handled |
| **Span** | The page range of a section, e.g. pages 209-226 |
| **Arbiter** | The judge that picks between the five location methods |
| **Supporters** | How many other methods agreed with the winner — our confidence measure |
| **Terminator** | A heading that marks the end of the section |
| **Re-trim** | Working out the boundaries again after OCR has made the text good |
| **Forward walk** | Reading one page at a time past the span until a terminator appears |
| **Escalation ladder** | Cheap OCR first, expensive OCR only when the cheap one fails |
| **Quality gate** | The check between two rungs of the ladder |
| **Manifest** | The log file listing everything processed |
| **Provenance** | The record of where a piece of data came from |
| **Resumable** | You can stop and restart without losing work or redoing it |
| **Idempotent** | Running it twice gives the same result as running it once |

## OCR and models

| Word | Simple meaning |
|---|---|
| **OCR** | Software that reads letters out of a picture |
| **VLM** | Vision Language Model — an AI that looks at an image and writes text |
| **Tesseract** | The classic free CPU OCR engine |
| **PaddleOCR-VL** | A small (0.9B) open document VLM. 100+ languages including Hindi. |
| **MinerU** | Another open document VLM, strong on dense multi-column |
| **olmOCR** | AllenAI's document VLM. Introduced document anchoring. |
| **ocrmypdf** | A tool that deskews, rotates, cleans and **writes a text layer back into the PDF** |
| **qpdf** | A tool that repairs damaged PDFs |
| **Textract** | AWS's OCR service. **No Hindi.** ~8x the cost of self-hosting. |
| **Document anchoring** | Giving the AI the PDF's own partial text as a hint |
| **Degeneracy** | When an AI model gets stuck repeating itself |
| **Silent substitution** | When a model replaces an unusual number with a plausible common one |
| **vLLM / SGLang** | Servers that host a model behind an OpenAI-compatible API |

## Layout

| Word | Simple meaning |
|---|---|
| **XY-cut** | A method to read multi-column pages in the right order: find the widest empty gap, split, repeat |
| **XY-Cut++** | A 2025 improvement on XY-cut. 98.8 BLEU on reading order. |
| **LayoutReader** | A trained model that predicts reading order |
| **Reading order** | Which block of text comes after which |
| **Running furniture** | Headers and footers that repeat on every page |
| **De-hyphenation** | Joining `manage-` and `ment` back into `management` |

## Storage

| Word | Simple meaning |
|---|---|
| **SHA-256** | A fingerprint of a file; identical files get the same fingerprint |
| **Content-addressed store** | Storing files by their fingerprint so duplicates vanish |
| **Blob** | The raw stored bytes of a file |
| **Hardlink** | A second name for the same file that costs no extra disk |
| **JSONL** | One JSON object per line. Append-only, crash-safe. |
| **Parquet** | A compressed columnar file format, good for analysis |
| **MinHash / LSH** | A fast way to find near-duplicate documents |

## Numbers and validation

| Word | Simple meaning |
|---|---|
| **XBRL** | Machine-readable financial filing format. Free from FY2018. |
| **Lakh** | 100,000 |
| **Crore** | 10,000,000 |
| **The unit trap** | The same table can be in lakh, crore, million or '000. Get it wrong and every number is off by 10-100x. |
| **TEDS** | A score for how correctly a table's structure was recovered |
| **Camelot** | A Python library for extracting tables from digital PDFs |
| **TATR** | Table Transformer — a learned table-structure model. Won on financial tables. |

## Evaluation

| Word | Simple meaning |
|---|---|
| **Labelled set** | Documents where a human wrote down the true answer |
| **Stratified sample** | A sample deliberately spread across categories, not random |
| **Exact-start accuracy** | Did we get the first page exactly right? |
| **±1 page accuracy** | Did we get within one page? The number that decides usability. |
| **Boundary IoU** | How much our page span overlaps the true span |
| **Pk / WindowDiff** | Standard scores for how well a section boundary was placed |
| **chrF++** | A text-similarity score used in the Hindi OCR benchmark |
| **ROUGE-1** | A text-similarity score. **Warning: high ROUGE does not mean correct numbers.** |
| **Fact-level accuracy** | Whether the actual numbers, units and entities survived. The metric that matters. |
| **OmniDocBench** | The main document-parsing benchmark (CVPR 2025) |
| **olmOCR-bench** | A harder OCR benchmark |
| **FinCriticalED** | A benchmark that scores financial *facts*, not text similarity |
| **MDPBench** | A multilingual document-parsing benchmark, 17 languages |
