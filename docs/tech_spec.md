# Technical Specification — Retail Demand Forecasting & Inventory Optimization Platform

**Author:** Md Hussain  
**Date:** October 2026  
**Version:** 1.0 (Day 1 Milestone)  
**Status:** Approved for Implementation

---

## 1. Overview
### 1.1 Problem Statement
Retailers face significant challenges in accurately balancing stock levels. Under-forecasting results in lost sales, stockouts, and dissatisfied customers, while over-forecasting leads to high carrying costs, working capital lock-in, and inventory depreciation or spoilage. Traditional heuristic approaches (e.g., simple moving averages or static safety stocks) fail to capture seasonal cycles, price elasticity, promotional spikes, and holiday effects.

### 1.2 Project Goal & Value Proposition
This platform delivers an end-to-end machine learning system that transforms raw historical sales, calendar data, promotions, and external environmental factors into accurate multi-horizon demand forecasts, actionable inventory reorder policies, and executive dashboards.

### 1.3 Target Audience
- **Retail Merchandisers & Planners:** Multi-horizon demand forecasts for replenishment planning.
- **Supply Chain & Inventory Managers:** Automated calculation of Reorder Points (ROP) and safety stock buffers.
- **Executive & Portfolio Audience:** Demonstration of production-grade ML engineering, clean architecture, reproducible pipelines, and interactive deployment.

---

## 2. Scope

### 2.1 In Scope (Must Have)
- **Data Engineering Pipeline:** Ingestion, cleaning, calendar alignment, feature store, and zero-leakage splitters.
- **Forecasting Models:**
  1. *Seasonal Naive Baseline* (Same day last week / last period).
  2. *Facebook Prophet* (Additive decomposition baseline).
  3. *Deep Learning (LSTM)* (Sequential temporal dynamics).
  4. *Gradient Boosted Decision Trees (CatBoost)* (Feature-rich tabular regression champion).
- **Evaluation Framework:** Multi-metric benchmarking (MAE, RMSE, MAPE, WMAPE, Bias) with temporal cross-validation.
- **Inventory Optimization Module:** Automated Safety Stock, Reorder Point, and stockout simulation.
- **Interactive UI & Dashboard:** Streamlit application featuring scenario planning and SKU exploration.
- **FastAPI Endpoint:** RESTful inference endpoint for real-time predictions.
- **Containerization & Deployment:** Dockerized configuration ready for cloud hosting.

### 2.2 Should Have (Secondary / Week 3–4)
- Automated hyperparameter tuning (Optuna).
- SHAP model explainability in the dashboard.
- Revenue simulation under varying discount campaigns.

### 2.3 Out of Scope / Future Roadmap
- Distributed streaming ingestion (Apache Kafka / Flink).
- Multi-cloud enterprise orchestration (Airflow DAGs in production).
- Continuous online automated retraining.

---

## 3. Data Architecture

### 3.1 Data Sources & Licensing
- Primary dataset based on *Corporación Favorita Grocery Sales Forecasting* (open benchmark dataset) covering multi-store, multi-product daily sales.
- External calendar and public holiday information via Python `holidays`.
- Historical temperature telemetry via Open-Meteo API.

### 3.2 Granularity & Time Horizons
- **Granularity:** Daily aggregated demand per Store-Product pair (`Date` $\times$ `Store_ID` $\times$ `Product_ID`).
- **History Length:** 2 to 3 years of continuous daily history.
- **Target Variable:** `Units_Sold` (integer or continuous quantity sold).

---

## 4. Forecasting Definition & Feature Strategy

### 4.1 Forecasting Configuration
- **Prediction Target:** `Units_Sold`.
- **Forecast Horizons:** 7-day, 14-day, and 30-day forward horizons.
- **Multi-step Strategy:** Direct forecasting strategy for tabular models (separate specialized models or horizon-indexed features) to eliminate error compounding inherent in recursive rollouts.
- **Data Split:** Strict time-based train/validation/test split:
  - *Train Set:* Historical period prior to validation window.
  - *Validation Set:* 30 days immediately preceding the test window.
  - *Test Set:* Final held-out 60 days (zero lookahead leakage).

### 4.2 Feature Engineering Groups
1. **Calendar Features:** Day of week, day of month, week of year, month, quarter, weekend indicator.
2. **Holiday & Festival Flags:** Pre-holiday ramp up flags, holiday day-of, post-holiday indicators.
3. **Price & Promotions:** Discount percentage, promotional campaign flags, relative price vs category median.
4. **Lag Features:** Lagged demand at $t-1, t-7, t-14, t-28, t-365$.
5. **Rolling Aggregations:** 7-day, 14-day, and 28-day rolling mean, standard deviation, min, and max.
6. **External Features:** Mean daily temperature and rainfall.

---

## 5. Model Selection & Architecture

| Model | Category | Primary Role | Justification |
|---|---|---|---|
| **Seasonal Naive** | Heuristic Baseline | Lower Benchmark | Baseline anchor ($y_{t} = y_{t-7}$) to prove ML adds tangible commercial value. |
| **Prophet** | Additive Decomposition | Interpretability Baseline | Fast decomposition of yearly, weekly seasonality and holiday regressors per category. |
| **LSTM** | Recurrent Neural Network | Deep Temporal Sequence | Captures long-range non-linear temporal dependencies across consecutive sequences. |
| **CatBoost** | Gradient Boosted Trees | High-Performance Champion | Superior native handling of categorical features (`Store_ID`, `Category`), robust against overfitting, and high inference speed. |

---

## 6. Evaluation Framework

Models are evaluated on the held-out 60-day test window:
- **Primary Metric:** WMAPE (Weighted Mean Absolute Percentage Error) — robust to intermittent zero-demand periods.
- **Secondary Metrics:** MAE, RMSE, Forecast Bias.
- **Selection Criteria:** Champion model selected based on lowest test WMAPE combined with inference latency under 200ms per batch.

---

## 7. Business Logic & Inventory Optimization

1. **Safety Stock ($SS$):**
   $$SS = Z_{\alpha} \times \sigma_{e} \times \sqrt{L}$$
   Where $Z_{0.95} = 1.645$ (95% service level), $\sigma_{e}$ is the standard deviation of forecast error, and $L = 7$ days lead time.
2. **Reorder Point ($ROP$):**
   $$ROP = (\hat{D}_{\text{daily}} \times L) + SS$$
3. **Stockout Risk Trigger:** Flagged whenever current on-hand inventory falls below $ROP$.
4. **Projected Revenue:** Computed as $\hat{Y}_{t} \times \text{Price}_{t} \times (1 - \text{Discount}_{t})$.

---

## 8. System Architecture & Directory Layout

```
retail-demand-forecasting/
├── .github/workflows/ci.yml       # Continuous integration
├── .vscode/settings.json          # Editor & linter configuration
├── data/                          # Data layers (raw, interim, processed, external)
├── notebooks/                     # Exploratory analysis & prototyping
├── src/                           # Production source modules
│   ├── config.py                  # Central configuration
│   ├── utils.py                   # Reproducibility seeds and loggers
│   ├── data/                      # Data loaders and generators
│   ├── preprocessing/             # Cleaning and transformation pipelines
│   ├── features/                  # Feature engineering pipeline
│   ├── models/                    # Model wrappers (Prophet, LSTM, CatBoost)
│   ├── evaluation/                # Metrics calculation and reporting
│   └── optimization/              # Safety stock, ROP, inventory logic
├── api/app.py                     # FastAPI prediction service
├── dashboard/app.py               # Streamlit interactive application
├── models/                        # Serialized artifacts (.cbm, .h5, scalers)
├── reports/figures/               # Visual outputs and plots
├── docs/                          # Technical specifications and documentation
├── tests/                         # Pytest test suite
├── scripts/verify_env.py          # Environment verification smoke test
├── Dockerfile                     # Container deployment image
├── requirements.txt               # Pinned Python package dependencies
└── README.md                      # Project documentation and quickstart
```

---

## 9. Deployment Strategy
- **Containerization:** Self-contained Docker image built on `python:3.11-slim`.
- **API Service:** FastAPI with Pydantic validation schemas running via Uvicorn.
- **Dashboard:** Streamlit UI deployed for interactive demand forecasting and inventory simulation.

---

## 10. Testing Strategy
- **Unit Tests:** Configuration validation, metric computations, seed setting.
- **Data Integrity Tests:** No duplicate keys, non-negative target values, monotonic timestamps.
- **Leakage Prevention Tests:** Verification that lag windows do not overlap with forecast horizon test targets.
- **CI Pipeline:** Automated execution via GitHub Actions on PRs to `main` and `dev`.

---

## 11. Assumptions & Limitations
- Assumes historical demand equals historical sales (unobserved stockouts are flagged as potential censored demand).
- Assumes supplier replenishment lead time is relatively stable (nominal 7 days).
- Extreme black swan events (e.g. global pandemic disruptions) are treated as anomalies via robust scaling.

---

## 12. Milestones & Timeline

| Phase | Milestone | Deliverable |
|---|---|---|
| **Week 1** | M1: Project Setup & Baseline Data | Environment verified, clean datasets, EDA, feature pipeline |
| **Week 2** | M2: Model Development | Prophet, LSTM, CatBoost trained and benchmarked |
| **Week 3** | M3: Productization | Inventory optimization module, FastAPI backend, Streamlit dashboard |
| **Week 4** | M4: Final Hardening & Polish | End-to-end testing, Docker validation, final documentation |
