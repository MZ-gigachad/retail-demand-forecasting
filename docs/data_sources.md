# Data Sources & Strategy â€” Retail Demand Forecasting Platform

**Project:** Retail Demand Forecasting & Inventory Optimization Platform
**Phase:** Week 1 â€” Data Engineering & Foundation (Day 3 Complete)
**Author:** Md Hussain
**Date:** October 2026
**Status:** Raw dataset assembly, domain adaptations, and inventory simulations completed

---

## 1. What is Real, Derived, and Simulated (Mandatory Transparency Disclosure)

To maintain absolute credibility and engineering honesty, the table below documents the exact origin, mathematical derivation, or simulation basis for every column in the platform.

| Column Group | Feature / Column Names | Engineering Status | Methodology & Source |
|---|---|---|---|
| **Demand Baseline** | `Units_Sold_Original`, `Date`, item key roots | **Real (Benchmark)** | Authentic store-SKU time series from Kaggle M5 Forecasting (Walmart, 2011â€“2016). Captures empirical retail intermittency (68% zeros) and day-of-week seasonality. |
| **Merchandise Hierarchy** | `Product_ID`, `Store_ID`, `Store_Name`, `Category`, `Department` | **Re-labelled** | M5 US stores and IDs mapped deterministically to 10 Indian retail stores (`STORE_001`â€“`STORE_010`) and Indian department hierarchies (`Grocery & Food`, etc.). |
| **Shelf Pricing** | `Price` (â‚¹), `Base_Price`, `Unit_Cost` | **Scaled from Benchmark** | Original USD sell prices scaled to â‚¹ using category-specific multipliers (`FOODS: 30`, `HOUSEHOLD: 35`, `HOBBIES: 40`) with Â±10% seeded item jitter. COGS derived via category margins. |
| **Promotions & Discounts** | `Promotion`, `Discount_Pct`, `Regular_Price` | **Derived from Prices** | Rolling 13-week prior median price represents `Regular_Price`. `Promotion = 1` when `Discount_Pct >= 5%`. *Disclosure: Approximates a real promo calendar without lookahead leakage.* |
| **Holidays & Calendars** | `Holiday`, `Holiday_Name`, `Festival_Window` | **Real Indian Calendar** | Python `holidays.India` combined with custom lunar calendar table (`data/external/holidays_india.csv`) covering Diwali, Holi, Eid, Dussehra, Pongal, etc. |
| **Festival Demand Uplift** | `Units_Sold` (Final target) | **Documented Simulation** | Transparent, switchable demand uplift applied strictly during 7-day pre-festival windows (`+25%` Grocery, `+20%` Home, `+15%` Toys) using stochastic integer rounding. |
| **Environmental Telemetry** | `Temperature`, `Rainfall_mm` | **Real Historical Telemetry** | Historical daily 2m temperature and precipitation from Open-Meteo Archive API for each of the 9 Indian store cities (2011â€“2016), with disk caching and seasonal fallback. |
| **Inventory Dynamics** | `Inventory`, `Stockout_Flag`, `Shortfall` | **Simulated Supply Chain** | Simulated using a periodic review $(R=7, S)$ order-up-to inventory policy with rolling demand estimation, item lead times ($L \in [2, 7]$), and batch MOQs. |

---

## 2. Final Dataset Sizes & Profiles (`data/raw/retail_demand_raw.parquet`)

The assembled raw dataset merges the interim benchmark data with all domain features:

| Dimension / Metric | Target Specification | Observed Final Assembled Dataset |
|---|---|---|
| **Calendar Range** | 2011-01-29 to 2016-05-22 | 1,941 contiguous daily observations |
| **Retail Stores** | 10 stores across India | 10 stores (`STORE_001` to `STORE_010`) in 9 cities |
| **Sampled Products** | 108 stratified SKUs | 108 products (`PROD_0001` to `PROD_0108`) across 3 categories |
| **Time Series Count** | 1,080 distinct series | Exactly 1,080 Store $\times$ Product pairs |
| **Total Rows** | $1,080 \times 1,941 = 2,096,280$ | **2,096,280 rows** (zero missing days, zero duplicates) |
| **Total Columns** | 11 Core + 10 Supporting | **21 columns** |
| **Total Units Sold** | ~2.0M units | **2,042,408 units** (Original: 1,937,034; Uplift: +5.44%) |
| **Total Projected Revenue** | Scaled in â‚¹ | **â‚¹340,320,443.51** |
| **Promotion Flag Rate** | 1% to 20% | **1.04%** of store-item-weeks |
| **Stockout Rate (Closing = 0)** | 1% to 8% | **1.32%** of active inventory days |
| **Shortfall Rate** | < 2% | **0.72%** of active inventory days |
| **Average Days of Cover** | 7 to 25 days | **20.5 days** |

---

## 3. Adaptation Configuration Parameters (`config.yaml`)

All parameters governing the adaptation, scaling, and simulation logic are centralized in `config.yaml`:

```yaml
adaptation:
  seed: 42
  price_scale:
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

---

## 4. Geographic & Store Master Mapping

| Source Store | Project Store ID | Store Name | City | State | Region | Lat / Lon | Store Type | Size (sq ft) |
|---|---|---|---|---|---|---|---|---|
| `CA_1` | `STORE_001` | Bangalore-01 | Bangalore | Karnataka | South | 12.9716, 77.5946 | Hypermarket | 63,218 |
| `CA_2` | `STORE_002` | Bangalore-02 | Bangalore | Karnataka | South | 12.9716, 77.5946 | Supermarket | 16,583 |
| `CA_3` | `STORE_003` | Mumbai-01 | Mumbai | Maharashtra | West | 19.0760, 72.8777 | Hypermarket | 57,011 |
| `CA_4` | `STORE_004` | Delhi-01 | Delhi | Delhi | North | 28.6139, 77.2090 | Express | 2,130 |
| `TX_1` | `STORE_005` | Hyderabad-01 | Hyderabad | Telangana | South | 17.3850, 78.4867 | Express | 5,663 |
| `TX_2` | `STORE_006` | Chennai-01 | Chennai | Tamil Nadu | South | 13.0827, 80.2707 | Supermarket | 11,438 |
| `TX_3` | `STORE_007` | Pune-01 | Pune | Maharashtra | West | 18.5204, 73.8567 | Express | 2,059 |
| `WI_1` | `STORE_008` | Kolkata-01 | Kolkata | West Bengal | East | 22.5726, 88.3639 | Supermarket | 24,196 |
| `WI_2` | `STORE_009` | Ahmedabad-01 | Ahmedabad | Gujarat | West | 23.0225, 72.5714 | Hypermarket | 44,792 |
| `WI_3` | `STORE_010` | Jaipur-01 | Jaipur | Rajasthan | North | 26.9124, 75.7873 | Express | 4,496 |

---

## 5. Pipeline Commands & Verification

To reproduce and verify the Day 3 data pipeline:

1. **Run full end-to-end dataset assembly:**
   ```bash
   python -m src.data.assemble
   ```
2. **Execute data validation and generate markdown profile report:**
   ```bash
   python -m src.data.validate_raw
   ```
3. **Execute unit and integrity test suite:**
   ```bash
   pytest
   ```
