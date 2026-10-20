# Retail Demand Forecasting & Inventory Optimization Platform

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

An end-to-end machine learning platform that forecasts multi-horizon retail demand and optimizes inventory reorder points to prevent stockouts and minimize holding costs.

```
Collect ──► Clean ──► Engineer Features ──► Forecast Demand ──► Compare Models ──► Optimize Inventory ──► Visualize ──► Deploy
```

---

## Project Status

- **Status:** In Progress (4-Week Implementation Plan)
- **Current Milestone:** **Day 3 Complete** (Domain Adaptation, Indian Retail Mapping, Holiday/Festival Calendars, Weather Integration, Inventory Simulation & Dataset Assembly)
- **Author:** Md Hussain

---

## Key Features

- **Multi-Model Forecasting Benchmark:**
  - *Seasonal Naive Baseline:* Benchmark lower bound.
  - *Facebook Prophet:* Additive time-series decomposition for seasonality and holiday trends.
  - *Deep Learning (LSTM):* Sequential temporal pattern learning.
  - *CatBoost Regressor:* Feature-rich gradient boosted tabular model handling complex interactions.
- **Inventory & Supply Chain Optimization:**
  - Dynamic Safety Stock ($SS$) computation based on forecast uncertainty.
  - Automatic Reorder Point ($ROP$) calculation.
  - Simulation of stockout reduction and holding cost savings.
- **Full-Stack ML Engineering:**
  - Modular Python pipeline (`src/`) with reproducible configuration (`config.yaml`).
  - Interactive **Streamlit** dashboard for business planners.
  - High-performance **FastAPI** prediction endpoint.
  - Production containerization via **Docker**.

---

## Project Structure

```text
retail-demand-forecasting/
├── .github/workflows/        # CI automation workflows
├── .vscode/                  # Workspace settings and debugger configurations
├── data/
│   ├── raw/                  # Immutable original datasets and assembled raw dataset
│   ├── interim/              # Intermediate transformations and dimension masters
│   ├── processed/            # Cleaned data and feature-engineered datasets
│   ├── external/             # Mappings, holiday calendars, and weather telemetry
│   └── sample/               # Light sample dataset for review without raw data
├── notebooks/                # Research and exploratory Jupyter notebooks
├── src/                      # Production source package
│   ├── config.py             # Configuration loader
│   ├── utils.py              # Reproducibility seed management and logging
│   ├── data/                 # Ingestion, adaptation, simulations, and assembly
│   ├── preprocessing/        # Data cleaning and sanity validation
│   ├── features/             # Lag, rolling, and temporal feature engineering
│   ├── models/               # Prophet, LSTM, and CatBoost models
│   ├── evaluation/           # MAE, RMSE, MAPE, WMAPE evaluation metrics
│   └── optimization/         # Safety stock, ROP, inventory simulation
├── api/                      # FastAPI REST application
├── dashboard/                # Streamlit interactive dashboard
├── models/                   # Serialized model weights and artifacts
├── reports/                  # Validation reports and dataset profiles
├── docs/                     # Architecture, technical specs, and guides
│   ├── tech_spec.md
│   ├── data_dictionary.md
│   ├── data_sources.md
│   └── kpis.md
├── tests/                    # Pytest test suite
├── scripts/                  # Verification and utility scripts
├── Dockerfile                # Container deployment definition
├── requirements.txt          # Python dependency specifications
└── README.md                 # Project overview and documentation
```

---

## Quick Start

### 1. Clone & Set Up Virtual Environment

```bash
# Clone the repository
git clone <repo-url>
cd retail-demand-forecasting

# Create and activate Python 3.11 virtual environment
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1    # On Linux/macOS: source .venv/bin/activate

# Upgrade pip and install dependencies
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### 2. Acquire Raw Data & Build Interim Parquet
```bash
# Acquire/download raw M5 dataset and generate SHA-256 manifest
python -m src.data.download
python -m src.data.manifest

# Run stratified sampling and build interim long dataset
python scripts/build_interim_data.py
```

### 3. Assemble Day 3 Adapted Dataset & Validate
```bash
# Run full adaptation, weather telemetry, inventory simulation, and assembly
python -m src.data.assemble

# Validate data integrity and generate markdown profile report
python -m src.data.validate_raw
```

### 4. Verify Environment & Tests

```bash
# Run environment smoke test
python scripts/verify_env.py

# Run test suite
pytest
```

### 5. Launch Dashboard & API

```bash
# Run Streamlit dashboard
streamlit run dashboard/app.py

# Run FastAPI service
uvicorn api.app:app --reload --port 8000
```

---

## Data & Benchmark Strategy

The platform implements **Option D: Hybrid Strategy** using the Kaggle **M5 Forecasting (Walmart)** benchmark schema:
- **Baseline Dynamics:** Authentic SKU-level count series capturing empirical intermittency (68.0% zero-sales cells) and weekly retail pricing.
- **Stratified Representative Portfolio:** 108 SKUs sampled across 3 super-categories (`FOODS`, `HOBBIES`, `HOUSEHOLD`) and 3 demand terciles (low/medium/high) across 10 retail stores.
- **Data Integrity:** Raw files are cataloged with SHA-256 hashes in `data/raw/m5/MANIFEST.md`. Raw benchmark data files are not tracked in Git.
- **Interim Storage:** Reshaped into daily long format with attached shelf prices in `data/interim/m5_subset_long.parquet` (2,096,280 observations).
- **Domain Adaptations (Day 3 Complete):**
  - Mapped to 10 Indian retail stores across 9 Tier-1/Tier-2 metropolitan hubs.
  - Category-based ₹ price scaling (paise precision) and COGS margins in `data/external/product_master.parquet`.
  - Derived regular reference prices and promotion flags.
  - Authentic Indian holiday calendar (`holidays` + custom festival registry) with 7-day pre-festival shopping windows.
  - Real daily weather telemetry (temperature and precipitation) fetched and cached from Open-Meteo Historical Archive.
  - Documented, switchable festival demand uplift with stochastic rounding.
  - Daily inventory on-hand, stockouts, and shortfalls simulated via periodic review $(R=7, S)$ order-up-to policy.
  - Assembled target dataset: `data/raw/retail_demand_raw.parquet` ($2,096,280$ rows $\times$ $21$ columns).
  - Lightweight preview sample committed in `data/sample/sample_sales.csv`.

---

## Documentation

- [Technical Specification](docs/tech_spec.md)
- [Data Sources & Strategy](docs/data_sources.md)
- [Data Dictionary](docs/data_dictionary.md)
- [Business & Forecast KPIs](docs/kpis.md)
- [Day 2 Implementation Guide](docs/day2_data_collection.md)
- [Day 3 Implementation Guide](docs/day3_data_collection_and_adaptation.md)

---

## License

This project is licensed under the [MIT License](LICENSE).

