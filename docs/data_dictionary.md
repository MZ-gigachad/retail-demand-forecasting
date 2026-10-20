# Data Dictionary â€” Retail Demand Forecasting Platform

**Project:** Retail Demand Forecasting & Inventory Optimization Platform
**Author:** Mohammad Mozammil Hussain
**Date:** October 2026
**Status:** Finalised for Raw Dataset Assembly (Day 3 Milestone)

---

## 1. Overview & Granularity

- **Primary Granularity:** Daily observation per unique **Store** $\times$ **Product** combination (`Date` + `Store_ID` + `Product_ID`).
- **Currency:** Indian Rupee (â‚¹), stored with 2 decimal places (paise precision).
- **Time Zone:** IST (UTC+05:30), single national time zone without Daylight Saving Time transitions.
- **Data Heritage & Disclosure:**
  - Base sales, store/item keys, and weekly price movements originate from the Kaggle M5 Forecasting benchmark (Walmart).
  - Store locations are mapped to Tier-1 and Tier-2 Indian metropolitan retail hubs with local climate telemetry from Open-Meteo.
  - Indian national public holidays and lunar festival calendars are joined via `holidays` and custom festival registries.
  - A documented, seeded pre-festival demand uplift is applied to align shopping surges with major Indian festivals.
  - Daily inventory on hand, stockouts, and shortfalls are generated using an order-up-to periodic review $(R, S)$ policy simulation.
  - *Disclosure:* `Promotion` is derived from price drops relative to a rolling regular price. It approximates, but is not identical to, a real promotion calendar.

---

## 2. Core Modelling & Assembled Dataset Schema (`retail_demand_raw.parquet`)

The assembled dataset contains 2,096,280 daily observations across 10 retail stores and 108 stratified SKUs spanning January 29, 2011 to May 22, 2016 (1,941 contiguous calendar days).

### 2.1 Core Target & Mandatory Features

| Column | Type | Description | Source | Derivation / Business Rule | Allowed Values / Range | Nullable |
|---|---|---|---|---|---|---|
| `Date` | datetime64[ns] | Calendar date of observation | M5 Calendar | Mapped from raw day indexes ($d_1$ to $d_{1941}$) | Contiguous daily range (2011-01-29 to 2016-05-22) | No |
| `Store_ID` | string | Standardised retail outlet identifier | Store Master | M5 stores mapped to Indian retail stores (`STORE_001` to `STORE_010`) | In store master | No |
| `Product_ID` | string | Standardised merchandise SKU identifier | Product Master | Sorted M5 items mapped to `PROD_0001` through `PROD_0108` | In product master | No |
| `Category` | string | Product merchandise super-category | Category Mapping | M5 `cat_id` mapped to Indian retail hierarchy | `Grocery & Food`, `Home & Household`, `Toys & Hobbies` | No |
| `Price` | float64 | Daily selling shelf price in â‚¹ | M5 Sell Prices | M5 weekly USD price $\times$ item `Price_Factor`, rounded to 2 dp | $> 0.0$ | Yes (before product launch) |
| `Promotion` | int8 | Binary promotional discount flag | Derived | $1$ if `Discount_Pct` $\ge 0.05$ (5% below rolling 13-week regular price), else $0$ | $0, 1$ | No |
| `Holiday` | int8 | National public holiday or major festival flag | `holidays` + Custom Table | National gazetted holidays + lunar festival days | $0, 1$ | No |
| `Temperature` | float64 | Daily mean temperature in store's city (Â°C) | Open-Meteo API | Historical archive 2m mean temperature | $5.0$ to $48.0$ Â°C | No |
| `Inventory` | float64 | End-of-day closing stock on hand | Simulated | Periodic review $(R=7, S)$ order-up-to policy simulation | $\ge 0.0$ | Yes (before product launch) |
| `Units_Sold` | int16 | **Primary Target:** Net units demanded/sold that day | M5 Benchmark + Uplift | Benchmark units with documented festival uplift applied | $\ge 0$ (non-negative integer) | No |
| `Revenue` | float64 | Net projected daily sales revenue in â‚¹ | Derived | Calculated as $\text{Units\_Sold} \times \text{Price}$ | $\ge 0.0$ | Yes (before product launch) |

### 2.2 Supporting Analytical & Audit Columns

| Column | Type | Description | Used For | Derivation / Logic | Allowed Values | Nullable |
|---|---|---|---|---|---|---|
| `Department` | string | Detailed product department | EDA & Dashboard drill-down | Mapped from M5 `dept_id` (7 merchandise departments) | Standard department enum | No |
| `City` | string | Host metropolitan city | Geospatial analytics & Weather join | Extracted from store master | Bangalore, Mumbai, Delhi, Hyderabad, Chennai, Pune, Kolkata, Ahmedabad, Jaipur | No |
| `Discount_Pct` | float64 | Percentage discount vs regular price | Price elasticity & Promotion feature | $\max(0, 1 - \text{Price} / \text{Regular\_Price})$ | $0.00$ to $1.00$ | No |
| `Regular_Price` | float64 | Rolling regular/reference shelf price in â‚¹ | Baseline price tracking | Rolling 13-week prior median price, falling back to current price | $> 0.0$ | Yes (before product launch) |
| `Rainfall_mm` | float64 | Total daily precipitation in mm | Weather telemetry feature | Open-Meteo historical daily precipitation | $\ge 0.0$ | No |
| `Holiday_Name` | string | Name of the holiday or festival | Holiday impact analysis | Matched national/festival calendar | Specific holiday title | Yes (non-holidays) |
| `Festival_Window` | int8 | Pre-festival shopping surge indicator | Seasonality & Uplift feature | $1$ if within 7 days prior to or on a major Indian festival | $0, 1$ | No |
| `Stockout_Flag` | float64 | Indicator of zero stock at close | Inventory optimization & Service level | $1.0$ if `Inventory == 0`, else $0.0$ | $0.0, 1.0$ | Yes (before product launch) |
| `Shortfall` | float64 | Demand quantity exceeding available stock | Emergency transfer audit | $\max(0, \text{Units\_Sold} - \text{Available\_Stock})$ | $\ge 0.0$ | Yes (before product launch) |
| `Units_Sold_Original` | int16 | Baseline sales before festival uplift | Audit trail & reproducibility | Raw M5 observed unit sales count | $\ge 0$ | No |

---

## 3. Supporting Dimension Tables

### 3.1 Product Dimension (`data/external/product_master.parquet`)

Contains merchandise hierarchy, price scaling, and supply chain replenishment parameters for all 108 SKUs.

| Column Name | Data Type | Description | Constraints & Business Rules |
|---|---|---|---|
| `Product_ID` | string | Unique primary key (`PROD_0001` to `PROD_0108`) | Non-null, unique |
| `Source_Item_ID` | string | Original M5 item identifier (e.g., `FOODS_1_024`) | Traceability anchor |
| `Product_Name` | string | Standardized merchandise label (e.g., `Fresh & Dairy Item 012`) | Generic, non-branded |
| `Category` | string | Super-category (`Grocery & Food`, `Home & Household`, `Toys & Hobbies`) | 3 discrete categories |
| `Department` | string | Sub-department (e.g., `Snacks & Beverages`, `Cleaning & Utilities`) | 7 discrete departments |
| `Price_Factor` | float64 | Item-specific multiplier to convert benchmark USD to â‚¹ | Category scale $\times (1 \pm \text{jitter})$ |
| `Base_Price` | float64 | Typical median selling price in â‚¹ | Median of historical INR prices |
| `Unit_Cost` | float64 | Cost of Goods Sold (COGS) to retailer in â‚¹ | Drawn within category margin brackets ($< \text{Base\_Price}$) |
| `Lead_Time_Days` | int64 | Supplier replenishment lead time $L$ in days | Discrete integer between $2$ and $7$ days |
| `Min_Order_Qty` | int64 | Minimum Order Quantity / replenishment batch multiple | Selected from $\{6, 12, 24\}$ |
| `Shelf_Life_Days`| float64 | Perishability limit in days | Perishables only ($3$â€“$14$ days for Fresh & Dairy), NaN otherwise |

### 3.2 Store Dimension (`data/external/store_master.parquet`)

Maps the 10 retail outlets across Indian commercial centers.

| Column Name | Data Type | Description | Constraints & Values |
|---|---|---|---|
| `Store_ID` | string | Unique primary key (`STORE_001` to `STORE_010`) | Non-null, unique |
| `Source_Store_ID` | string | Original M5 store identifier (`CA_1` to `WI_3`) | Traceability anchor |
| `Store_Name` | string | Human-readable store branch name | e.g., `Bangalore-01`, `Mumbai-01` |
| `City` | string | Host metropolitan city | 9 unique cities |
| `State` | string | State or union territory | Karnataka, Maharashtra, Delhi, Telangana, Tamil Nadu, West Bengal, Gujarat, Rajasthan |
| `Region` | string | Geographic quadrant | South, West, North, East |
| `Latitude` | float64 | Geographic latitude coordinate | e.g., $12.9716$ |
| `Longitude` | float64 | Geographic longitude coordinate | e.g., $77.5946$ |
| `Store_Type` | string | Operational retail format | `Hypermarket`, `Supermarket`, `Express` (derived from sales volume) |
| `Size_Sqft` | int64 | Gross store floor area in square feet | Hypermarket: 40kâ€“70k, Supermarket: 10kâ€“25k, Express: 2kâ€“6k |
| `Opening_Date` | datetime64[ns] | Store inaugural operating date | Fixed at `2010-01-01` (fully active prior to historical window) |

### 3.3 Indian Holiday & Festival Calendar (`data/external/holidays_india.parquet`)

Daily calendar covering national public holidays and major Hindu, Islamic, and Christian festivals.

| Column Name | Data Type | Description | Range & Rules |
|---|---|---|---|
| `Date` | datetime64[ns] | Calendar date | Contiguous daily range |
| `Holiday` | int8 | Binary indicator of gazetted public holiday | $0$ or $1$ |
| `Holiday_Name` | string | Title of holiday/festival | Null for standard business days |
| `Festival_Window` | int8 | Flag for 7-day shopping ramp-up period | $1$ during shopping surge, else $0$ |
| `Festival_Name` | string | Primary festival name for window | Non-null if `Festival_Window == 1` |

---

## 4. End-to-End Data Lineage

```text
[ Kaggle M5 Benchmark: sales_train_evaluation.csv ]
   â”‚
   â”œâ”€â”€ Filter 108 Stratified SKUs x 10 Stores
   â””â”€â”€ Reshape Wide to Long â”€â”€â–º [ data/interim/m5_subset_long.parquet ]
                                   â”‚
                                   â”œâ”€â”€ Join Product Master (Price_Factor) â”€â”€â–º Convert Prices to â‚¹
                                   â”œâ”€â”€ Complete Product Master (Base_Price, Unit_Cost)
                                   â”œâ”€â”€ Derive Regular Price & Promotion Flags (Rolling 13-week median)
                                   â”‚
                                   â”œâ”€â”€ Join Store Master (City, Lat, Lon, Store_Type)
                                   â”œâ”€â”€ Join Holiday Calendar (Gazetted Holidays & Festival Windows)
                                   â”œâ”€â”€ Join Open-Meteo Weather (Temperature, Rainfall_mm by City)
                                   â”‚
                                   â”œâ”€â”€ Apply Festival Demand Uplift (stochastic integer rounding)
                                   â”œâ”€â”€ Simulate Inventory Dynamics (Periodic review R=7, S policy)
                                   â””â”€â”€ Compute Net Revenue (Units_Sold x Price)
                                           â”‚
                                           â–¼
                       [ data/raw/retail_demand_raw.parquet ]
```

---

## 5. Data Quality Expectations & Validation Gates

1. **Completeness**: Zero nulls across all core primary keys (`Date`, `Store_ID`, `Product_ID`) and the target variable (`Units_Sold`).
2. **Structural Nulls**: `Price`, `Regular_Price`, `Inventory`, and `Revenue` contain nulls strictly for observations occurring before an item's commercial launch date.
3. **Monotonicity**: Sorted strictly ascending by `Store_ID`, `Product_ID`, and `Date`.
4. **Target Bounds**: `Units_Sold >= 0` with no negative returns.
5. **No Lookahead Leakage**:
   - `Regular_Price` is computed using only historical weeks ($t-1$ and earlier).
   - Inventory ordering decisions use strictly lagged demand expectations.
   - External weather and calendar attributes match empirical historical observations for the stated dates.
