# Data Dictionary — Retail Demand Forecasting Platform

**Project:** Retail Demand Forecasting & Inventory Optimization Platform  
**Author:** Md Hussain  
**Date:** October 2026  
**Status:** Frozen for MVP (Day 1)

---

## 1. Overview & Granularity

- **Primary Granularity:** Daily observation per unique **Store** $\times$ **Product** combination (`Date` + `Store_ID` + `Product_ID`).
- **Currency:** INR (₹) or standard currency units.
- **Time Zone:** IST (UTC+05:30), single time zone without DST transitions.
- **Primary Data Source:** Inspired by *Corporación Favorita Grocery Sales Forecasting* augmented with calendar holidays and weather telemetry.

---

## 2. Core Modelling Table (`sales_daily`)

One record per calendar date for each active store-product pair.

| Column Name | Data Type | Nullable | Example | Description | Validation & Business Rules |
|---|---|---|---|---|---|
| `Date` | Date (YYYY-MM-DD) | No | `2024-03-15` | Calendar date of observation | Must have zero gaps per store-product time series; strictly monotonic ascending |
| `Store_ID` | String | No | `STORE_001` | Unique retail outlet identifier | Must match foreign key in `dim_stores` |
| `Product_ID` | String | No | `PROD_0042` | Unique item / SKU identifier | Must match foreign key in `dim_products` |
| `Category` | String | No | `GROCERY` | Product merchandise hierarchy | Matches category in `dim_products` |
| `Price` | Float | No | `149.50` | Selling price per unit | Strictly $> 0.0$ |
| `Discount_Pct` | Float | No | `0.10` | Applied discount percentage | Between $0.00$ and $1.00$ |
| `Promotion` | Integer (0/1) | No | `1` | Binary flag for active promotional campaign | Must be `0` or `1`; missing defaults to `0` |
| `Holiday` | Integer (0/1) | No | `0` | Public holiday or festival flag | `1` if official state/national holiday, else `0` |
| `Holiday_Name` | String | Yes | `Diwali` | Name of holiday/event if active | Null if non-holiday |
| `Temperature` | Float | Yes | `28.4` | Mean daily temperature in °C | Range $-10.0$ to $55.0$ °C |
| `Rainfall_mm` | Float | Yes | `0.0` | Daily rainfall precipitation in mm | $\ge 0.0$ |
| `Inventory` | Integer | Yes | `45` | End-of-day closing on-hand stock | $\ge 0$ |
| `Units_Sold` | Integer / Float | No | `18` | **Target Variable**: total daily units demanded | $\ge 0$; integer or fractional unit count |
| `Revenue` | Float | No | `2691.00` | Net daily sales revenue | Calculated as $\text{Units\_Sold} \times \text{Price} \times (1 - \text{Discount\_Pct})$ |

---

## 3. Dimension Tables

### 3.1 Product Dimension (`dim_products`)
| Column Name | Data Type | Description | Rules / Constraints |
|---|---|---|---|
| `Product_ID` | String | Unique product identifier (Primary Key) | Unique, non-null |
| `Product_Name`| String | Human-readable merchandise name | Non-null |
| `Category` | String | Department or product group | Non-null |
| `Subcategory` | String | Finer classification (e.g., Beverages) | Optional |
| `Base_Price` | Float | MSRP / Standard shelf price | $> 0.0$ |
| `Unit_Cost` | Float | Cost of Goods Sold (COGS) per unit | $> 0.0$; must be $\le \text{Base\_Price}$ |
| `Perishable` | Integer (0/1) | Shelf-life constraint indicator | `1` for perishables, `0` for durable |
| `Lead_Time_Days`| Integer | Supplier replenishment cycle duration in days | $\ge 1$, typical default 7 days |

### 3.2 Store Dimension (`dim_stores`)
| Column Name | Data Type | Description | Rules / Constraints |
|---|---|---|---|
| `Store_ID` | String | Unique store identifier (Primary Key) | Unique, non-null |
| `Store_Name` | String | Store title | Non-null |
| `City` | String | Metropolitan city | Non-null |
| `State` | String | State / Regional administration | Non-null |
| `Store_Type` | String | Format (Supermarket, Express, Hypermarket) | Standardized enum |
| `Cluster` | Integer | Clustering label for store groups | Integer |

### 3.3 Calendar Dimension (`dim_calendar`)
| Column Name | Data Type | Description | Rules / Constraints |
|---|---|---|---|
| `Date` | Date | Calendar day | Primary Key |
| `Day_Of_Week` | Integer | Day index (0 = Monday, 6 = Sunday) | 0 to 6 |
| `Is_Weekend` | Integer (0/1) | Weekend flag | 1 if Saturday or Sunday |
| `Month` | Integer | Month of year (1-12) | 1 to 12 |
| `Quarter` | Integer | Calendar quarter (1-4) | 1 to 4 |
| `Year` | Integer | 4-digit calendar year | e.g., 2023, 2024 |
| `Is_Holiday` | Integer (0/1) | Public holiday flag | 0 or 1 |
| `Event_Type` | String | Festival / Sporting / National event | Nullable |

---

## 4. Data Quality Expectations & Validation Rules

1. **Completeness**: No missing `Date`, `Store_ID`, `Product_ID`, or `Units_Sold` records.
2. **Monotonicity**: Time-series per store-product key sorted strictly ascending by `Date`.
3. **No Duplicate Keys**: Composite key `(Date, Store_ID, Product_ID)` must be unique.
4. **Target Bounds**: `Units_Sold >= 0`. Outliers exceeding $5\sigma$ flagged for inspection rather than silent drop.
5. **No Lookahead Leakage**: Future known features (`Promotion`, `Holiday`) may be known at inference; past unknown features (`Temperature`, `Rainfall`, past sales lags) must strictly lag or use seasonal forecasts.
