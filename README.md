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
- **Current Milestone:** **Day 2 Complete** (Data Collection, Ingestion, Profiling, Manifest Verification & Interim Loader)
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
│   ├── raw/                  # Immutable original datasets
│   ├── interim/              # Intermediate transformations
│   ├── processed/            # Cleaned data and feature-engineered datasets
│   └── external/             # Holiday calendars and weather telemetry
├── notebooks/                # Research and exploratory Jupyter notebooks
├── src/                      # Production source package
│   ├── config.py             # Configuration loader
│   ├── utils.py              # Reproducibility seed management and logging
│   ├── data/                 # Ingestion and synthetic data generators
│   ├── preprocessing/        # Data cleaning and sanity validation
│   ├── features/             # Lag, rolling, and temporal feature engineering
│   ├── models/               # Prophet, LSTM, and CatBoost models
│   ├── evaluation/           # MAE, RMSE, MAPE, WMAPE evaluation metrics
│   └── optimization/         # Safety stock, ROP, inventory simulation
├── api/                      # FastAPI REST application
├── dashboard/                # Streamlit interactive dashboard
├── models/                   # Serialized model weights and artifacts
├── reports/figures/          # Generated charts and diagrams
├── docs/                     # Architecture, technical specs, and KPIs
│   ├── tech_spec.md
│   ├── data_dictionary.md
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

### 3. Verify Environment & Tests

```bash
# Run environment smoke test
python scripts/verify_env.py

# Run test suite
pytest
```

### 4. Launch Dashboard & API

```bash
# Run Streamlit dashboard
streamlit run dashboard/app.py

# Run FastAPI service
uvicorn api.app:app --reload --port 8000
```

---

## Data & Benchmark Strategy

The platform implements **Option D: Hybrid Strategy** using the Kaggle **M5 Forecasting (Walmart)** benchmark schema:
- **Baseline Dynamics:** Authentic SKU-level count series capturing empirical intermittency (42.2% zero-sales cells) and weekly retail pricing.
- **Stratified Representative Portfolio:** 108 SKUs sampled across 3 super-categories (`FOODS`, `HOBBIES`, `HOUSEHOLD`) and 3 demand terciles (low/medium/high) across 10 retail stores.
- **Data Integrity:** Raw files are cataloged with SHA-256 hashes in `data/raw/m5/MANIFEST.md`.
- **Interim Storage:** Reshaped into daily long format with attached shelf prices in `data/interim/m5_subset_long.parquet` (788,400 observations).
- **Adaptations (Day 3):** Re-indexing to Indian Tier-1/2 retail hubs, ₹ price scaling, gazetted festival calendar, Open-Meteo weather telemetry, and simulated inventory stocks.

---

## Documentation

- [Technical Specification](docs/tech_spec.md)
- [Data Sources & Strategy](docs/data_sources.md)
- [Data Dictionary](docs/data_dictionary.md)
- [Business & Forecast KPIs](docs/kpis.md)
- [Day 2 Implementation Guide](docs/day2_data_collection.md)

---

## License

This project is licensed under the [MIT License](LICENSE).

