# Business & Forecast KPIs — Retail Demand Forecasting Platform

**Project:** Retail Demand Forecasting & Inventory Optimization Platform  
**Author:** Md Hussain  
**Date:** October 2026

---

## 1. Forecast Accuracy KPIs

Accuracy metrics quantify how closely model predictions $\hat{y}_t$ align with observed real ground-truth demand $y_t$ over the test evaluation horizon $H$.

| Metric | Mathematical Formula | Units / Range | Purpose & Interpretation |
|---|---|---|---|
| **MAE** (Mean Absolute Error) | $\frac{1}{N} \sum_{i=1}^N \vert y_i - \hat{y}_i \vert$ | Same as target (units) | Direct intuitive magnitude of average error per forecast instance. Robust to single extreme outliers. |
| **RMSE** (Root Mean Squared Error) | $\sqrt{\frac{1}{N} \sum_{i=1}^N (y_i - \hat{y}_i)^2}$ | Same as target (units) | Heavily penalizes large forecasting misses. Critical for operations where large errors trigger emergency logistical costs. |
| **MAPE** (Mean Absolute Percentage Error) | $\frac{100\%}{N} \sum_{i=1}^N \left\vert \frac{y_i - \hat{y}_i}{y_i} \right\vert$ | Percentage (%) | Percentage relative deviation. *Limitation:* Undefined or explodes when actual demand $y_i = 0$ (intermittent demand). |
| **WMAPE** (Weighted Mean Absolute Percentage Error) | $\frac{\sum_{i=1}^N \vert y_i - \hat{y}_i \vert}{\sum_{i=1}^N y_i} \times 100\%$ | Percentage (%) | Volume-weighted error. Completely avoids zero-division issues; highly recommended industry standard for retail. |
| **Forecast Bias** | $\frac{1}{N} \sum_{i=1}^N (\hat{y}_i - y_i)$ | Units ($-\infty$ to $+\infty$) | Measures systemic over-forecasting ($\text{Bias} > 0$) or under-forecasting ($\text{Bias} < 0$). Ideal is $0$. |

---

## 2. Inventory & Supply Chain Business KPIs

These metrics evaluate the commercial impact of replacing heuristic reorder points with ML forecast-driven inventory targets.

| Business Metric | Formula / Computation | Target Direction | Business Meaning |
|---|---|---|---|
| **Stockout Rate** | $\frac{\text{Days with } \text{Inventory} = 0 \text{ & Demand} > 0}{\text{Total Operating Days}} \times 100\%$ | Minimise ($\le 2\%$) | Proportion of sales lost due to exhausted inventory on the retail floor. |
| **Overstock Rate** | $\frac{\text{SKU-Days with } \text{Inventory} > (\hat{D}_{\text{horizon}} + \text{Safety Stock})}{\text{Total SKU-Days}} \times 100\%$ | Minimise ($\le 5\%$) | Tied-up working capital and risk of spoilage or holding depreciation. |
| **Fill Rate** | $\frac{\text{Demand Fulfilled}}{\text{Total Customer Demand}} \times 100\%$ | Maximise ($\ge 98\%$) | Service level experienced by shoppers. |
| **Days of Cover (DoC)** | $\frac{\text{Current Inventory On Hand}}{\text{Forecast Daily Demand}}$ | Target 7–14 days | How many days the current stock can satisfy demand before depletion. |
| **Reorder Point (ROP)** | $(\hat{D}_{\text{lead\_time}}) + \text{Safety Stock}$ | Operational control | The stock threshold that triggers automated inventory replenishment. |
| **Safety Stock ($SS$)** | $Z \times \sigma_{\text{forecast\_error}} \times \sqrt{L}$ | Risk buffer | Stock maintained to absorb demand volatility during lead time $L$ with service factor $Z_{0.95} = 1.645$. |
| **Holding Cost Savings** | $(\text{Baseline Avg Stock} - \text{Optimized Avg Stock}) \times \text{Unit Cost} \times r_{\text{holding}}$ | Maximise savings | Direct financial savings from reduced excess inventory ($r_{\text{holding}} \approx 20\%$/year). |
| **Forecasted Revenue** | $\sum_{t=1}^H (\hat{y}_t \times \text{Expected Net Price}_t)$ | Predictive metric | Forward-looking revenue projection for finance and procurement teams. |

---

## 3. Success Benchmarks for Day 1 Spec

1. **Baseline Outperformance**:
   - The primary champion model (CatBoost / LSTM) must demonstrate at least a **15% reduction in WMAPE** compared to the seasonal naive baseline (same weekday last week).
   - Prophet baseline must outperform flat historical average.
2. **Operational Target**:
   - Simulation must demonstrate a **20% to 30% reduction in simulated stockouts** while keeping holding costs flat or lower compared to fixed static threshold replenishment.
