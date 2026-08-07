# =============================================================================
# Lists every quarter confirmed to have NO transcript available (not a bug --
# verified by the collector: the provider genuinely has nothing for that
# firm-quarter). Exports to outputs/confirmed_empty_list.csv for inspection.
# =============================================================================
import os, json, re
import pandas as pd

OUTPUT_DIR = r"D:\sem_iitk\sem 8\thesis\outputs"

empty = set()
for p in ["confirmed_empty.json", os.path.join(OUTPUT_DIR, "confirmed_empty.json")]:
    if os.path.exists(p):
        empty |= set(json.load(open(p)))

rows = []
for e in empty:
    m = re.match(r"([A-Z]+)_(\d{4})Q(\d)", e)
    if m:
        rows.append(dict(ticker=m.group(1), year=int(m.group(2)), quarter=int(m.group(3))))

df = pd.DataFrame(rows).sort_values(["ticker", "year", "quarter"])
df.to_csv(os.path.join(OUTPUT_DIR, "confirmed_empty_list.csv"), index=False)
print(f"total confirmed-empty quarters: {len(df)}")
print(df.groupby("ticker").size().sort_values(ascending=False))
print("\nsaved -> outputs/confirmed_empty_list.csv")
