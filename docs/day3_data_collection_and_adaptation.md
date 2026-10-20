# Day 3 – Data Collection (Part 2): Build the Supporting Tables and Assemble the Raw Dataset (Complete Guide)

**Project:** Retail Demand Forecasting & Inventory Optimization Platform
**Phase:** Week 1 – Data Engineering & Foundation (Day 3, second half of the "Day 2–3 Data Collection" block)
**Goal of the day:** Turn the interim M5 subset from Day 2 into the full project dataset. Build the product and store masters, convert prices to ₹ and derive promotions, build the Indian holiday/festival calendar, fetch weather, simulate inventory, merge everything into the target schema, and finalise the data dictionary.
**Estimated time:** 7–9 hours (the heaviest day of Week 1)
**Deliverable:** Raw project dataset + complete data dictionary.

> **Starting point (from Day 2):** `data/interim/m5_subset_long.parquet` with columns `id, item_id, dept_id, cat_id, store_id, state_id, Units_Sold, Date, wm_yr_wk, Price` (weekly price already joined to each day, `NaN` before an item's launch), plus `data/interim/selected_items.csv` and `docs/data_sources.md`.
>
> **If you chose the fully synthetic path (Option C):** skip Tasks 2, 4 and 5 as written and follow the **"Path C – Synthetic generator"** section near the end of this file, which builds the same tables from a simulator. Tasks 6, 7, 9, 10, 11 and 12 still apply.

---

## Day 3 Task Overview

| # | Task | Time | Output |
|---|---|---|---|
| 1 | Review Day 2 outputs and prepare the Day 3 workspace | 25 min | Module skeletons + config additions |
| 2 | Build the category mapping and product master | 50 min | `product_master.parquet` |
| 3 | Build the store master and Indian store mapping | 40 min | `store_master.parquet`, `store_mapping.csv` |
| 4 | Convert prices to ₹ (daily price table) | 40 min | `Price` in INR |
| 5 | Derive promotion flag and discount % | 60 min | `Promotion`, `Discount_Pct`, `Regular_Price` |
| 6 | Build the Indian holiday and festival calendar | 60 min | `holidays_india.parquet` |
| 7 | Fetch and cache weather data | 45 min | `data/external/weather/*.csv` |
| 8 | (Recommended) Apply a documented festival demand uplift | 40 min | Adjusted `Units_Sold` + audit column |
| 9 | Simulate inventory | 75 min | `Inventory`, `Stockout_Flag` |
| 10 | Assemble the target schema | 45 min | `retail_demand_raw.parquet` |
| 11 | Validate the assembled dataset | 45 min | Validation report |
| 12 | Finalise the data dictionary and documentation | 45 min | `docs/data_dictionary.md` |
| 13 | (Optional) Controlled data-quality issues | 30 min | Issue log |
| 14 | Tests, commit and push | 25 min | Tests passing, merged |

**Recommended pipeline order** (each step depends on the previous ones):

```text
Interim long table (Day 2)
  → product master (+ price scale factors)
  → store master
  → INR prices
  → promotion / discount
  → holiday calendar
  → weather
  → festival demand adjustment (optional)
  → inventory simulation
  → assemble + revenue
  → validate → data dictionary
```

---

## Task 1 – Review Day 2 Outputs and Prepare the Workspace

### 1.1 Checks before starting
- [ ] `data/interim/m5_subset_long.parquet` loads and has the expected row count (series × days)
- [ ] `data/interim/selected_items.csv` exists
- [ ] Raw files in `data/raw/m5/` are untouched
- [ ] Virtual environment is active, `python scripts/verify_env.py` still passes
- [ ] You are on a feature branch: `git checkout -b feature/data-adaptation`

### 1.2 Create the modules for today

```text
src/data/
├── build_masters.py      # product master, store master
├── prices.py             # INR conversion, promotion derivation
├── calendar_india.py     # holiday and festival calendar
├── weather.py            # Open-Meteo fetch + cache + fallback
├── demand_adjust.py      # optional festival uplift
├── inventory.py          # inventory simulation
└── assemble.py           # merge everything into the target schema

data/external/
├── category_mapping.csv
├── store_mapping.csv
├── holidays_india.csv
└── weather/              # one CSV per city, cached
```

### 1.3 Add an adaptation block to `config.yaml`

```yaml
adaptation:
  seed: 42
  price_scale:            # constant multiplier per category (USD benchmark price -> INR price)
    FOODS: 30
    HOUSEHOLD: 35
    HOBBIES: 40
  price_jitter: 0.10      # +/-10% constant per-item variation
  promo:
    window_weeks: 13      # rolling reference-price window
    min_periods: 4
    min_discount: 0.05    # price must be >=5% below reference to count as promotion
  festival_uplift:
    enabled: true
    window_days: 7        # days before a festival that receive the uplift
    by_category:
      Grocery & Food: 0.25
      Home & Household: 0.20
      Toys & Hobbies: 0.15
  inventory:
    review_days: 7
    service_z: 1.65       # about 95% service level
    window: 28
    initial_cover_days: 14
  weather:
    enabled: true
    use_fallback_if_api_fails: true
```

### Challenges
- **Pipeline order mistakes:** price scale factors must exist before the promotion step; the inventory step needs final `Units_Sold`. Use the order shown above.
- **Running everything in one notebook:** build each step as a function in `src/data/` so the whole pipeline is re-runnable with one command (`python -m src.data.assemble`).
- **Config drift:** keep every tunable number in `config.yaml`, not inside functions.

---

## Task 2 – Build the Category Mapping and Product Master

### 2.1 Category and department mapping

M5 categories are US-style (FOODS, HOBBIES, HOUSEHOLD). Map them to retail-friendly names and save as `data/external/category_mapping.csv`.

| M5 `cat_id` | Project `Category` |
|---|---|
| FOODS | Grocery & Food |
| HOUSEHOLD | Home & Household |
| HOBBIES | Toys & Hobbies |

| M5 `dept_id` | Project `Department` |
|---|---|
| FOODS_1 | Snacks & Beverages |
| FOODS_2 | Staples & Packaged Food |
| FOODS_3 | Fresh & Dairy |
| HOUSEHOLD_1 | Cleaning & Utilities |
| HOUSEHOLD_2 | Home Decor & Kitchen |
| HOBBIES_1 | Toys & Games |
| HOBBIES_2 | Stationery & Crafts |

> Department labels are approximations chosen for the Indian retail scenario. Document that in `docs/data_sources.md`, because the source does not describe the departments.

### 2.2 Product master columns

| Column | Description | How it is built |
|---|---|---|
| `Product_ID` | Standardised ID (`PROD_0001`) | Sorted `item_id`, enumerated, then saved as a mapping |
| `Source_Item_ID` | Original M5 `item_id` | Kept for traceability |
| `Product_Name` | Readable label | Generated, e.g. `Snacks & Beverages Item 014` (not a real product name) |
| `Category` | Mapped category | Category mapping |
| `Department` | Mapped department | Department mapping |
| `Price_Factor` | USD→INR scale multiplier for this item | Category scale × (1 + jitter × U(−1, 1)) |
| `Base_Price` | Typical ₹ price | Median of the item's INR price history (filled in Task 4) |
| `Unit_Cost` | ₹ cost to the retailer | `Base_Price × margin`, margin drawn per category |
| `Lead_Time_Days` | Supplier lead time | Random integer 2–7 (seeded) |
| `Min_Order_Qty` | Order multiple | Chosen from {6, 12, 24} |
| `Shelf_Life_Days` | Optional, perishables only | Fresh & Dairy short, others blank |

### 2.3 Reference implementation

```python
# src/data/build_masters.py
import numpy as np
import pandas as pd
from src.config import CFG, EXTERNAL_DIR, INTERIM_DIR

CAT_MAP = {"FOODS": "Grocery & Food", "HOUSEHOLD": "Home & Household", "HOBBIES": "Toys & Hobbies"}
DEPT_MAP = {
    "FOODS_1": "Snacks & Beverages", "FOODS_2": "Staples & Packaged Food", "FOODS_3": "Fresh & Dairy",
    "HOUSEHOLD_1": "Cleaning & Utilities", "HOUSEHOLD_2": "Home Decor & Kitchen",
    "HOBBIES_1": "Toys & Games", "HOBBIES_2": "Stationery & Crafts",
}
MARGIN = {"Grocery & Food": (0.70, 0.88), "Home & Household": (0.60, 0.80), "Toys & Hobbies": (0.50, 0.75)}

def build_product_master(long_df: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(CFG["adaptation"]["seed"])
    items = (long_df[["item_id", "dept_id", "cat_id"]].drop_duplicates()
             .sort_values("item_id").reset_index(drop=True))
    items["Product_ID"] = [f"PROD_{i:04d}" for i in range(1, len(items) + 1)]
    items["Category"] = items["cat_id"].map(CAT_MAP)
    items["Department"] = items["dept_id"].map(DEPT_MAP)
    items["Product_Name"] = (items["Department"] + " Item "
                             + items.groupby("dept_id").cumcount().add(1).astype(str).str.zfill(3))

    scale = CFG["adaptation"]["price_scale"]
    jitter = CFG["adaptation"]["price_jitter"]
    u = rng.uniform(-1, 1, len(items))
    items["Price_Factor"] = items["cat_id"].map(scale) * (1 + jitter * u)

    items["Lead_Time_Days"] = rng.integers(2, 8, len(items))
    items["Min_Order_Qty"] = rng.choice([6, 12, 24], len(items))
    items["Shelf_Life_Days"] = np.where(items["dept_id"] == "FOODS_3", rng.integers(3, 15, len(items)), np.nan)
    items = items.rename(columns={"item_id": "Source_Item_ID"})
    # Base_Price and Unit_Cost are completed after INR prices exist (Task 4)
    return items.drop(columns=["dept_id", "cat_id"])
```

### 2.4 Rules
- The ID mapping must be **deterministic** (same input → same IDs). Save `product_master.parquet` and never regenerate it casually, otherwise IDs shift between runs.
- Keep `Source_Item_ID` so every project row can be traced back to the benchmark.

### Challenges
- **Fake product names look unprofessional.** Use consistent, plainly generic labels; never invent brand names. State in the documentation that product names are generic labels.
- **Category relabelling credibility:** the mapping is an assumption. Document it.
- **Perishables:** shelf life is optional; if you add it, use it later only for overstock logic, not for model features.

---

## Task 3 – Build the Store Master and Indian Store Mapping

### 3.1 Store mapping (M5 store → Indian store)

Save as `data/external/store_mapping.csv`.

| M5 `store_id` | `Store_ID` | `Store_Name` | City | State | Region | Latitude | Longitude |
|---|---|---|---|---|---|---:|---:|
| CA_1 | STORE_001 | Bangalore-01 | Bangalore | Karnataka | South | 12.9716 | 77.5946 |
| CA_2 | STORE_002 | Bangalore-02 | Bangalore | Karnataka | South | 12.9716 | 77.5946 |
| CA_3 | STORE_003 | Mumbai-01 | Mumbai | Maharashtra | West | 19.0760 | 72.8777 |
| CA_4 | STORE_004 | Delhi-01 | Delhi | Delhi | North | 28.6139 | 77.2090 |
| TX_1 | STORE_005 | Hyderabad-01 | Hyderabad | Telangana | South | 17.3850 | 78.4867 |
| TX_2 | STORE_006 | Chennai-01 | Chennai | Tamil Nadu | South | 13.0827 | 80.2707 |
| TX_3 | STORE_007 | Pune-01 | Pune | Maharashtra | West | 18.5204 | 73.8567 |
| WI_1 | STORE_008 | Kolkata-01 | Kolkata | West Bengal | East | 22.5726 | 88.3639 |
| WI_2 | STORE_009 | Ahmedabad-01 | Ahmedabad | Gujarat | West | 23.0225 | 72.5714 |
| WI_3 | STORE_010 | Jaipur-01 | Jaipur | Rajasthan | North | 26.9124 | 75.7873 |

If you subset fewer stores on Day 2, keep only the matching rows.

### 3.2 Additional store attributes (generated, seeded)

| Column | Values |
|---|---|
| `Store_Type` | Hypermarket / Supermarket / Express |
| `Size_Sqft` | Hypermarket 40,000–70,000; Supermarket 10,000–25,000; Express 2,000–6,000 |
| `Opening_Date` | Before the first data date (all stores open for the full history) |

Choose store types so that they roughly reflect each M5 store's relative sales volume (compute total units per store and assign the biggest stores to Hypermarket). This keeps the master table consistent with the data.

### 3.3 Reference implementation

```python
def build_store_master(long_df: pd.DataFrame) -> pd.DataFrame:
    mapping = pd.read_csv(EXTERNAL_DIR / "store_mapping.csv")
    totals = long_df.groupby("store_id", observed=True)["Units_Sold"].sum().rename("total_units")
    sm = mapping.merge(totals, left_on="Source_Store_ID", right_index=True, how="inner")
    sm = sm.sort_values("total_units", ascending=False).reset_index(drop=True)
    n = len(sm)
    sm["Store_Type"] = ["Hypermarket"] * (n // 3) + ["Supermarket"] * (n // 3) + \
                       ["Express"] * (n - 2 * (n // 3))
    rng = np.random.default_rng(CFG["adaptation"]["seed"])
    size_ranges = {"Hypermarket": (40000, 70000), "Supermarket": (10000, 25000), "Express": (2000, 6000)}
    sm["Size_Sqft"] = [int(rng.integers(*size_ranges[t])) for t in sm["Store_Type"]]
    sm["Opening_Date"] = pd.Timestamp("2010-01-01")
    return sm.drop(columns="total_units").sort_values("Store_ID").reset_index(drop=True)
```

(In the mapping CSV name the first column `Source_Store_ID`.)

### Challenges
- **Honest re-labelling:** the sales patterns come from the benchmark's US stores. State this in `docs/data_sources.md`.
- **Two stores in one city:** weather is fetched once per city, so store-level weather duplicates for Bangalore. Acceptable and documented.
- **Store IDs in different formats across tables:** use `Store_ID` (`STORE_001`) everywhere in the project; `Source_Store_ID` only in the mapping.

---

## Task 4 – Convert Prices to ₹ (Daily Price Table)

### 4.1 What already exists
Day 2 joined weekly prices to each day via `wm_yr_wk`. Price is therefore already **daily** (constant within a retail week), with `NaN` for dates before an item's first price record (not yet launched).

### 4.2 Conversion approach

```text
Price_INR = sell_price_USD × Price_Factor(item)
```

- `Price_Factor` is a **constant per item** (from the product master), not per week. This keeps the relative price changes (discounts, price hikes) and the price-vs-demand relationship from the benchmark intact.
- A flat market exchange rate (about 80+) would give unrealistic Indian shelf prices for everyday items. The category scale (30 / 35 / 40) is a documented "price-level adjustment" and is configurable.
- Round to **2 decimals (paise)**, not to ₹5 or ₹10. Coarse rounding would erase small price changes that Task 5 needs to detect promotions.

### 4.3 Reference implementation

```python
# src/data/prices.py
def to_inr(long_df, product_master):
    pm = product_master[["Source_Item_ID", "Product_ID", "Price_Factor"]]
    df = long_df.merge(pm, left_on="item_id", right_on="Source_Item_ID", how="left", validate="m:1")
    assert df["Product_ID"].notna().all(), "Unmapped items found"
    df["Price"] = (df["Price"] * df["Price_Factor"]).round(2)
    return df.drop(columns=["Source_Item_ID"])

def complete_product_master(product_master, df):
    base = (df.dropna(subset=["Price"]).groupby("Product_ID")["Price"].median().rename("Base_Price"))
    pm = product_master.drop(columns=["Base_Price"], errors="ignore").merge(base, on="Product_ID", how="left")
    rng = np.random.default_rng(CFG["adaptation"]["seed"] + 1)
    lo_hi = pm["Category"].map(MARGIN)
    cost_ratio = [rng.uniform(lo, hi) for lo, hi in lo_hi]
    pm["Unit_Cost"] = (pm["Base_Price"] * np.array(cost_ratio)).round(2)
    return pm
```

(`MARGIN` is defined in `build_masters.py`; the value is the *cost as a share of price*, so costs sit below the selling price.)

### 4.4 Checks
- [ ] Price > 0 wherever it is not `NaN`
- [ ] Price ranges per category look plausible (e.g. groceries ₹30–₹1,000, household ₹60–₹2,500, hobbies ₹100–₹4,000; check against your own judgement)
- [ ] `Unit_Cost < Base_Price` for every product
- [ ] Share of `NaN` prices equals the pre-launch share seen on Day 2

### Challenges
- **Unrealistic ₹ prices:** inspect min/max per category and tune the scale factors rather than accepting the first values.
- **Missing prices (pre-launch):** do **not** fill them. They are structural and are handled in Day 4 (rows before launch are dropped by a documented rule).
- **Merge row inflation:** use `validate="m:1"` on the product merge and compare row counts before and after.

---

## Task 5 – Derive Promotion Flag and Discount %

M5 has no promotion column, so promotions are **derived from price drops**. This is an approximation and must be documented as such.

### 5.1 Method

Work at the **weekly** level (price is constant within a week) for each store-item:

1. **Reference (regular) price** = rolling median of the previous `window_weeks` weekly prices (excluding the current week, using `shift(1)`), requiring at least `min_periods` weeks.
2. **Discount %** = `max(0, 1 − Price / Reference)`.
3. **Promotion = 1** if `Discount_Pct ≥ min_discount` (default 5%), otherwise 0.
4. Weeks without a reference (first few weeks after launch) get `Promotion = 0`, `Discount_Pct = 0`.
5. `Regular_Price` = reference price, falling back to the actual price where no reference exists.
6. Map the weekly results back to every day of that week.

Using only **past** prices for the reference avoids look-ahead and keeps the feature realistic for forecasting.

### 5.2 Reference implementation

```python
def derive_promotions(df, window_weeks=13, min_periods=4, min_discount=0.05):
    keys = ["store_id", "item_id"]
    wk = (df[keys + ["wm_yr_wk", "Price"]].drop_duplicates()
          .sort_values(keys + ["wm_yr_wk"]).reset_index(drop=True))

    wk["Regular_Price"] = (wk.groupby(keys, observed=True)["Price"]
                           .transform(lambda s: s.shift(1).rolling(window_weeks, min_periods=min_periods).median()))
    disc = 1 - wk["Price"] / wk["Regular_Price"]
    wk["Discount_Pct"] = disc.clip(lower=0).fillna(0).round(4)
    wk["Promotion"] = (wk["Discount_Pct"] >= min_discount).astype("int8")
    wk["Regular_Price"] = wk["Regular_Price"].fillna(wk["Price"]).round(2)

    out = df.merge(wk[keys + ["wm_yr_wk", "Regular_Price", "Discount_Pct", "Promotion"]],
                   on=keys + ["wm_yr_wk"], how="left", validate="m:1")
    return out
```

### 5.3 Calibrate the threshold (important)
Run these diagnostics, then adjust `min_discount` and `window_weeks`:

| Diagnostic | Healthy range / what to look for |
|---|---|
| Share of store-item-weeks flagged as promotion | Roughly 5–20% |
| Distribution of `Discount_Pct` for flagged weeks | Mostly 5–40% |
| Average units on promo vs non-promo weeks | Promo weeks higher on average (confirms the signal) |
| Persistent price cuts | A permanent price drop should stop counting as a promotion after the median catches up |
| Items with zero promotion weeks | Some is fine; most items having zero means the threshold is too high |

M5 price changes are often small, so if almost nothing is flagged at 5%, lower `min_discount` (for example to 3%) and document the final choice.

### 5.4 Document the limitation
Write in the data dictionary: *"`Promotion` is derived from price drops relative to a rolling regular price. It approximates, but is not identical to, a real promotion calendar."*

### Challenges
- **Permanent price cuts mislabelled as promotions:** the rolling median reference solves this partly; check a few items visually (plot weekly price with the flag).
- **Price increases:** these produce `Discount_Pct = 0`; do not flag them.
- **Tiny price changes (cents):** may be noise; the threshold filters them out.
- **Groupby performance on large data:** the weekly table is far smaller than the daily table (about 1/7 of the rows), which is why the derivation works weekly.
- **Look-ahead leakage:** never compute the reference using future weeks.

---

## Task 6 – Build the Indian Holiday and Festival Calendar

### 6.1 Outputs

One row per date covering the full data range (the M5 dates run from early 2011 to mid-2016; use your actual min/max `Date`).

| Column | Description |
|---|---|
| `Date` | Calendar date |
| `Holiday` | 1 if a national public holiday (or a major festival day), else 0 |
| `Holiday_Name` | Name of the holiday (blank if none) |
| `Festival_Window` | 1 if within the pre-festival shopping window (default: 7 days before a major festival, including the day) |
| `Festival_Name` | Festival that the window belongs to |
| `Regional_Holiday` | Optional: state-level holiday flag (stored per state, not per date, if used) |

### 6.2 Sources
1. **`holidays` Python library** (`holidays.India(years=...)`) for national holidays; it also accepts a `subdiv` argument for state holidays.
2. **Custom festival table** (`data/external/holidays_india.csv`) for festivals and shopping events the library lacks or covers inconsistently for older years, such as Diwali, Dussehra, Holi, Eid, Ganesh Chaturthi, Pongal / Makar Sankranti, Onam, Raksha Bandhan, plus fixed-date shopping events (Republic Day sale, Independence Day sale, year-end sale).

> **Verify coverage:** the `holidays` library may not include every religious festival for every year from 2011. After building the calendar, check that each major festival (Diwali, Holi, Eid, Dussehra) appears **once per year** for every year in your range. For any that are missing, add the date to the custom CSV from an authoritative source (official government holiday notification or a published festival calendar). Lunar-calendar festival dates move every year, so never assume a fixed date.
>
> Example of a custom-table row format (verify every date against a reliable calendar before use):
> ```csv
> date,name,type
> 2013-11-03,Diwali,festival
> 2014-10-23,Diwali,festival
> 2015-11-11,Diwali,festival
> ```

### 6.3 Reference implementation

```python
# src/data/calendar_india.py
import holidays
import pandas as pd
from src.config import EXTERNAL_DIR, CFG

FIXED = {  # month, day -> name (shopping/fixed-date events)
    (1, 1): "New Year", (1, 26): "Republic Day", (8, 15): "Independence Day",
    (10, 2): "Gandhi Jayanti", (12, 25): "Christmas",
}
MAJOR_FESTIVALS = {"Diwali", "Holi", "Dussehra", "Eid", "Christmas", "Pongal", "Onam",
                   "Ganesh Chaturthi", "Raksha Bandhan", "Republic Day", "Independence Day"}

def build_holiday_calendar(start, end) -> pd.DataFrame:
    dates = pd.date_range(start, end, freq="D")
    years = range(dates.min().year, dates.max().year + 1)

    names = {pd.Timestamp(d): n for d, n in holidays.India(years=years).items()}
    custom_path = EXTERNAL_DIR / "holidays_india.csv"
    if custom_path.exists():
        custom = pd.read_csv(custom_path, parse_dates=["date"])
        for d, n in zip(custom["date"], custom["name"]):
            names.setdefault(pd.Timestamp(d), n)
    for d in dates:
        names.setdefault(d, FIXED.get((d.month, d.day)))
    cal = pd.DataFrame({"Date": dates})
    cal["Holiday_Name"] = cal["Date"].map(names)
    cal["Holiday"] = cal["Holiday_Name"].notna().astype("int8")

    # pre-festival shopping window
    window = CFG["adaptation"]["festival_uplift"]["window_days"]
    cal["Festival_Window"] = 0
    cal["Festival_Name"] = None
    for d, n in cal.loc[cal["Holiday"] == 1, ["Date", "Holiday_Name"]].itertuples(index=False):
        if any(f in str(n) for f in MAJOR_FESTIVALS):
            mask = (cal["Date"] > d - pd.Timedelta(days=window)) & (cal["Date"] <= d)
            cal.loc[mask, "Festival_Window"] = 1
            cal.loc[mask, "Festival_Name"] = n
    return cal
```

Save the result to `data/external/holidays_india.parquet`.

### 6.4 Checks
- [ ] Number of holidays per year looks reasonable (typically a few to a couple of dozen)
- [ ] Each major festival appears once per year in the range
- [ ] No duplicate dates; one row per date
- [ ] `Festival_Window` days are contiguous blocks before festivals
- [ ] Spot-check three years' Diwali and Holi dates against an external calendar

### Challenges
- **Lunar-calendar festivals** move every year; library coverage can be incomplete. Always run the "once per year" check.
- **State-specific festivals** (Pongal in Tamil Nadu, Onam in Kerala): the national flag does not capture them. Keep the project to a national flag plus festival windows, and note state-level holidays as a future enhancement (or use `holidays.India(subdiv=...)` per store state).
- **The date-mismatch problem (important):** M5's real sales respond to **US** events (Thanksgiving, Super Bowl, July 4th). Indian festival flags will therefore show little real effect in the raw data. Task 8 addresses this; otherwise the EDA will find "no holiday impact" and the Holiday feature will be weak.
- **Multiple holidays on the same date:** keep one name per date; use `setdefault` as shown, or concatenate.

---

## Task 7 – Fetch and Cache Weather Data

### 7.1 Source
**Open-Meteo Historical Weather API** (free, no API key for non-commercial use; check its terms and credit it in the README).

```text
GET https://archive-api.open-meteo.com/v1/archive
  ?latitude=<lat>&longitude=<lon>
  &start_date=<YYYY-MM-DD>&end_date=<YYYY-MM-DD>
  &daily=temperature_2m_mean,precipitation_sum
  &timezone=Asia%2FKolkata
```

Fetch **once per city** (Bangalore's two stores share data), 9 cities for the 10-store setup, and **cache** every response to `data/external/weather/<city>_<start>_<end>.csv`.

### 7.2 Reference implementation

```python
# src/data/weather.py
import time
import numpy as np
import pandas as pd
import requests
from src.config import EXTERNAL_DIR

URL = "https://archive-api.open-meteo.com/v1/archive"
CACHE = EXTERNAL_DIR / "weather"

def fetch_city_weather(city, lat, lon, start, end) -> pd.DataFrame:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{city.lower()}_{start}_{end}.csv"
    if path.exists():
        return pd.read_csv(path, parse_dates=["Date"])
    params = {"latitude": lat, "longitude": lon, "start_date": start, "end_date": end,
              "daily": "temperature_2m_mean,precipitation_sum", "timezone": "Asia/Kolkata"}
    r = requests.get(URL, params=params, timeout=60)
    r.raise_for_status()
    d = r.json()["daily"]
    df = pd.DataFrame({"Date": pd.to_datetime(d["time"]),
                       "Temperature": d["temperature_2m_mean"],
                       "Rainfall_mm": d["precipitation_sum"]})
    df.to_csv(path, index=False)
    time.sleep(1.5)                      # be polite to the free API
    return df

def fallback_weather(city_seed, start, end, mean_temp=27, amp=6):
    """Seasonal synthetic temperature if the API is unavailable. Document if used."""
    rng = np.random.default_rng(city_seed)
    dates = pd.date_range(start, end)
    doy = dates.dayofyear.values
    temp = mean_temp + amp * np.sin(2 * np.pi * (doy - 100) / 365) + rng.normal(0, 1.2, len(dates))
    rain = np.clip(rng.gamma(0.4, 6, len(dates)) * (np.sin(2 * np.pi * (doy - 150) / 365) > 0.3), 0, None)
    return pd.DataFrame({"Date": dates, "Temperature": temp.round(1), "Rainfall_mm": rain.round(1)})
```

### 7.3 Build the per-store weather table
Join `store_master.City` to each city's weather and produce `(Date, Store_ID, Temperature, Rainfall_mm)`.

### 7.4 Checks
- [ ] Temperature between roughly 5 °C and 48 °C for Indian cities; no extreme outliers
- [ ] Missing share is near 0%
- [ ] Seasonal pattern looks right (Delhi cold in winter and hot in May–June; Mumbai heavy rainfall in the monsoon, roughly June–September)
- [ ] One row per (Date, city)

### Challenges
- **API limits/failures:** use caching so you call each city once; split by year if a long range returns an error; use `fallback_weather` and **document** if you must.
- **Coverage period:** the archive covers the 2011–2016 dates of M5, so the weather is real for those dates, matching the (re-labelled) Indian scenario.
- **Missing days:** forward-fill at most 1–2 days; larger gaps are left for Day 4.
- **Weather effect on demand is weak in M5** (no weather-sensitive categories such as beverages or ice cream). Expect low correlation in EDA, and report that honestly rather than forcing an effect. If you want a visible effect, apply an optional, documented temperature uplift to a subset of items (see Task 8's note).

---

## Task 8 – (Recommended) Apply a Documented Festival Demand Uplift

### 8.1 Why
The benchmark's seasonality follows the US calendar. Without any adjustment, the Indian `Holiday` and `Festival_Window` features carry almost no signal, so the dashboard's holiday analysis and the models' holiday features would look empty. A **small, transparent, seeded** uplift lets the Indian festival features carry realistic signal.

### 8.2 Approach
- Multiply demand by `1 + uplift` for rows in a `Festival_Window`, using category-specific uplifts from `config.yaml` (for example Grocery +25%, Household +20%, Toys +15%).
- Use **stochastic rounding** so counts stay integer: `floor(x)` plus 1 with probability equal to the fractional part (seeded).
- Keep the original value in `Units_Sold_Original` for auditability.
- Label the result honestly as **semi-synthetic** in the README and data documentation.
- Make it switchable (`festival_uplift.enabled`) so the pure benchmark version can be reproduced.

### 8.3 Reference implementation

```python
# src/data/demand_adjust.py
import numpy as np
from src.config import CFG

def apply_festival_uplift(df):
    cfg = CFG["adaptation"]["festival_uplift"]
    df["Units_Sold_Original"] = df["Units_Sold"]
    if not cfg["enabled"]:
        return df
    rng = np.random.default_rng(CFG["adaptation"]["seed"] + 2)
    uplift = df["Category"].map(cfg["by_category"]).fillna(0.0).to_numpy()
    factor = 1.0 + uplift * df["Festival_Window"].to_numpy()
    x = df["Units_Sold_Original"].to_numpy() * factor
    base = np.floor(x)
    frac = x - base
    df["Units_Sold"] = (base + (rng.random(len(df)) < frac)).astype("int16")
    return df
```

### 8.4 Optional second adjustment
A mild temperature effect on one department (for example `+1.5%` demand per °C above 30 °C for "Snacks & Beverages"). Apply it only if you want a visible weather effect, record it in the config and documentation, and keep the original column.

### 8.5 Sanity checks
- [ ] Total units change by only a few percent overall
- [ ] Festival-window days show a visible, but not absurd, uplift versus the same weekday outside the window
- [ ] Promotion and price relationships from the benchmark still hold (average units on promo weeks still higher)
- [ ] `Units_Sold` remains non-negative integers

### Challenges
- **Over-engineering the signal:** keep the uplift modest. Models that see unrealistically clean festival effects will look too good.
- **Transparency:** this edit changes the benchmark. The README must say the dataset is "benchmark-based with documented, seeded adjustments".
- **Leakage-style confusion:** the uplift depends only on the calendar and category, not on the target, so it does not leak.
- **Skip option:** if you prefer to keep the benchmark pure, set `enabled: false` and state in the EDA that Indian-festival effects are weak by construction.

---

## Task 9 – Simulate Inventory

### 9.1 Why simulate
The benchmark has no inventory, but Week 3 (reorder point, safety stock, overstock and low-stock alerts) needs a stock history. The simulation produces a plausible stock-on-hand series that is **consistent with sales**.

### 9.2 Simulation design (periodic review, order-up-to policy)

For each store-product series, from its first sale/price date:

| Element | Rule |
|---|---|
| Review period `R` | Every 7 days (with a random weekday offset per series so stores don't all order on the same day) |
| Lead time `L` | `Lead_Time_Days` from the product master |
| Demand estimate | Rolling mean `μ` and standard deviation `σ` of the previous 28 days (shifted so no look-ahead) |
| Order-up-to level `S` | `μ × (R + L) + z × σ × sqrt(R + L)`, with `z = 1.65` (about 95% service) |
| Order quantity | `ceil(S − inventory position)`, rounded up to `Min_Order_Qty`, never negative |
| Inventory position | On-hand stock + on-order stock |
| Receipts | Order placed on day `t` arrives on day `t + L` |
| Opening stock | `initial_cover_days × average early demand` |
| Daily update | `available = stock + receipts`; `closing = max(0, available − Units_Sold)` |
| Stock-out | `Stockout_Flag = 1` when closing stock is 0 |
| Shortfall | `Shortfall = max(0, Units_Sold − available)` (kept as an audit column) |

> **Assumption (document it):** observed `Units_Sold` is treated as given. On the rare days when recorded sales exceed available stock (a shortfall), the retailer is assumed to have covered the gap through emergency transfers. These days are flagged so Day 4 and Week 3 can analyse them. This keeps the target unchanged while still giving realistic low-stock and stock-out events.

### 9.3 Reference implementation

```python
# src/data/inventory.py
import numpy as np
import pandas as pd
from src.config import CFG

def simulate_series(sales, lead_time, moq, seed, review=7, z=1.65, window=28, cover=14):
    n = len(sales)
    s = pd.Series(sales, dtype="float64")
    early = max(s.iloc[:14].mean(), 0.5)
    mu = s.shift(1).rolling(window, min_periods=7).mean().fillna(early).to_numpy()
    sd = s.shift(1).rolling(window, min_periods=7).std().fillna(0).to_numpy()

    rng = np.random.default_rng(seed)
    offset = int(rng.integers(0, review))
    arrivals = np.zeros(n + lead_time + 2)
    stock = float(np.ceil(early * cover))
    on_order = 0.0
    inv = np.zeros(n); short = np.zeros(n)

    for t in range(n):
        stock += arrivals[t]
        on_order -= arrivals[t]
        if (t + offset) % review == 0:
            S = mu[t] * (review + lead_time) + z * sd[t] * np.sqrt(review + lead_time)
            qty = max(0.0, S - (stock + on_order))
            if qty > 0:
                qty = np.ceil(qty / moq) * moq
                arrivals[t + lead_time] += qty
                on_order += qty
        available = stock
        short[t] = max(0.0, sales[t] - available)
        stock = max(0.0, available - sales[t])
        inv[t] = stock
    return inv, short

def simulate_inventory(df, product_master):
    cfg = CFG["adaptation"]["inventory"]
    pm = product_master.set_index("Product_ID")[["Lead_Time_Days", "Min_Order_Qty"]]
    df = df.sort_values(["Store_ID", "Product_ID", "Date"]).reset_index(drop=True)
    df["Inventory"] = np.nan
    df["Shortfall"] = np.nan

    for k, (key, idx) in enumerate(df.groupby(["Store_ID", "Product_ID"], sort=False).groups.items()):
        sub = df.loc[idx]
        launched = sub["Price"].notna().to_numpy()
        if not launched.any():
            continue
        first = launched.argmax()
        pos = sub.index[first:]
        inv, short = simulate_series(
            sub.loc[pos, "Units_Sold"].to_numpy(),
            int(pm.loc[key[1], "Lead_Time_Days"]), int(pm.loc[key[1], "Min_Order_Qty"]),
            seed=CFG["adaptation"]["seed"] + k,
            review=cfg["review_days"], z=cfg["service_z"],
            window=cfg["window"], cover=cfg["initial_cover_days"])
        df.loc[pos, "Inventory"] = inv
        df.loc[pos, "Shortfall"] = short
    df["Stockout_Flag"] = (df["Inventory"] == 0).astype("float").where(df["Inventory"].notna())
    return df
```

Runtime: roughly thousands of series × ~1,900 days is a few million loop steps (about one to several minutes in pure Python). If too slow, process stores in parallel (`joblib`) or compile `simulate_series` with `numba`.

### 9.4 Checks and calibration
| Metric | Healthy value |
|---|---|
| Inventory ≥ 0 | Always |
| Share of days with closing stock of 0 (`Stockout_Flag`) | Roughly 1–8% (varies with intermittency; slow movers produce more zeros between orders) |
| Share of days with `Shortfall > 0` | Very low (below about 2%) |
| Average days of cover (`Inventory / mean daily demand`) | About 7–25 days |
| Some overstock visible | A few series with cover much higher than average (slow movers) |

Tune `service_z`, `review_days` and `initial_cover_days` if the stock-out or cover values look unrealistic, and plot 3–4 series (sales vs closing inventory) to see the sawtooth restocking pattern.

### Challenges
- **Intermittent demand breaks the demand estimate:** items with mostly zeros give σ ≈ 0 and tiny order quantities, creating many stock-outs. The MOQ and a minimum order-up-to level (for example at least one MOQ for any active item) mitigate this.
- **Look-ahead leakage in the policy:** use only past sales in `μ` and `σ` (the `shift(1)` does this).
- **Censored demand:** real stock-outs hide demand. This dataset does not model lost sales; state it as a limitation and keep `Shortfall` and `Stockout_Flag` for analysis.
- **Speed:** a Python loop over all series is slow. Subsetting on Day 2 keeps it manageable; otherwise parallelise.
- **Realism vs. simplicity:** the simulation is one policy for all items. Good enough for the portfolio. Document it, and do not present simulated inventory as real company data.

---

## Task 10 – Assemble the Target Schema

### 10.1 Merge order

```text
long table (Date, store_id, item_id, Units_Sold, Price, wm_yr_wk, ...)
 + product master  → Product_ID, Category, Department
 + store master    → Store_ID, City
 + holiday calendar (on Date)            → Holiday, Holiday_Name, Festival_Window
 + weather (on Date, City)               → Temperature, Rainfall_mm
 + promotion/discount (from Task 5)      → Promotion, Discount_Pct, Regular_Price
 → festival demand adjustment (Task 8)   → Units_Sold (adjusted), Units_Sold_Original
 → inventory simulation (Task 9)         → Inventory, Stockout_Flag, Shortfall
 → Revenue = Units_Sold × Price
```

### 10.2 Final columns

**Core schema (as defined on Day 1):**

```text
Date, Store_ID, Product_ID, Category, Price, Promotion, Holiday,
Temperature, Inventory, Units_Sold, Revenue
```

**Supporting columns kept for analysis and later steps:**

| Column | Used for |
|---|---|
| `Department`, `City` | EDA, dashboard filters |
| `Discount_Pct`, `Regular_Price` | Price/promotion analysis, discount feature |
| `Rainfall_mm` | Weather feature |
| `Holiday_Name`, `Festival_Window` | Holiday impact analysis, festival features |
| `Stockout_Flag`, `Shortfall` | Inventory analysis (Week 3) and cleaning checks |
| `Units_Sold_Original` | Audit trail for the festival adjustment |

### 10.3 Reference implementation

```python
# src/data/assemble.py
import pandas as pd
from src.config import RAW_DIR, INTERIM_DIR, EXTERNAL_DIR

CORE = ["Date", "Store_ID", "Product_ID", "Category", "Price", "Promotion", "Holiday",
        "Temperature", "Inventory", "Units_Sold", "Revenue"]
EXTRA = ["Department", "City", "Discount_Pct", "Regular_Price", "Rainfall_mm", "Holiday_Name",
         "Festival_Window", "Stockout_Flag", "Shortfall", "Units_Sold_Original"]

def assemble(df, product_master, store_master, holiday_cal, weather):
    n0 = len(df)
    df = df.merge(store_master[["Source_Store_ID", "Store_ID", "City"]],
                  left_on="store_id", right_on="Source_Store_ID", how="left", validate="m:1")
    df = df.merge(product_master[["Product_ID", "Category", "Department"]],
                  on="Product_ID", how="left", validate="m:1")
    df = df.merge(holiday_cal[["Date", "Holiday", "Holiday_Name", "Festival_Window"]],
                  on="Date", how="left", validate="m:1")
    df = df.merge(weather[["Date", "City", "Temperature", "Rainfall_mm"]],
                  on=["Date", "City"], how="left", validate="m:1")
    assert len(df) == n0, "Row count changed during merges"

    # adjustment and inventory are applied after the merges (Tasks 8 and 9)
    # Revenue is computed last from the final units and price
    df["Revenue"] = (df["Units_Sold"] * df["Price"]).round(2)
    out = df[CORE + [c for c in EXTRA if c in df.columns]]
    out = out.sort_values(["Store_ID", "Product_ID", "Date"]).reset_index(drop=True)
    out.to_parquet(RAW_DIR / "retail_demand_raw.parquet", index=False)
    return out
```

In the actual pipeline run Task 8 and Task 9 between the merges and the `Revenue` line.

### 10.4 Sample file for the repository
Save a small sample (a few thousand rows, a few stores and products) to `data/sample/sample_sales.csv` so reviewers can see the schema without the full data. **Only commit a sample if the source's terms permit it;** otherwise generate the sample from the synthetic generator (Path C).

### Challenges
- **Merge key types:** `Date` must be `datetime64` in every table; `City` strings must match exactly (strip whitespace).
- **Row inflation or loss:** assert row counts after every merge (`validate="m:1"` plus the assertion above).
- **Revenue consistency:** compute revenue **after** the demand adjustment, never before.
- **`NaN` handling:** pre-launch rows keep `Price = NaN`, `Inventory = NaN` and `Revenue = NaN`. Do not fill them today; Day 4 documents and applies the rule.
- **Memory:** use categoricals for IDs and downcast numeric columns before saving.

---

## Task 11 – Validate the Assembled Dataset

Write `src/data/validate_raw.py` that prints a report (and fails on critical errors).

### 11.1 Validation checklist

**Structure**
- [ ] All 11 core columns present, correct dtypes
- [ ] Unique key: no duplicate `(Date, Store_ID, Product_ID)`
- [ ] Row count = number of series × number of days
- [ ] Date range complete and contiguous, no missing days per series
- [ ] Every `Store_ID` exists in the store master; every `Product_ID` in the product master

**Values**
- [ ] `Units_Sold` integer and ≥ 0
- [ ] `Price` > 0 where not null; `Price` null only before launch
- [ ] `Revenue == Units_Sold × Price` (within rounding)
- [ ] `Promotion` and `Holiday` only take 0/1
- [ ] `Inventory` ≥ 0 where not null
- [ ] `Temperature` within a plausible range, few missing

**Distribution sanity**
- [ ] Promotion share in the calibrated range
- [ ] Holiday and festival-window share plausible (holidays are a small share of days)
- [ ] Stock-out share and days-of-cover in the healthy ranges from Task 9
- [ ] Total units close to the Day 2 total (difference explained by the festival uplift)

**Traceability**
- [ ] Every `Product_ID` and `Store_ID` maps back to the source IDs
- [ ] Config values (seed, scale factors, thresholds) written to a run log

### 11.2 Write a profile summary
Save `reports/raw_dataset_profile.md` containing: row/column counts, date range, number of stores/products/categories, % missing per column, promotion rate, holiday rate, stock-out rate, price range per category, total units and revenue.

### Challenges
- **Silent logic errors** (misaligned merges, wrong price joins) show up only in these checks, so make the validation script fail loudly.
- **Different counts than Day 2:** reconcile them (festival uplift explains unit differences; nothing else should).

---

## Task 12 – Finalise the Data Dictionary and Documentation

### 12.1 `docs/data_dictionary.md`

Use this table for every column (core and supporting):

| Column | Type | Description | Source | Derivation / Rule | Allowed values / range | Nulls |
|---|---|---|---|---|---|---|
| `Date` | datetime | Calendar day (IST) | M5 calendar | Mapped from `d_*` index | Contiguous daily range | No |
| `Store_ID` | string | Store identifier (`STORE_001`…) | Store master | M5 store mapped to Indian store | In store master | No |
| `Product_ID` | string | Product identifier (`PROD_0001`…) | Product master | Sorted M5 `item_id`, enumerated | In product master | No |
| `Category` | string | Product category | Category mapping | M5 `cat_id` renamed | 3 values | No |
| `Price` | float (₹) | Selling price that day | M5 `sell_price` | × item `Price_Factor`, rounded to 2 dp | > 0 | Yes, before launch |
| `Promotion` | int8 | Promotion flag | Derived | Price ≥ 5% below rolling regular price | 0 / 1 | No |
| `Holiday` | int8 | Public holiday or major festival day | `holidays` library + custom table | National holiday calendar | 0 / 1 | No |
| `Temperature` | float (°C) | Daily mean temperature in the store's city | Open-Meteo | City-level | Plausible range | Rare |
| `Inventory` | float/int | Closing stock on hand | Simulated | Order-up-to policy simulation | ≥ 0 | Yes, before launch |
| `Units_Sold` | int16 | **Target:** units sold that day | M5 (adjusted) | Festival uplift if enabled | ≥ 0 | No |
| `Revenue` | float (₹) | Daily revenue | Derived | `Units_Sold × Price` | ≥ 0 | Yes, before launch |
| `Department` | string | Department | Department mapping | M5 `dept_id` renamed | 7 values | No |
| `City` | string | Store city | Store master | | | No |
| `Discount_Pct` | float | Discount vs regular price | Derived | `max(0, 1 − Price/Regular_Price)` | 0–1 | No |
| `Regular_Price` | float (₹) | Rolling reference price | Derived | Median of previous 13 weeks | > 0 | Rare |
| `Rainfall_mm` | float | Daily precipitation | Open-Meteo | | ≥ 0 | Rare |
| `Holiday_Name` | string | Holiday name | Calendar | | | Yes |
| `Festival_Window` | int8 | Within 7 days before a major festival | Derived | | 0 / 1 | No |
| `Stockout_Flag` | float | Closing stock is zero | Simulated | | 0 / 1 | Yes, before launch |
| `Shortfall` | float | Sales above available stock | Simulated | | ≥ 0 | Yes, before launch |
| `Units_Sold_Original` | int16 | Units before festival adjustment | M5 | | ≥ 0 | No |

Also add: the **supporting-table dictionaries** (`product_master`, `store_master`, `holidays_india`, weather) and a **lineage diagram** (source → transformation → column).

### 12.2 Update `docs/data_sources.md`
- Final subset sizes (stores, products, rows, date range)
- All adaptations with their parameters (price scale, promo threshold, festival uplift, inventory policy)
- Weather source and fallback usage (if any)
- A prominent **"What is real, derived and simulated"** table:

| Column group | Status |
|---|---|
| Units sold, base price movements, weekly seasonality | Real (benchmark) |
| Store names/cities, product names, categories, department names | Re-labelled |
| ₹ prices | Scaled from benchmark prices |
| Promotion, discount, regular price | Derived from prices |
| Holiday, festival windows | Real Indian calendar (library + custom table) |
| Festival demand uplift | Simulated adjustment (documented, seeded, optional) |
| Temperature, rainfall | Real (Open-Meteo) or seeded fallback |
| Inventory, stock-out, shortfall | Simulated |

### 12.3 README update
Add a "Dataset" section: source credit, "benchmark-based with documented adaptations", how to regenerate (`python -m src.data.assemble`), and that raw data files are not included.

### Challenges
- **Documentation honesty is the credibility of the project.** A reviewer who finds an undisclosed simulation will distrust everything else.
- **Keeping the dictionary and the data in sync:** generate the column list and dtypes from the dataframe and compare against the dictionary in a test.

---

## Task 13 – (Optional) Controlled Data-Quality Issues

The benchmark is already clean, which would make Day 4 (cleaning) trivial. If you want Day 4 to demonstrate real cleaning work, you may **inject a small, fully documented set of realistic faults** into `retail_demand_raw.parquet`, and keep the clean version aside for verification.

| Fault | Suggested amount |
|---|---|
| Duplicate rows | About 0.1% |
| Missing `Temperature` | About 0.5% |
| Missing `Promotion` | About 0.3% |
| A handful of negative `Units_Sold` | 20–50 rows |
| A few extreme outliers in `Units_Sold` | 20–50 rows |
| Inconsistent ID formatting (lowercase, extra spaces) | About 0.1% |
| A few impossible dates | A handful of rows |

Rules:
- Use a seeded function in `src/data/inject_issues.py` that writes an **injection log** (`reports/injected_issues_log.csv` with row key, fault type and original value).
- Keep a clean copy (`data/interim/retail_demand_clean_truth.parquet`) so Day 4's pipeline can be **verified** against ground truth.
- State in the documentation that faults were injected to demonstrate the cleaning pipeline.
- Make it switchable and skip it if you prefer to present the dataset as-is.

### Challenges
- **Honesty:** never present injected faults as real-world dirt; say so plainly.
- **Overdoing it:** keep volumes small and realistic, because heavy corruption makes the project look contrived.

---

## Task 14 – Tests, Commit and Push

### 14.1 Tests (`tests/test_data_assembly.py`)

```python
import numpy as np
import pandas as pd
from src.data.inventory import simulate_series

def test_inventory_never_negative():
    sales = np.random.default_rng(0).poisson(3, 200)
    inv, short = simulate_series(sales, lead_time=3, moq=6, seed=1)
    assert (inv >= 0).all() and (short >= 0).all()

def test_revenue_consistency():
    df = pd.DataFrame({"Units_Sold": [2, 3], "Price": [10.0, 5.5]})
    df["Revenue"] = (df["Units_Sold"] * df["Price"]).round(2)
    assert df["Revenue"].tolist() == [20.0, 16.5]
```

Add tests for: promotion derivation (a clear 20% price drop is flagged; a price rise is not), unique keys after assembly, holiday calendar (one row per date, major festival present each year), and the dictionary-vs-dataframe columns check.

### 14.2 Commit

```bash
git status                                  # data files must not be listed
git add src docs tests config.yaml data/external/*.csv
git commit -m "feat: add product/store masters, promo derivation, holidays, weather, inventory simulation and dataset assembly"
git checkout dev && git merge feature/data-adaptation
git push origin dev
```

(`data/external/*.csv` mapping files are small and are the only external files worth committing; the `.gitignore` from Day 1 ignores everything else under `data/`. Add an exception line such as `!data/external/store_mapping.csv` and `!data/external/category_mapping.csv` if Git ignores them.)

---

## Path C – Synthetic Generator (only if you chose fully synthetic data)

Build the same tables from a simulator in `src/data/generator.py`. Settle the parameters below, write them in `docs/data_sources.md`, and keep everything seeded.

### C.1 Parameters

| Parameter | Suggested value |
|---|---|
| History | 3 years daily (for example 2023-01-01 to 2025-12-31) |
| Stores | 8–10 across Indian cities (use the store mapping above) |
| Products | 100–150 across 5–6 categories |
| Base daily demand per series | `store_scale × product_popularity`, popularity log-normal (a few fast sellers, many slow) |
| Trend | Mild growth (for example 5–15% per year), category-dependent |
| Weekly seasonality | Weekend uplift of 10–35%, category-dependent |
| Yearly seasonality | Festival season (October–November) peak, summer and year-end effects |
| Holiday effect | Spikes in the 7 days before major festivals |
| Promotion | Random promo calendar per product, uplift 10–40%, with a post-promo dip |
| Price elasticity | Negative, category-dependent (for example −0.8 to −2.0) |
| Weather effect | Temperature-sensitive categories only |
| Noise | Poisson or negative binomial (integer counts) |
| Intermittency | Extra zero-inflation for slow movers |
| Anomalies | A few stock-outs and one-off spikes |

### C.2 Core generator logic

```python
import numpy as np
import pandas as pd

def generate_demand(dates, store_scale, popularity, cat, promo, price_ratio, temp, festival, rng):
    n = len(dates)
    t = np.arange(n)
    trend = 1 + cat["trend_per_year"] * t / 365
    dow = dates.dayofweek.values
    weekly = 1 + cat["weekend_uplift"] * (dow >= 5)
    doy = dates.dayofyear.values
    yearly = 1 + cat["yearly_amp"] * np.sin(2 * np.pi * (doy - cat["peak_doy"]) / 365)
    holiday = 1 + cat["festival_uplift"] * festival
    promo_eff = 1 + cat["promo_uplift"] * promo
    price_eff = price_ratio ** cat["elasticity"]            # elasticity < 0, price_ratio = price / regular
    weather = 1 + cat["temp_coef"] * (temp - 27)

    mu = store_scale * popularity * trend * weekly * yearly * holiday * promo_eff * price_eff * weather
    mu = np.clip(mu, 0.01, None)
    # gamma-Poisson (negative binomial) for overdispersed counts
    k = cat["dispersion"]                                     # smaller k = more noise
    lam = rng.gamma(k, mu / k)
    return rng.poisson(lam)
```

Then build the same supporting tables (price series with a regular price plus promo discounts, holiday calendar, weather, inventory simulation) and assemble to the same target schema. Because every effect is known, record the **true parameters** in `docs/data_sources.md`; they allow you later to check whether the models recover the true seasonality and promotion lift.

### C.3 Challenges
- **Too-clean signals:** keep noise high enough that MAPE for individual series stays realistic.
- **Credibility:** explain that the generator is the *data source*, and describe the components. Do not call it real data.
- **Intermittency:** model slow movers explicitly, otherwise the dataset will not exercise the WMAPE decision from Day 1.

---

## Day 3 Challenges Summary

| Challenge | Impact | Mitigation |
|---|---|---|
| Pipeline order dependencies | Wrong or inconsistent columns | Fixed order; one command runs everything |
| Unrealistic ₹ prices | Looks fake, distorts revenue | Per-category scale factors, inspect ranges, tune |
| Rounding erases price changes | Promotions undetectable | Keep 2 decimals, never round to ₹5/₹10 |
| Promotion derivation noise | Weak or wrong promo feature | Past-only rolling median reference, calibrate threshold, plot examples |
| Permanent price cuts flagged as promos | Biased promo effect | Median reference lets the baseline adjust |
| Holiday library gaps for older years | Missing festivals | "Once per year" check, custom CSV from authoritative sources |
| US-calendar seasonality vs Indian festivals | No holiday signal in EDA | Documented, seeded festival uplift (or accept and report weak effect) |
| Weather API limits/failures | Missing columns | Cache, one call per city, split ranges, documented fallback |
| Weak weather–demand link in M5 | Low feature value | Report honestly; optional documented effect |
| Intermittent demand in inventory simulation | Many stock-outs | Minimum order-up-to level, MOQ, calibrate z and cover |
| Look-ahead leakage in rolling stats | Unrealistic features/policy | Always `shift(1)` before rolling |
| Python-loop speed | Slow runs | Subset, parallelise or use numba |
| Merge duplication | Silent row inflation | `validate="m:1"`, row-count assertions |
| Simulated data presented as real | Credibility and trust risk | "Real / derived / simulated" table in docs and README |
| Source licence | Legal and credibility risk | Credit source, keep raw data out of Git, sample only if permitted |
| Too-clean dataset | Trivial Day 4 | Optional, fully logged fault injection |

---

## Day 3 Deliverables Checklist

**Tables**
- [ ] `product_master.parquet` (IDs, categories, departments, price factor, base price, unit cost, lead time, MOQ)
- [ ] `store_master.parquet` and `data/external/store_mapping.csv`
- [ ] `data/external/category_mapping.csv`
- [ ] `holidays_india.parquet` (complete, festival-checked)
- [ ] `data/external/weather/*.csv` (one per city, cached) or documented fallback

**Derived columns**
- [ ] INR `Price` with plausible ranges
- [ ] `Promotion`, `Discount_Pct`, `Regular_Price` (calibrated, diagnostics saved)
- [ ] Festival uplift applied (or deliberately disabled and documented), `Units_Sold_Original` kept
- [ ] `Inventory`, `Stockout_Flag`, `Shortfall` simulated and calibrated
- [ ] `Revenue` computed from final units and price

**Dataset**
- [ ] `data/raw/retail_demand_raw.parquet` with the full target schema and supporting columns
- [ ] Validation script passes; `reports/raw_dataset_profile.md` written
- [ ] (Optional) sample file and injected-issue log

**Documentation**
- [ ] `docs/data_dictionary.md` finalised for every column and supporting table
- [ ] `docs/data_sources.md` updated, including the "real / derived / simulated" table
- [ ] README "Dataset" section added

**Code and Git**
- [ ] All steps live in `src/data/` and run end-to-end with `python -m src.data.assemble`
- [ ] Tests passing (`pytest -q`)
- [ ] Work committed on `feature/data-adaptation`, merged to `dev`, pushed
- [ ] No data files or secrets in the commit

**Final deliverable for Day 3:** raw project dataset + complete data dictionary, ready for cleaning.

---

## Preview of Day 4 – Data Cleaning

Tomorrow you will build the reusable preprocessing pipeline (`src/preprocessing/cleaning.py`):
1. Load `retail_demand_raw.parquet` and validate the schema.
2. Remove duplicates and standardise IDs.
3. Validate dates and complete each series to a full daily calendar.
4. Apply the missing-value strategy per column (including dropping pre-launch rows by a documented rule).
5. Detect and handle negative and abnormal sales and outliers (flag, then cap rather than delete).
6. Treat stock-out days and the `Shortfall` audit column consistently.
7. Produce a data-quality report and save `data/processed/clean_sales.parquet`.
8. If you injected faults on Day 3, verify the pipeline against the clean ground-truth copy.
