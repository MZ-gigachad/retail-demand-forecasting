# Data Sources & Strategy â€” Retail Demand Forecasting Platform

**Project:** Retail Demand Forecasting & Inventory Optimization Platform
**Phase:** Week 1 â€” Data Engineering & Foundation (Day 2)
**Author:** Md Hussain
**Date:** October 2026
**Status:** Data collection and profiling completed; domain extensions planned for Day 3

---

## 1. Target Schema & Data Requirements Checklist (Task 1)

The target daily schema is defined in `docs/data_dictionary.md`. Its intended granularity is one record for each Date Ã— Store_ID Ã— Product_ID combination.

```text
Date, Store_ID, Product_ID, Category, Price, Promotion, Holiday,
Temperature, Inventory, Units_Sold, Revenue
```

### Requirements Matrix

| Requirement | Why It Matters | Minimum Acceptable | Project Target | Status |
|---|---|---|---|---|
| Daily Sales per Store-Product | Main target for forecasting (`Units_Sold`) | Daily observations | Daily sales across multiple years | Met by M5 benchmark |
| History Length | Captures seasonality, holidays and demand patterns | At least 730 days | Approximately 3â€“5 years where available | Met: 1,941 sales days |
| Store Diversity | Supports store-level demand analysis | At least 5 stores | 10 stores mapped to Indian retail locations | Met: 10 stores |
| Product & Category Coverage | Supports product and category comparisons | At least 3 categories and 50 products | 100â€“200 selected items | Met: 108 selected items |
| Price History | Supports price and revenue analysis | Price records over time | Weekly prices by store and item | Available in `sell_prices.csv` |
| Promotions & Discounts | Helps study price-related demand changes | Promotion indicator | Derived promotion and discount features | Planned for Day 3 |
| Holidays & Events | Helps explain seasonal demand changes | Calendar features | Indian holidays and festivals | Planned for Day 3 |
| Weather Telemetry | May help explain weather-sensitive demand | Optional external feature | Temperature and rainfall | Planned for Day 3 |
| Inventory On-Hand | Supports replenishment and stockout analysis | Inventory records | Simulated inventory history | Planned for Day 3 |

---

## 2. Evaluation of Data Source Options (Task 2)

### 2.1 Candidate Comparison

**Option A: M5 Forecasting Accuracy â€” Kaggle**

- **Strengths:** Real daily unit sales, 3,049 items, 10 stores, 1,941 sales days, intermittent demand and weekly prices.
- **Limitations:** US retail context, USD prices, wide-format sales data and no direct inventory or weather records.

**Option B: CorporaciÃ³n Favorita Grocery Sales â€” Kaggle**

- **Strengths:** Includes promotion flags, store information, transactions and oil-price data.
- **Limitations:** Different product granularity and no equivalent individual shelf-price history for the intended workflow.

**Option C: Fully Synthetic Dataset**

- **Strengths:** Allows complete control over Indian holidays, INR prices, weather, promotions and inventory.
- **Limitations:** Does not reproduce all real-world customer purchasing behaviour and data irregularities.

**Option D: Selected Hybrid Strategy**

The project uses the original M5 dataset as the sales benchmark and adds domain-specific features in later stages.

The strategy is to:

1. Use real M5 sales and price records as the baseline.
2. Convert sales from wide format into daily long-format records.
3. Select a reproducible sample of 108 items across three categories and three demand levels.
4. Extend the dataset with Indian store mappings, INR-scaled prices, Indian holidays, derived promotion indicators, weather and simulated inventory.
5. Retain synthetic data generation as a development and testing fallback where appropriate.

The Indian store mappings and future domain features are project adaptations. They do not mean that the original M5 records were collected from Indian stores.

### 2.2 Decision Scoring Matrix

Scores range from 1 to 5. These are project-level assessments, not externally measured benchmark results.

| Criterion (Weight) | Option A (M5) | Option B (Favorita) | Option C (Synthetic) | Option D (Hybrid M5) |
|---|---:|---:|---:|---:|
| Demand Realism & Intermittency (25%) | 5 | 5 | 2.5 | 4.8 |
| Schema Completeness (20%) | 2.5 | 3.5 | 5 | 4.5 |
| SKU Granularity (15%) | 5 | 2.5 | 5 | 5.0 |
| Indian Retail Relevance (15%) | 1 | 1 | 5 | 4.2 |
| Portfolio & Client Credibility (15%) | 5 | 5 | 3 | 4.7 |
| Pipeline Performance & Size (10%) | 2.5 | 3.5 | 5 | 4.0 |
| **Weighted Total** | **3.60** | **3.50** | **3.95** | **4.57** |

The hybrid approach is selected because it combines real sales behaviour with the flexibility to add project-specific features.

---

## 3. Raw Data Profile & Inspection Summary (Task 5)

The profile below was generated from the original M5 Forecasting Accuracy dataset in `data/raw/m5_original/` using `scripts/build_interim_data.py`.

### 3.1 Dataset Profile

| Metric | Observed Value | Significance |
|---|---|---|
| Sales date range | 2011-01-29 to 2016-05-22 | Covers multiple seasonal cycles |
| Number of sales days | 1,941 | Daily sales history |
| Calendar date range | 2011-01-29 to 2016-06-19 | Calendar includes dates beyond the sales history |
| Number of calendar days | 1,969 | Includes additional calendar dates |
| Stores | 10 | CA, TX and WI store groups |
| Total raw items | 3,049 | Unique item identifiers |
| Selected items | 108 | Reproducible stratified sample |
| Categories | 3 | FOODS, HOBBIES and HOUSEHOLD |
| Departments | 7 | Supports department-level comparisons |
| Full sales series | 30,490 | Store-item combinations |
| Subset sales series | 1,080 | 108 items across 10 stores |
| Full reshaped row estimate | 59,181,090 | 30,490 series Ã— 1,941 sales days |
| Interim subset rows | 2,096,280 | 1,080 series Ã— 1,941 sales days |
| Total raw sales units | 66,927,173 | Sum across the raw sales history |
| Subset sales units | 1,937,034 | Sum across the selected series |
| Zero-sales cells | 68.0% | Indicates intermittent demand |
| Missing subset prices | 20.34% | Includes periods before price records begin |
| Price range (USD) | $0.01â€“$107.32 | Observed weekly price range |
| Mean price (USD) | $4.41 | Mean across weekly price records |
| Calendar event records | 162 | Event records in the source calendar |

**Important:** The calendar contains 1,969 dates, but the sales data contains 1,941 daily columns. The additional 28 calendar dates do not have corresponding sales columns in this dataset. Row-count validation must therefore use 1,941 sales days.

### 3.2 Key Inspection Insights

- **Intermittent demand:** Approximately 68% of the raw daily sales cells contain zero units. Forecast evaluation should account for zero-demand periods.
- **Stratified sampling:** The selected 108 items represent three categories and low-, medium- and high-demand groups.
- **Multiple stores:** The selected items produce 1,080 store-item time series across 10 stores.
- **Price coverage:** Approximately 20.34% of the subset rows have no matching weekly price. The pipeline identifies these records rather than silently treating the prices as known.
- **Data validation:** The pipeline passed row-count, units-preservation and duplicate-key checks.
- **Interim output:** The generated Parquet file contains 2,096,280 rows and is saved as `data/interim/m5_subset_long.parquet`.

Missing prices must be investigated before forecasting or revenue calculations. Records without prices should not automatically be treated as having a zero price.

---

## 4. Source to Project Schema Mapping (Task 8)

| Project Target Column | M5 Source Origin | Field Type | Processing / Adaptation |
|---|---|---|---|
| `Date` | `calendar.csv` (`date`) | DATE | Map sales day identifiers to calendar dates |
| `Store_ID` | `store_id` | STRING | Map source store codes to project store identifiers |
| `Product_ID` | `item_id` | STRING | Standardize item identifiers if required |
| `Category` | `cat_id` / `dept_id` | STRING | Use source categories and map them to project categories |
| `Price` | `sell_prices.csv` (`sell_price`) | FLOAT | Join weekly prices to daily sales; apply INR scaling in Day 3 |
| `Promotion` | Derived | INT (0/1) | Derive a promotion indicator from price changes |
| `Discount_Pct` | Derived | FLOAT | Estimate discount depth from an appropriate reference price |
| `Holiday` | Source calendar / Indian calendar | INT (0/1) | Add Indian holidays and festival windows in Day 3 |
| `Holiday_Name` | Derived | STRING | Add the relevant holiday or festival name |
| `Temperature` | External data | FLOAT | Retrieve historical weather for the mapped project cities |
| `Rainfall_mm` | External data | FLOAT | Retrieve historical precipitation for the mapped project cities |
| `Inventory` | Simulated | INT | Simulate stock levels and replenishment in a later project stage |
| `Units_Sold` | `sales_train_evaluation.csv` | INT | Reshape daily sales columns into records |
| `Revenue` | Derived | FLOAT | Calculate only when the required price and discount data are available |

### 4.1 Store Mapping Reference

The following table defines proposed project mappings. These are illustrative project locations, not the actual locations of the source M5 stores.

| M5 Store Code | Project Store ID | City / Area | Region / Tier |
|---|---|---|---|
| `CA_1` | `STORE_BLR_01` | Bengaluru (Indiranagar) | South / Tier-1 |
| `CA_2` | `STORE_BLR_02` | Bengaluru (Whitefield) | South / Tier-1 |
| `CA_3` | `STORE_BOM_01` | Mumbai (Andheri) | West / Tier-1 |
| `CA_4` | `STORE_DEL_01` | New Delhi (Connaught Place) | North / Tier-1 |
| `TX_1` | `STORE_HYD_01` | Hyderabad (Hitec City) | South / Tier-1 |
| `TX_2` | `STORE_MAA_01` | Chennai (T. Nagar) | South / Tier-1 |
| `TX_3` | `STORE_PNQ_01` | Pune (Kothrud) | West / Tier-2 |
| `WI_1` | `STORE_CCU_01` | Kolkata (Salt Lake) | East / Tier-1 |
| `WI_2` | `STORE_AMD_01` | Ahmedabad (SG Highway) | West / Tier-2 |
| `WI_3` | `STORE_JAI_01` | Jaipur (Malviya Nagar) | North / Tier-2 |

---

## 5. Key Assumptions & Known Limitations (Task 9)

### 5.1 Assumptions

1. **Constant weekly price:** M5 prices are recorded by store, item and retail week. A weekly price can be joined to the daily sales records for the corresponding week.
2. **Pre-launch periods:** A missing price may indicate that an item was not yet available, but this must be validated rather than assumed for every missing record.
3. **Promotion proxy:** A material price reduction may be used as a proxy for a promotion. The threshold and reference price will be defined and tested in Day 3.
4. **Inventory simulation:** Inventory levels will be simulated using explicit assumptions about demand, lead time and replenishment policy.
5. **Indian context:** The store mappings, Indian holiday calendar and weather features are project extensions and do not change the original source data's US retail origin.

### 5.2 Known Limitations

1. **Source geography:** The original demand data comes from US retail. Indian store mappings do not turn it into observed Indian retail data.
2. **No original inventory history:** The M5 dataset does not provide the inventory-on-hand history required by the proposed inventory optimization system.
3. **No explicit promotion flag:** Promotions must be estimated from available information; price changes alone do not prove that a promotion occurred.
4. **Missing prices:** Some daily records have no matching weekly price. Revenue and price-dependent features need appropriate missing-data handling.
5. **Intermittent demand:** Many daily observations contain zero sales. Metrics such as standard MAPE can be misleading when actual demand is zero or very low.
6. **External feature dependencies:** Weather data and Indian holiday features must be added and validated before they can be used in modelling.

---

## 6. Reproducibility & Data Governance

- **Source data:** The original dataset is stored locally under `data/raw/m5_original/`.
- **Manifest:** Record file sizes and SHA-256 hashes in `data/raw/m5_original/MANIFEST.md` and verify them after generating the manifest.
- **Git hygiene:** Keep raw datasets, interim datasets and processed data out of Git. Commit source code, documentation and tests instead.
- **Sampling seed:** Use `SEED = 42` for reproducible item sampling.
- **Interim outputs:** The pipeline creates `data/interim/selected_items.csv` and `data/interim/m5_subset_long.parquet`.
- **Rebuild command:**

```powershell
.\.venv\Scripts\python.exe scripts\build_interim_data.py
```

- **Test command:**

```powershell
.\.venv\Scripts\python.exe -m pytest
```

- **Data integrity:** Validate row counts, total units, unique Dateâ€“Storeâ€“Item keys and price missingness after rebuilding the dataset.
- **Dataset usage:** Follow the Kaggle competition's applicable terms and rules. Do not commit or redistribute the raw dataset through the project repository.

