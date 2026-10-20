# Assembled Raw Dataset Profile Report

**Generated:** 2026-10-20 20:51:48
**Source File:** `raw\retail_demand_raw.parquet`
**Status:** VALIDATED (All integrity assertions passed)

---

## 1. High-Level Summary

| Metric | Value |
|---|---|
| **Total Observations** | 2,096,280 |
| **Total Columns** | 21 |
| **Date Range** | 2011-01-29 to 2016-05-22 (1,941 days) |
| **Stores** | 10 Indian Retail Outlets |
| **Products** | 108 Stratified SKUs |
| **Categories** | 3 |
| **Total Units Sold** | 2,015,648 (Original: 1,937,034, Uplift: +4.06%) |
| **Total Projected Revenue** | â‚¹251,501,846.80 |

---

## 2. Operational & Behavioral Diagnostics

| Diagnostic | Observed Rate | Target / Healthy Benchmark | Status |
|---|---|---|---|
| **Promotion Flag Rate** | 1.04% | 1.0% â€“ 20.0% | Normal |
| **National Holiday Rate** | 6.23% | 2.0% â€“ 10.0% | Normal |
| **Festival Window Rate** | 19.11% | 10.0% â€“ 25.0% | Normal |
| **Stockout Rate (Zero Inventory)** | 1.32% | 1.0% â€“ 8.0% | Healthy |
| **Shortfall Incident Rate** | 0.72% | < 2.0% | Healthy |
| **Average Days of Cover (DoC)** | 21.3 days | 7 â€“ 25 days | Optimal |

---

## 3. Selling Price Distribution by Category (INR â‚¹)

| Category | Item-Days | Min (â‚¹) | Median (â‚¹) | Mean (â‚¹) | Max (â‚¹) |
|---|---|---|---|---|---|
| **Grocery & Food** | 553,370 | â‚¹0.27 | â‚¹72.39 | â‚¹91.03 | â‚¹228.24 |
| **Home & Household** | 584,779 | â‚¹8.70 | â‚¹189.51 | â‚¹204.87 | â‚¹579.72 |
| **Toys & Hobbies** | 531,726 | â‚¹1.92 | â‚¹189.64 | â‚¹256.79 | â‚¹1321.65 |

---

## 4. Completeness & Schema Audit

| Column | Non-Null Count | Null Count | Null % | Dtype | Rule / Assessment |
|---|---|---|---|---|---|
| `Date` | 2,096,280 | 0 | 0.0% | `datetime64[ns]` | Complete |
| `Store_ID` | 2,096,280 | 0 | 0.0% | `object` | Complete |
| `Product_ID` | 2,096,280 | 0 | 0.0% | `object` | Complete |
| `Category` | 2,096,280 | 0 | 0.0% | `object` | Complete |
| `Price` | 1,669,875 | 426,405 | 20.34% | `float64` | Pre-launch dates expected |
| `Promotion` | 2,096,280 | 0 | 0.0% | `int8` | Complete |
| `Holiday` | 2,096,280 | 0 | 0.0% | `int8` | Complete |
| `Temperature` | 2,096,280 | 0 | 0.0% | `float64` | Complete |
| `Inventory` | 1,669,875 | 426,405 | 20.34% | `float64` | Pre-launch dates expected |
| `Units_Sold` | 2,096,280 | 0 | 0.0% | `int16` | Complete |
| `Revenue` | 1,669,875 | 426,405 | 20.34% | `float64` | Pre-launch dates expected |
| `Department` | 2,096,280 | 0 | 0.0% | `object` | Complete |
| `City` | 2,096,280 | 0 | 0.0% | `object` | Complete |
| `Discount_Pct` | 2,096,280 | 0 | 0.0% | `float64` | Complete |
| `Regular_Price` | 1,669,875 | 426,405 | 20.34% | `float64` | Pre-launch dates expected |
| `Rainfall_mm` | 2,096,280 | 0 | 0.0% | `float64` | Complete |
| `Holiday_Name` | 130,680 | 1,965,600 | 93.77% | `object` | Pre-launch dates expected |
| `Festival_Window` | 2,096,280 | 0 | 0.0% | `int8` | Complete |
| `Stockout_Flag` | 1,669,875 | 426,405 | 20.34% | `float64` | Pre-launch dates expected |
| `Shortfall` | 1,669,875 | 426,405 | 20.34% | `float64` | Pre-launch dates expected |
| `Units_Sold_Original` | 2,096,280 | 0 | 0.0% | `int16` | Complete |
