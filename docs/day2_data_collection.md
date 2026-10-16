# Day 2 – Data Collection: Choose, Acquire and Inspect the Source Data (Complete Guide)

**Project:** Retail Demand Forecasting & Inventory Optimization Platform
**Phase:** Week 1 – Data Engineering & Foundation (Day 2 of the combined "Day 2–3 Data Collection" block)
**Goal of the day:** Decide the data strategy, acquire the primary sales data into `data/raw/`, inspect it thoroughly, build a reusable raw-data loader, and document the source. Day 3 then builds the remaining tables (product/store masters, prices and promotions, holidays, weather, inventory) and finalises the data dictionary.
**Estimated time:** 5–7 hours

> **How Day 2 and Day 3 divide the work**
> - **Day 2 (today):** data strategy decision → download primary dataset → inspect and profile → loader module → subsetting → raw data documentation.
> - **Day 3 (tomorrow):** supporting tables → India-specific adaptation → holiday and weather data → inventory simulation → merge into the target schema → final data dictionary.

---

## Day 2 Task Overview

| # | Task | Time | Output |
|---|---|---|---|
| 1 | Review the target schema and data requirements | 20 min | Requirements checklist |
| 2 | Evaluate data source options | 60 min | Decision matrix + chosen strategy |
| 3 | Set up data acquisition tooling | 20 min | Kaggle CLI / API configured |
| 4 | Download the primary dataset into `data/raw/` | 40 min | Raw files + checksums |
| 5 | First inspection and profiling | 60 min | Profile report |
| 6 | Build the raw data loader (`src/data/loader.py`) | 60 min | Reusable loader functions |
| 7 | Reshape and subset the data | 45 min | Subset in long format (interim) |
| 8 | Map the source schema to the project schema | 30 min | Mapping table |
| 9 | Document the data source and assumptions | 30 min | `docs/data_sources.md` |
| 10 | Tests, commit and push | 20 min | Tests passing, committed |

---

## Task 1 – Review the Target Schema and Data Requirements

Recall the target schema decided on Day 1 (one row per Date × Store × Product):

```text
Date, Store_ID, Product_ID, Category, Price, Promotion, Holiday,
Temperature, Inventory, Units_Sold, Revenue
```

### 1.1 What the project actually needs from the data

| Requirement | Why it matters | Minimum acceptable |
|---|---|---|
| Daily sales per store-product | Forecast target | Daily granularity, no weekly aggregates only |
| 2+ years of history | Yearly seasonality, a proper test window, lag features | ≥ 730 days (3+ years is better) |
| Multiple stores | Store-level demand and store performance dashboard | ≥ 5 stores |
| Multiple categories and products | Category/product demand analysis, global models | ≥ 3 categories, ≥ 50 products |
| Price history | Price vs demand, revenue forecasting | Price per product (and over time) |
| Promotion information | Promotion impact, a key business feature | A flag or on-promotion count |
| Holiday/event information | Holiday impact and seasonality | Calendar of events |
| Weather/external | External factors | Optional, can be added from an API |
| Inventory | Week 3 inventory optimization | Can be simulated if absent |

### 1.2 Reality check
No single public benchmark has **every** column. Plan from the start to **combine a benchmark sales dataset with derived/simulated and external columns**. The honest documentation of this is part of what makes the project credible.

**Deliverable of this task:** a short requirement checklist (copy the table above into `docs/data_sources.md`).

---

## Task 2 – Evaluate Data Source Options

### 2.1 Option comparison

#### Option A: M5 Forecasting (Walmart) – benchmark
- **What it is:** Daily unit sales of Walmart products across 10 stores in 3 US states (CA, TX, WI), from the Kaggle "M5 Forecasting – Accuracy" competition.
- **Scale:** About 3,049 products, 3 categories (FOODS, HOBBIES, HOUSEHOLD), 7 departments, 10 stores, roughly 1,900+ days (2011–2016).
- **Files:**
  - `calendar.csv`: date, weekday, month, year, `d` (day index), event names/types, SNAP flags
  - `sales_train_validation.csv` / `sales_train_evaluation.csv`: **wide format**, one row per item-store, columns `d_1 ... d_N` with units sold
  - `sell_prices.csv`: weekly price per store-item (`store_id, item_id, wm_yr_wk, sell_price`)
  - `sample_submission.csv`: not needed
- **Strengths:** Realistic retail data, real intermittency, real price changes, event calendar, widely recognised (reviewers know it).
- **Gaps:** No explicit promotion flag, no inventory, no weather, US stores/US events, dollars not rupees. Wide format needs reshaping. Large file.
- **Licence:** Kaggle competition data, accessed under the competition rules (you must accept them on Kaggle). Verify current terms before publishing derivatives and credit the source in the README.

#### Option B: Favorita (Store Sales – Time Series Forecasting) – benchmark with promotions
- **What it is:** Daily sales for families of products across 54 Corporación Favorita stores in Ecuador (Kaggle "Store Sales – Time Series Forecasting").
- **Files:** `train.csv` (date, store, product **family**, sales, **onpromotion**), `stores.csv`, `oil.csv`, `holidays_events.csv`, `transactions.csv`.
- **Strengths:** Has a **promotion count**, store metadata, holiday data, an external economic indicator (oil price), and a manageable size and long history (2013–2017).
- **Gaps:** Sales are at **product family** level (about 33 families), not individual SKU; no price; no inventory; no weather.
- **Licence:** Kaggle competition rules apply.

#### Option C: Fully synthetic data
- **What it is:** Data you generate yourself with a documented simulator.
- **Strengths:** Complete control; every column in your schema exists; India-specific stores, ₹ prices and festivals; no licence concerns; fast and small.
- **Gaps:** Can look fake and make models look unrealistically good; clients may be sceptical without a strong justification.
- **Acceptable when:** the generator's assumptions are clearly documented (your plan explicitly allows this).

#### Option D (Recommended): Hybrid
- Use a **benchmark** (M5 most likely) for realistic demand patterns, intermittency and price dynamics.
- **Adapt and extend** it to your schema: rename stores to Indian cities, convert prices to ₹, replace US events with Indian holidays/festivals, derive the promotion flag from price drops, add weather from Open-Meteo, and simulate inventory from sales and a replenishment policy.
- **Document every transformation transparently.**

### 2.2 Decision matrix

Score each 1 (poor) to 5 (excellent):

| Criterion | A: M5 | B: Favorita | C: Synthetic | D: Hybrid (M5-based) |
|---|:---:|:---:|:---:|:---:|
| Realism of demand patterns | 5 | 5 | 2–3 | 4–5 |
| Covers all schema columns | 2 | 3 | 5 | 4 |
| Product-level (SKU) granularity | 5 | 2 | 5 | 5 |
| Promotion information | 2 | 4 | 5 | 3–4 |
| India relevance | 1 | 1 | 5 | 4 |
| Portfolio credibility | 5 | 5 | 3 | 4–5 |
| Effort to prepare | 3 | 3 | 3 | 2 |
| Licence risk | 3 | 3 | 5 | 3 |
| Size manageability | 2 | 4 | 5 | 3 |

**Recommended choice:** **Option D (Hybrid based on M5)**, with a fall back to Option C if the download or licence is a problem, or Option B if you want real promotion data and are happy with family-level products.

### 2.3 Record the decision
Write the decision in `docs/data_sources.md`:

```markdown
## Data Strategy Decision
- Chosen: Hybrid (M5 Forecasting as base demand/price data)
- Reason: realistic demand, product-level granularity, credible benchmark
- Adaptations (Day 3): Indian store mapping, INR conversion, Indian holiday calendar,
  derived promotion flag, weather via Open-Meteo, simulated inventory
- Fallback: fully synthetic generator (documented assumptions)
```

### Challenges for this task
- **Decision paralysis:** time-box the decision to one hour.
- **Licence ambiguity:** note the licence/competition rules on the source page, credit the source in the README, and if you plan to redistribute data publicly, **do not commit raw data to GitHub**; commit only code and a small sample or the generator.
- **Over-adapting:** the more you modify, the more you must document. Keep adaptations principled and listed.

---

## Task 3 – Set Up Data Acquisition Tooling

### 3.1 Kaggle API credentials (for M5 or Favorita)

1. Create/log in to a Kaggle account.
2. **Accept the competition rules** on the competition page (required before download works):
   - M5: competition slug `m5-forecasting-accuracy`
   - Favorita: competition slug `store-sales-time-series-forecasting`
3. Account settings → **Create New API Token** (downloads `kaggle.json`; newer accounts may use an API token/env variable instead, so follow the current Kaggle instructions on the settings page).
4. Place credentials securely:

```bash
# macOS / Linux / WSL
mkdir -p ~/.kaggle
mv ~/Downloads/kaggle.json ~/.kaggle/kaggle.json
chmod 600 ~/.kaggle/kaggle.json
```

```powershell
# Windows
mkdir $env:USERPROFILE\.kaggle
move $env:USERPROFILE\Downloads\kaggle.json $env:USERPROFILE\.kaggle\kaggle.json
```

5. Install the CLI inside the venv:

```bash
pip install kaggle
kaggle --version
```

**Security rule:** never place `kaggle.json` or any token inside the repo. It is stored in your home directory only.

### 3.2 Manual fallback
If the CLI fails, download the files from the competition **Data** tab in the browser and place them into `data/raw/m5/`.

### Challenges
- **403 Forbidden on download:** you haven't accepted the competition rules. Accept them in the browser.
- **Credential permissions warning:** run `chmod 600`.
- **Corporate/ISP network blocks:** use manual download.

---

## Task 4 – Download the Primary Dataset into `data/raw/`

### 4.1 Raw data layout

```text
data/raw/
└── m5/
    ├── calendar.csv
    ├── sales_train_evaluation.csv
    ├── sales_train_validation.csv
    ├── sell_prices.csv
    └── MANIFEST.md          (generated: file list, sizes, checksums, download date)
```

### 4.2 Download script: `src/data/download.py`

```python
"""Download raw datasets into data/raw. Safe to re-run."""
import subprocess
import zipfile
from pathlib import Path

from src.config import RAW_DIR

COMPETITION = "m5-forecasting-accuracy"
TARGET_DIR = RAW_DIR / "m5"

def download_m5():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = TARGET_DIR / f"{COMPETITION}.zip"

    if not (TARGET_DIR / "sales_train_evaluation.csv").exists():
        subprocess.run(
            ["kaggle", "competitions", "download", "-c", COMPETITION, "-p", str(TARGET_DIR)],
            check=True,
        )
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(TARGET_DIR)
        zip_path.unlink()          # keep disk usage low
    else:
        print("M5 already downloaded, skipping.")

if __name__ == "__main__":
    download_m5()
```

Run from the repo root:

```bash
python -m src.data.download
```

### 4.3 Create a manifest with checksums: `src/data/manifest.py`

```python
import hashlib
from datetime import date
from pathlib import Path

def sha256(path: Path, chunk=1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()

def write_manifest(folder: Path, source: str):
    lines = [f"# Manifest: {folder.name}", f"- Source: {source}",
             f"- Downloaded: {date.today().isoformat()}", "",
             "| File | Size (MB) | SHA-256 |", "|---|---:|---|"]
    for p in sorted(folder.glob("*.csv")):
        lines.append(f"| {p.name} | {p.stat().st_size/1e6:.1f} | {sha256(p)} |")
    (folder / "MANIFEST.md").write_text("\n".join(lines))
```

The manifest proves the exact data version used and helps detect accidental edits to raw files.

### 4.4 Make raw files read-only (protects "never edit raw")

```bash
chmod -R a-w data/raw/m5/*.csv        # macOS / Linux
```

### Confirm Git is ignoring the data
```bash
git status        # data/raw/m5/* must NOT appear
```

### Challenges
- **Large size** (the evaluation sales file is hundreds of MB when expanded; the dataset total is several hundred MB). Ensure enough disk space (≥ 2 GB free).
- **Slow/interrupted download:** the script is re-runnable; delete partial files and retry.
- **Accidentally committing data:** verify `.gitignore` before `git add .`.
- **Two sales files:** `sales_train_validation.csv` (fewer days) and `sales_train_evaluation.csv` (more days, includes the validation period). **Use the evaluation file** for the most history. Record this choice in the docs.

---

## Task 5 – First Inspection and Profiling

Do this in a scratch notebook (`notebooks/00_raw_inspection.ipynb`, optional) or a script. The aim is to understand the data **before** transforming it.

### 5.1 Load efficiently (wide sales table is large)

```python
import pandas as pd
from src.config import RAW_DIR

m5 = RAW_DIR / "m5"

calendar = pd.read_csv(m5 / "calendar.csv", parse_dates=["date"])
prices   = pd.read_csv(m5 / "sell_prices.csv")
sales    = pd.read_csv(m5 / "sales_train_evaluation.csv")

for name, df in [("calendar", calendar), ("prices", prices), ("sales", sales)]:
    print(name, df.shape, f"{df.memory_usage(deep=True).sum()/1e6:.0f} MB")
```

Tip: the wide sales table has ~1,900+ day columns. Use `usecols`, downcast integers (`int16`) and categoricals for ID columns to reduce memory.

### 5.2 Inspection checklist

**Structure**
- [ ] Shape, columns, dtypes of each file
- [ ] ID columns: `id`, `item_id`, `dept_id`, `cat_id`, `store_id`, `state_id`
- [ ] Number of unique items, stores, departments, categories, states
- [ ] Date range from `calendar` (first and last date, number of days)
- [ ] Day index `d_1 … d_N` mapping to dates via `calendar.d`

**Quality**
- [ ] Missing values per file
- [ ] Duplicate rows or duplicate keys
- [ ] Negative sales (should be none)
- [ ] Price missing for weeks when an item is not sold (expected: items launch at different times)
- [ ] Items with long runs of zeros (not yet launched vs genuinely no demand)

**Distribution**
- [ ] Summary statistics of daily units
- [ ] Share of zero-sales cells (expect a high share; demand is intermittent)
- [ ] Top 10 items by total units
- [ ] Sales by category and by store (totals)
- [ ] Price range by category; number of price changes per item

**Calendar/events**
- [ ] List of unique `event_name_1` and `event_type_1`
- [ ] Which events are US-specific (need replacing on Day 3)
- [ ] SNAP flags (US food-assistance flag; explain it or drop it)

### 5.3 Profile summary to write down

Create a small table in `docs/data_sources.md`:

```markdown
| Metric | Value |
|---|---|
| Date range | (fill in) |
| Number of days | (fill in) |
| Stores | (fill in) |
| Items | (fill in) |
| Categories / Departments | (fill in) |
| Rows after reshaping (full) | (fill in) |
| % zero-sales cells | (fill in) |
| Missing price % | (fill in) |
```

### 5.4 Key insights to look for
- **Intermittent demand:** many items have mostly zero sales, so MAPE will not work for them. This confirms the WMAPE decision from Day 1.
- **Late-launch items:** items with all zeros until a certain date (no price rows before that). These are not true zero demand; treat the pre-launch period as "not on sale".
- **Store differences:** some stores sell much more; global models need store as a feature.
- **Weekly price table:** price is weekly (`wm_yr_wk`), so mapping to daily requires the calendar.

### Challenges
- **Memory errors** reading the wide file. Use `dtype` downcasting, read in chunks, or filter to a subset of rows early.
- **Misreading zeros.** Distinguish "not launched" (no price) from "launched, zero sales".
- **Confusing `d` indices.** `d_1` is the first calendar date; always map through `calendar`.

---

## Task 6 – Build the Raw Data Loader (`src/data/loader.py`)

Create a reusable loader so notebooks and pipelines never re-implement reading logic.

### 6.1 Functions to implement

| Function | Purpose |
|---|---|
| `load_calendar()` | Returns the calendar with parsed dates and useful dtypes |
| `load_prices()` | Returns weekly price table with typed columns |
| `load_sales_wide(stores=None, items=None, cats=None)` | Returns the wide sales table, optionally filtered early to save memory |
| `wide_to_long(sales_wide, calendar)` | Melts `d_*` columns into `Date`, `Units_Sold` rows |
| `attach_prices(sales_long, calendar, prices)` | Joins weekly price to each daily row by `store_id, item_id, wm_yr_wk` |
| `load_m5_long(...)` | Convenience wrapper that returns the merged long-format table |

### 6.2 Reference implementation

```python
# src/data/loader.py
from pathlib import Path
import pandas as pd
from src.config import RAW_DIR

M5_DIR = RAW_DIR / "m5"
ID_COLS = ["id", "item_id", "dept_id", "cat_id", "store_id", "state_id"]

def load_calendar() -> pd.DataFrame:
    cal = pd.read_csv(M5_DIR / "calendar.csv", parse_dates=["date"])
    for c in ["weekday", "event_name_1", "event_type_1", "event_name_2", "event_type_2"]:
        cal[c] = cal[c].astype("category")
    return cal

def load_prices() -> pd.DataFrame:
    p = pd.read_csv(M5_DIR / "sell_prices.csv")
    p["store_id"] = p["store_id"].astype("category")
    p["item_id"] = p["item_id"].astype("category")
    p["sell_price"] = p["sell_price"].astype("float32")
    return p

def load_sales_wide(stores=None, items=None, cats=None) -> pd.DataFrame:
    df = pd.read_csv(M5_DIR / "sales_train_evaluation.csv")
    if stores is not None:
        df = df[df["store_id"].isin(stores)]
    if items is not None:
        df = df[df["item_id"].isin(items)]
    if cats is not None:
        df = df[df["cat_id"].isin(cats)]
    day_cols = [c for c in df.columns if c.startswith("d_")]
    df[day_cols] = df[day_cols].astype("int16")
    return df.reset_index(drop=True)

def wide_to_long(sales_wide: pd.DataFrame, calendar: pd.DataFrame) -> pd.DataFrame:
    day_cols = [c for c in sales_wide.columns if c.startswith("d_")]
    long = sales_wide.melt(id_vars=ID_COLS, value_vars=day_cols,
                           var_name="d", value_name="Units_Sold")
    long = long.merge(calendar[["d", "date", "wm_yr_wk"]], on="d", how="left")
    long["Units_Sold"] = long["Units_Sold"].astype("int16")
    return long.drop(columns="d").rename(columns={"date": "Date"})

def attach_prices(sales_long, prices):
    out = sales_long.merge(prices, on=["store_id", "item_id", "wm_yr_wk"], how="left")
    return out.rename(columns={"sell_price": "Price"})
```

### 6.3 Design rules
- No hard-coded absolute paths; use `src/config.py`.
- Functions are pure where possible (input in, output out); no hidden global state.
- Log shapes and row counts at each step (use `get_logger` from `src/utils.py`).
- Filter **before** melting; melting the full table creates tens of millions of rows.

### Challenges
- **Melt explosion:** 30,000+ series × 1,900+ days is tens of millions of rows. Always subset first.
- **Join key mismatch:** price joins on `store_id + item_id + wm_yr_wk`; verify row counts before and after (a many-to-many join will silently duplicate rows).
- **Categorical dtype merges:** mismatched categories can cause merge failures or silent NaNs. Cast keys to the same dtype before merging.

---

## Task 7 – Reshape and Subset the Data

### 7.1 Why subset
The full M5 data is far larger than needed for a portfolio MVP. A sensible subset keeps the project fast, keeps the dashboard responsive, and still covers every category and store type.

### 7.2 Recommended subset design

| Dimension | Choice | Reason |
|---|---|---|
| Stores | 5–10 (all 10 is fine if memory allows) | Store comparison and store-level dashboard |
| Categories | All 3 (FOODS, HOBBIES, HOUSEHOLD) | Category demand analysis |
| Items | About 100–200 total, stratified across categories and across demand levels | Fast training, still diverse |
| Dates | At least the last 3 years of the history (or all if size allows) | Seasonality and test window |

### 7.3 Sampling method (stratified, reproducible)

1. Compute total units per item.
2. Within each category, bucket items into **high / medium / low** demand terciles (also keep some intermittent items on purpose).
3. Sample a fixed number from each bucket with `random_state=42`.
4. Save the selected item list to `data/interim/selected_items.csv` so the sample is reproducible.

```python
import pandas as pd
from src.config import SEED

def stratified_item_sample(sales_wide, n_per_cat_bucket=15):
    day_cols = [c for c in sales_wide.columns if c.startswith("d_")]
    item_tot = (sales_wide.assign(total=sales_wide[day_cols].sum(axis=1))
                .groupby(["cat_id", "item_id"])["total"].sum().reset_index())
    item_tot["bucket"] = (item_tot.groupby("cat_id")["total"]
                          .transform(lambda s: pd.qcut(s.rank(method="first"), 3,
                                                       labels=["low", "med", "high"])))
    picked = (item_tot.groupby(["cat_id", "bucket"], group_keys=False)
              .apply(lambda g: g.sample(min(len(g), n_per_cat_bucket), random_state=SEED)))
    return picked
```

### 7.4 Produce the interim long-format dataset

```python
cal = load_calendar()
prices = load_prices()
wide = load_sales_wide(items=selected_items)          # filter first
long = wide_to_long(wide, cal)
long = attach_prices(long, prices)
long.to_parquet(INTERIM_DIR / "m5_subset_long.parquet", index=False)
```

Save as **parquet** (smaller and faster than CSV, keeps dtypes).

### 7.5 Sanity checks after reshaping
- [ ] Row count = number of series × number of days
- [ ] Date range matches the calendar
- [ ] No duplicate keys on (Date, store_id, item_id)
- [ ] Price missing share is similar to the earlier profile (pre-launch periods)
- [ ] Total units in long format equals total units in the wide subset (sum check)

### Challenges
- **Biased sampling:** random sampling may pick mostly low-volume items. Stratify, as above.
- **Too many zero-series:** include a few intermittent items for realism, but avoid a subset dominated by dead items.
- **Reproducibility:** save the selected item list and the seed.
- **Memory:** if melt is still heavy, process store by store and concatenate.

---

## Task 8 – Map the Source Schema to the Project Schema

Create the mapping table now so Day 3 transformations are straightforward.

| Project column | M5 source | Status | Day 3 action |
|---|---|---|---|
| `Date` | `calendar.date` via `d` | Available | None |
| `Store_ID` | `store_id` (e.g. CA_1) | Available | Rename to Indian store IDs/cities |
| `Product_ID` | `item_id` | Available | Standardise format (`PROD_0001`) |
| `Category` | `cat_id` | Available | Map to retail-friendly names |
| `Price` | `sell_price` (weekly, USD) | Available, weekly | Expand to daily, convert to INR |
| `Promotion` | not provided | **Derive** | Flag weeks where price drops materially below the item's typical price |
| `Holiday` | `calendar.event_name_*` (US events) | Partial (US) | Replace with Indian holidays/festivals |
| `Temperature` | not provided | **External** | Fetch from Open-Meteo per store city |
| `Inventory` | not provided | **Simulate** | Replenishment-policy simulation from sales |
| `Units_Sold` | wide `d_*` values | Available | None |
| `Revenue` | not provided | **Derive** | `Units_Sold × Price` |

### Store mapping idea (to finalise on Day 3)

| M5 store | Example Indian city/store |
|---|---|
| CA_1 … CA_4 | Bangalore-01, Bangalore-02, Mumbai-01, Delhi-01 |
| TX_1 … TX_3 | Hyderabad-01, Chennai-01, Pune-01 |
| WI_1 … WI_3 | Kolkata-01, Ahmedabad-01, Jaipur-01 |

Keep the mapping in a version-controlled CSV (`data/external/store_mapping.csv` or in `config`), so it is reproducible and transparent.

### Challenges
- **Weekly to daily price expansion:** price is constant within a retail week, which is fine, but note it as an assumption.
- **Derived promotion quality:** a derived flag is an approximation, not ground truth. State it in the limitations.
- **Currency conversion realism:** a flat conversion factor makes Indian prices unrealistic (₹ 80 for a sub-dollar item). Plan a documented scaling approach on Day 3 (for example a category-specific price scaling).
- **Store/city re-labelling honesty:** state clearly that the sales patterns come from the benchmark and were re-labelled for the portfolio scenario.

---

## Task 9 – Document the Data Source and Assumptions

Create `docs/data_sources.md`:

```markdown
# Data Sources

## 1. Primary source
- Dataset: M5 Forecasting – Accuracy (Walmart), Kaggle
- URL / slug: m5-forecasting-accuracy
- Access date: <date>
- Licence/terms: Kaggle competition rules (accepted); raw data not redistributed
- Files used: calendar.csv, sales_train_evaluation.csv, sell_prices.csv
- Original coverage: <stores>, <items>, <days>, <date range>

## 2. Subset used
- Selection method: stratified sample by category and demand tercile (seed 42)
- Selected stores: <list>
- Selected items: <count> (saved in data/interim/selected_items.csv)
- Date range: <start> to <end>

## 3. Planned adaptations (Day 3)
(see mapping table)

## 4. Assumptions
- Price is constant within each retail week
- Promotion flag derived from price drops (not ground truth)
- Inventory simulated using a replenishment policy
- Store names/cities re-labelled for the Indian retail scenario
- Zero sales before the first price record = item not yet launched

## 5. Known limitations
- US consumer behaviour, adapted to an Indian context
- No real promotion, weather or inventory columns in the source
- Intermittent demand for many items

## 6. Reproducibility
- Raw files + checksums in data/raw/m5/MANIFEST.md
- Download: python -m src.data.download
- Random seed: 42
```

Also add a **README section** "Data" that mentions the source and credits it, and that the raw data is not included in the repo.

---

## Task 10 – Tests, Commit and Push

### 10.1 Tests: `tests/test_loader.py`

```python
import pandas as pd
from src.data.loader import wide_to_long

def test_wide_to_long_shape_and_sum():
    wide = pd.DataFrame({
        "id": ["a", "b"], "item_id": ["i1", "i2"], "dept_id": ["d", "d"],
        "cat_id": ["c", "c"], "store_id": ["s1", "s1"], "state_id": ["x", "x"],
        "d_1": [1, 0], "d_2": [2, 3],
    })
    cal = pd.DataFrame({
        "d": ["d_1", "d_2"],
        "date": pd.to_datetime(["2020-01-01", "2020-01-02"]),
        "wm_yr_wk": [11949, 11949],
    })
    long = wide_to_long(wide, cal)
    assert len(long) == 4
    assert long["Units_Sold"].sum() == 6
    assert long["Date"].min() == pd.Timestamp("2020-01-01")
```

Add one test that confirms there are no duplicate (Date, store, item) keys after `attach_prices`.

### 10.2 Commit

```bash
git checkout dev
git checkout -b feature/data-collection
git status                       # raw/interim data must not be listed
git add src docs tests config.yaml
git commit -m "feat: add M5 download, loader, subsetting and data source docs"
git checkout dev && git merge feature/data-collection
git push origin dev
```

---

## Alternative Paths (if you don't use M5)

### Path B – Favorita
- Download `store-sales-time-series-forecasting`.
- Files: `train.csv`, `stores.csv`, `oil.csv`, `holidays_events.csv`, `transactions.csv`.
- Treat **product family** as the "product" level. Real `onpromotion` becomes your `Promotion` feature; the oil price serves as an economic indicator.
- Gap: no price, so simulate or assign a price per family on Day 3.

### Path C – Fully synthetic (generator design to settle today, build on Day 3)
Decide the following parameters today and write them in `docs/data_sources.md`:

| Parameter | Suggested value |
|---|---|
| History | 3 years of daily data |
| Stores | 8–10 across Indian cities |
| Products | 100–150 across 5–6 categories |
| Base demand per product | Log-normal distribution (a few fast sellers, many slow) |
| Trend | Mild linear/logistic growth, differing by category |
| Weekly seasonality | Weekend uplift, category dependent |
| Yearly seasonality | Festival season (Oct–Nov), summer, year-end |
| Holiday effect | Spikes before major festivals (Diwali, Eid, Christmas, Pongal) |
| Promotion | Random promo calendar with uplift 10–40% and a post-promo dip |
| Price elasticity | Negative, category dependent |
| Weather effect | Temperature-sensitive categories (beverages, ice cream) |
| Noise | Poisson/negative-binomial for count data (not Gaussian) |
| Intermittency | Zero-inflation for slow movers |
| Anomalies | A few stock-outs, data glitches and one-off spikes |

Use a **negative-binomial/Poisson** process for counts so the data stays integer and realistic.

---

## Day 2 Challenges Summary

| Challenge | Impact | Mitigation |
|---|---|---|
| Kaggle 403 / credentials | Blocks download | Accept competition rules; fix token permissions; manual download fallback |
| Large wide-format file | Memory errors | Filter first, downcast dtypes, read in chunks |
| Melt row explosion | Crashes/slow | Subset before reshaping; process by store |
| Many-to-many join duplicates rows | Silent data corruption | Check row counts before/after joins; assert unique keys |
| Zero sales vs not launched | Wrong demand signal | Use missing-price weeks to detect pre-launch periods |
| Missing promo/inventory/weather in source | Incomplete schema | Derive/simulate/fetch on Day 3, and document it |
| US data in an Indian scenario | Credibility | Transparent adaptation and honest documentation |
| Licence uncertainty | Legal/credibility risk | Credit source, keep raw data out of Git, check terms |
| Biased item sample | Misleading models | Stratified, seeded sample saved to disk |
| Decision paralysis | Lost time | Time-box the decision; hybrid M5 default |

---

## Day 2 Deliverables Checklist

**Decisions**
- [ ] Data strategy chosen and recorded (Hybrid/M5 recommended)
- [ ] Requirements checklist and decision matrix saved in `docs/data_sources.md`

**Acquisition**
- [ ] Kaggle (or alternative) access working
- [ ] Raw files in `data/raw/m5/` (read-only)
- [ ] `MANIFEST.md` with sizes and SHA-256 checksums
- [ ] Confirmed data folders are ignored by Git

**Inspection**
- [ ] Profile metrics filled in (date range, stores, items, zero share, missing price)
- [ ] Intermittency and late-launch items noted
- [ ] US-specific events listed for replacement on Day 3

**Code**
- [ ] `src/data/download.py` and `src/data/manifest.py`
- [ ] `src/data/loader.py` with load, melt and price-join functions
- [ ] Stratified item sampler with saved `selected_items.csv`
- [ ] Interim parquet `m5_subset_long.parquet` created and validated
- [ ] `tests/test_loader.py` passing

**Documentation**
- [ ] Schema mapping table (source → project columns)
- [ ] `docs/data_sources.md` complete (source, subset, assumptions, limitations)
- [ ] README "Data" section added

**Git**
- [ ] Work committed on `feature/data-collection`, merged into `dev`, pushed

**Final deliverable for Day 2:** raw dataset acquired and documented, a reusable loader, a reproducible interim subset, and a clear plan for Day 3's table-building and adaptation work.

---

## Preview of Day 3

Tomorrow you will:
1. Build the **product master** and **store master** (with Indian store/city mapping).
2. Expand weekly prices to daily, convert to ₹ with a documented scaling approach, and derive the **promotion flag and discount %**.
3. Build the **Indian holiday and festival calendar** (`holidays` library plus custom festival windows).
4. Fetch **weather** (Open-Meteo) per store city and cache it in `data/external/`.
5. **Simulate inventory** from sales using a reorder policy, including some stock-outs.
6. Merge everything into the target schema and finalise `docs/data_dictionary.md`.
