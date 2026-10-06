# WeatherAI — Adaptive AI–NWP Multi-Model Weather Forecasting & Verification Platform

A production-grade, uncertainty-aware meteorological forecasting system combining Numerical Weather Prediction (NWP) global models (GFS, ECMWF, JMA), real-time METAR & Weather Union airport observations, and a 14-City Model Output Statistics (MOS) machine-learning ensemble (**Random Forest + XGBoost + AdaBoost + Heteroscedastic Two-Head PyTorch ANN**).

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [14-City Synoptic Verification Network](#14-city-synoptic-verification-network)
3. [Architecture & Project Layout](#architecture--project-layout)
4. [ML Methodology & MOS Residual Framework](#ml-methodology--mos-residual-framework)
5. [Quick Start — Running Locally](#quick-start--running-locally)
   - [A. Windows (PowerShell)](#a-windows-powershell)
   - [B. WSL Ubuntu / Linux](#b-wsl-ubuntu--linux)
6. [Multi-City 1-Year Factual Training](#multi-city-1-year-factual-training)
7. [Weather Union & METAR Integration](#weather-union--metar-integration)
8. [Dynamic Inverse-MAE Weight Router](#dynamic-inverse-mae-weight-router)
9. [Two-Head Heteroscedastic ANN](#two-head-heteroscedastic-ann)
10. [Environment Variables](#environment-variables)
11. [100% Free Cloud Deployment (Vercel)](#100-free-cloud-deployment-vercel)
12. [Docker Deployment](#docker-deployment)
13. [API Documentation](#api-documentation)
14. [Testing & Verification](#testing--verification)

---

## 🌡️ Project Overview

WeatherAI does **not** simply average raw NWP model outputs. It implements a **Model Output Statistics (MOS)** framework that:

- Predicts residual error $\hat{y}_{res} = y_{truth} - y_{nwp\_valid}(t+H)$ with valid-time lead alignment.
- Corrects systematic boundary-layer biases in coastal and complex land-sea breeze regimes (achieving up to **+45.3% MAE reduction** in Ahmedabad, **+34.6%** in Kochi, and **+28.7%** in Mumbai).
- Dynamically allocates model weights $w_m \propto \frac{1}{\text{MAE}_m + \epsilon}$ with a 5% minimum floor safeguard to prevent overfit in hyper-accurate inland regimes (e.g. Pune MAE 0.44°C).
- Outputs 95% Gaussian Confidence Bands ($\pm 1.96\sigma$) via a Two-Head PyTorch ANN trained under Negative Log-Likelihood (NLL) Loss.

```
GFS (0.25°) + ECMWF (0.1°) + JMA GSM
                  +
METAR & Weather Union Real-Time Observations
                  ↓
MOS Feature Matrix (t+H Valid Alignment, Issue-Time Bias e_t, Lags)
                  ↓
MOS RF + XGBoost + AdaBoost  →  Inverse-MAE Router
                  ↓
Two-Head PyTorch ANN
  ├── HEAD 1: Mean Forecast (μ)
  └── HEAD 2: Log-Variance Uncertainty (σ²)
                  ↓
Operational Meteorologist Forecast + 95% Confidence Bounds (±1.96σ)
```

---

## 🏆 14-City Synoptic Verification Network

Evaluated on **1-Year (8,784 hourly samples per city, 122.9k total obs)** of factual ERA5 reanalysis and METAR airport observations across India:

| City | ICAO Code | Coordinates | 1-Yr Samples | Raw NWP MAE | MOS Best MAE | Skill Score ($SS_{NWP}$) | Optimal Model |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **Ahmedabad** | `VAAH` | 23.07°N, 72.63°E | 8,784 | 1.61°C | **0.88°C** | **+45.3%** | XGBoost |
| **Kochi** | `VOCI` | 9.93°N, 76.26°E | 8,784 | 1.10°C | **0.72°C** | **+34.6%** | XGBoost |
| **Mumbai** | `VABB` | 19.08°N, 72.88°E | 8,784 | 0.94°C | **0.67°C** | **+28.7%** | XGBoost |
| **Hyderabad** | `VOHS` | 17.39°N, 78.49°E | 8,784 | 1.23°C | **0.95°C** | **+22.8%** | Random Forest |
| **Bengaluru** | `VOBL` | 12.98°N, 77.59°E | 8,784 | 0.94°C | **0.82°C** | **+12.8%** | XGBoost |
| **Chennai** | `VOMM` | 13.08°N, 80.27°E | 8,784 | 1.03°C | **0.93°C** | **+9.7%** | XGBoost |
| **Delhi** | `VIDP` | 28.56°N, 77.10°E | 8,784 | 1.19°C | 1.19°C | 0.0% | NWP Baseline |
| **Kolkata** | `VECC` | 22.65°N, 88.45°E | 8,784 | 0.83°C | 0.83°C | 0.0% | NWP Baseline |
| **Pune** | `VAPO` | 18.58°N, 73.92°E | 8,784 | 0.44°C | 0.44°C | 0.0% | NWP Baseline |
| **Jaipur** | `VIJP` | 26.82°N, 75.80°E | 8,784 | 0.83°C | 0.83°C | 0.0% | NWP Baseline |
| **Lucknow** | `VILK` | 26.76°N, 80.88°E | 8,784 | 1.05°C | 1.05°C | 0.0% | NWP Baseline |
| **Chandigarh** | `VICG` | 30.67°N, 76.79°E | 8,784 | 0.98°C | 0.98°C | 0.0% | NWP Baseline |
| **Bhopal** | `VABP` | 23.26°N, 77.41°E | 8,784 | 1.12°C | 1.12°C | 0.0% | NWP Baseline |
| **Patna** | `VEPT` | 25.59°N, 85.09°E | 8,784 | 1.08°C | 1.08°C | 0.0% | NWP Baseline |

---

## 🏗️ Architecture & Project Layout

```
weather-ai-platform/
├── backend/                   # FastAPI Serverless & REST API
│   ├── api/                   # Vercel Serverless entry point (index.py)
│   ├── app/
│   │   ├── api/               # Models, Forecast, Weather, Health endpoints
│   │   ├── core/              # Config, DB, Logging
│   │   ├── ml/
│   │   │   ├── features/      # MOS Feature Matrix & Cyclical Encoding
│   │   │   ├── models/        # RF, XGBoost, AdaBoost, Two-Head ANN
│   │   │   ├── training/      # Chronological Pipeline (70/15/15)
│   │   │   └── inference/     # High-performance ML Engine
│   │   └── services/          # NWP Open-Meteo & METAR API clients
│   └── artifacts/             # Trained 14-city models & multi_city_summary.json
├── frontend/                  # React 18 + Vite + TypeScript
│   └── src/
│       ├── pages/             # Dashboard, Forecast, Models, Map, Pipeline
│       ├── components/        # Synoptic UI Components & Metric Cards
│       ├── charts/            # 95% CI Area & Dual-Axis Uncertainty Charts
│       ├── maps/              # Leaflet 14-Station METAR Pins & Basemaps
│       ├── hooks/             # React Query Hooks
│       └── services/          # Axios API Client
├── scripts/
│   ├── train_multi_city.py    # 14-City 365-Day Factual Batch Trainer
│   └── fetch_and_train.py     # METAR & ERA5 Data Ingestion Script
├── vercel.json                # Full-Stack Vercel Deployment Specification
├── docker-compose.yml         # Local Docker Production Environment
└── README.md
```

---

## ⚡ Quick Start — Running Locally

### Prerequisites
- **Node.js**: v18+ or v20+
- **Python**: v3.10, v3.11, or v3.12

---

### A. Windows (PowerShell)

#### 1. Start the Backend API Server
```powershell
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# Start FastAPI server on port 8000
uvicorn app.main:app --reload --port 8000
```
- API Swagger Docs available at: `http://localhost:8000/api/docs`

#### 2. Start the Frontend Application (In a second terminal)
```powershell
cd frontend

# Install Node dependencies
npm install

# Start Vite dev server on port 5173
npm run dev
```
- Open `http://localhost:5173` in your browser!

---

### B. WSL Ubuntu / Linux

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

---

## 🏋️ Multi-City 1-Year Factual Training

To train or update the ML models across all 14 Indian cities using 365 days (8,784 hourly samples) of factual ERA5 reanalysis and METAR station truth:

```bash
# Run 14-city batch training (365 days per city)
python scripts/train_multi_city.py --days 365 --target temperature_c --cities all

# Output summary report will be saved to:
# backend/artifacts/multi_city_summary.json
```

---

## 📡 Weather Union & METAR Integration

[Weather Union](https://www.weatherunion.com/) and METAR ASOS airport feeds provide hyper-local weather station ground truth across Indian airports (`VIDP`, `VABB`, `VOBL`, etc.).

### Setting your API key:
1. Open `backend/.env` (copy from `.env.example`).
2. Add your key:
   ```env
   WEATHER_UNION_API_KEY=your_actual_api_key_here
   ```
3. Restart backend. Note: If no API key is provided, the platform automatically degrades gracefully to factual METAR & NWP reanalysis mode.

---

## ⚖️ Dynamic Inverse-MAE Weight Router

Model weights are dynamically calculated from rolling verification metrics:

$$w_m = \frac{\frac{1}{\text{MAE}_m + \epsilon}}{\sum_{k} \frac{1}{\text{MAE}_k + \epsilon}}$$

- Enforces exponential smoothing ($\alpha=0.3$).
- Minimum floor safeguard ($w_m \ge 0.05$) to prevent model collapse.

---

## 🧠 Two-Head Heteroscedastic ANN

Trained under Gaussian Negative Log-Likelihood (NLL) Loss:

$$\mathcal{L}_{NLL} = \frac{(y - \mu)^2}{2\sigma^2} + \frac{1}{2}\log(\sigma^2)$$

- **Head 1 ($\mu$)**: Predicts calibrated mean temperature forecast.
- **Head 2 ($\log \sigma^2$)**: Predicts heteroscedastic uncertainty, providing 95% Confidence Interval bounds ($\hat{y} \pm 1.96\sigma$).

---

## 🌐 100% Free Cloud Deployment (Vercel)

The repository is configured with `vercel.json` for 1-click full-stack deployment on Vercel:

1. Push your code to GitHub:
   ```bash
   git add .
   git commit -m "Deploy Weather AI Platform"
   git push origin main
   ```
2. Go to [https://vercel.com/new](https://vercel.com/new) and import your GitHub repository (`AI-NWP`).
3. Leave Root Directory as `./` and click **Deploy**.
4. Vercel automatically builds:
   - **Frontend**: Vite SPA built from `./frontend`.
   - **Backend API**: FastAPI serverless execution via `./api/index.py`.

---

## 🐳 Docker Deployment

To launch the full stack (PostgreSQL + Redis + FastAPI Backend + React Nginx Frontend) using Docker:

```bash
cp .env.example .env
docker-compose up --build
```
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`

---

## 🧪 Testing & Verification

Run the automated pytest suite:

```bash
cd backend
pytest -v
```

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.
