# Complete Project Structure & Architecture Guide

Welcome to the **WeatherAI Platform** architectural documentation. This guide details the complete codebase structure, data flow, component responsibilities, and how all backend, frontend, database, and machine learning components interact.

---

## 1. High-Level Repository Layout

```
finalnwp/
├── .venv/                         # Python Virtual Environment
├── .vscode/                       # Editor configurations & launch tasks
└── weather-ai-platform/           # Main Production Platform
    ├── backend/                   # FastAPI Backend + ML Subsystem
    │   ├── app/                   # Core application logic
    │   │   ├── api/               # REST API route handlers
    │   │   ├── core/              # Config, DB connections, Redis, logging
    │   │   ├── models/            # SQLAlchemy ORM database models
    │   │   ├── schemas/           # Pydantic validation schemas
    │   │   ├── services/          # External integrations (Weather Union, NWP)
    │   │   └── ml/                # Machine learning pipeline implementation
    │   ├── artifacts/             # Serialized model weights & metrics
    │   ├── tests/                 # Backend test suite (Pytest, AsyncIO)
    │   ├── Dockerfile             # Backend container definition
    │   └── requirements.txt       # Python dependencies
    ├── frontend/                  # React 18 + Vite + TypeScript Web App
    │   ├── src/                   # Frontend source code
    │   │   ├── pages/             # Route pages (Dashboard, Forecast, Models)
    │   │   ├── components/        # Reusable UI widgets
    │   │   ├── charts/            # Recharts uncertainty & forecast charts
    │   │   ├── maps/              # Leaflet station visualizers
    │   │   ├── services/          # Axios HTTP client
    │   │   └── types/             # TypeScript type definitions
    │   ├── public/                # Static assets
    │   ├── dist/                  # Production compiled build
    │   ├── Dockerfile             # Frontend container definition
    │   └── package.json           # Node.js dependencies
    ├── database/                  # SQL migrations & schema initialization
    │   └── migrations/            # 001_initial_schema.sql
    ├── scripts/                   # CLI runners & training automation
    │   ├── fetch_and_train.py     # Single-city 1-year factual data trainer
    │   ├── train_multi_city.py    # Multi-city batch trainer (14+ cities)
    │   └── train.py               # Synthetic fallback trainer
    ├── data/                      # Cached 1-year historical CSV datasets
    ├── docs/                      # Complete platform documentation hub
    │   ├── README.md              # Complete structure guide (this file)
    │   ├── STARTME.md             # Localhost running instructions & API keys
    │   ├── GITUPLOAD.md           # GitHub repository upload guide
    │   └── DEPLOYMENT.md          # Cloud PaaS, VPS Docker & enterprise guide
    ├── STARTME.md                 # Localhost quick start guide (root mirror)
    ├── GITUPLOAD.md               # GitHub upload guide (root mirror)
    ├── DEPLOYMENT.md              # Production deployment guide (root mirror)
    ├── docker-compose.yml         # Full-stack Docker composition
    ├── .env.example               # Template environment configuration
    └── README.md                  # Main platform overview
```

---

## 2. Directory Breakdown & File Responsibilities

### `backend/app/` — Backend Architecture

| Directory / File | Responsibility |
| :--- | :--- |
| `app/main.py` | FastAPI application factory, CORS middleware, lifespan events, and router registration. |
| `app/core/config.py` | Pydantic `Settings` class loading `.env` securely without hardcoded secrets. |
| `app/core/database.py` | Async SQLAlchemy engine (`asyncpg` for PostgreSQL / `aiosqlite` for SQLite). |
| `app/core/redis_client.py` | Redis client for caching Weather Union and NWP API responses with 5-minute TTL. |
| `app/core/logging.py` | Structured JSON and console logging. |
| `app/api/forecast.py` | Endpoints `/api/forecast` generating point and multi-hour forecasts with confidence intervals. |
| `app/api/health.py` | Endpoint `/api/health` providing readiness, database status, and API key verification. |
| `app/api/models.py` | Endpoint `/api/models` returning live model metrics, weights, and ablation comparisons. |
| `app/api/locations.py` | Endpoint `/api/locations` managing Indian city coordinates and monitored stations. |
| `app/api/weather_union.py` | Server-side proxy caching live Weather Union station observations. |
| `app/models/` | Database entities: `Location`, `Station`, `Forecast`, `Observation`, `ModelMetric`. |
| `app/schemas/` | Pydantic request/response schemas ensuring strict type validation. |

---

### `backend/app/ml/` — Machine Learning Subsystem

```
backend/app/ml/
├── features/
│   └── engineer.py           # Feature engineering with strict leakage prevention
├── models/
│   ├── base.py               # Abstract base class for weather models
│   ├── random_forest.py      # WeatherRandomForest (Scikit-Learn)
│   ├── xgboost_model.py      # WeatherXGBoost (XGBoost Regressor)
│   ├── adaboost.py           # WeatherAdaBoost with NaN-safe imputation
│   ├── dynamic_weighting.py  # Error-inverse dynamic model weighter
│   └── neural_network.py     # TwoHeadWeatherNet (PyTorch Gaussian NLL)
├── inference/
│   └── engine.py             # MLInferenceEngine (orchestrator for loaded models)
├── metrics/
│   └── evaluation.py         # MAE, RMSE, R², MAPE, and AblationStudy framework
└── training/
    └── pipeline.py           # WeatherForecastingPipeline (chronological train/val/test)
```

#### ML Pipeline Execution Flow:
1. **Raw Historical Fetching**: Fetches ERA5 reanalysis (truth) and GFS, ECMWF, JMA hindcasts from Open-Meteo.
2. **Feature Engineering**: Computes lag features ($t-1 \dots t-24$), rolling statistics (mean, std, min, max), cyclical calendar encodings, NWP model disagreement, and Weather Union bias features.
3. **Leakage-Safe Splitting**: Chronological split (70% train / 15% validation / 15% test).
4. **Base Model Training**: Fits Random Forest, XGBoost, and AdaBoost.
5. **Ensemble & Meta-Features**: Stacks base predictions as meta-features for the neural network.
6. **Two-Head ANN**: Trains shared trunk with two output heads:
   * **Head 1**: Weather forecast prediction (minimizing MSE / Gaussian loss).
   * **Head 2**: Heteroscedastic uncertainty ($\sigma$) predicting confidence variance.
7. **Ablation Study**: Compares baseline NWP vs NWP+WU vs NWP+ML vs Full Hybrid.
8. **Artifact Serialization**: Saves model weights, scaler, feature names, and metadata into `backend/artifacts/`.

---

### `frontend/src/` — Frontend React Application

| Directory / File | Responsibility |
| :--- | :--- |
| `src/main.tsx` | React 18 DOM mount point and QueryClient provider. |
| `src/App.tsx` | Main router and application shell with navigation bar. |
| `src/pages/Dashboard.tsx` | Primary overview: current city weather, NWP comparison, and forecast summary. |
| `src/pages/Forecast.tsx` | Detailed forecast timeline with interactive uncertainty confidence bands. |
| `src/pages/Models.tsx` | Model performance leaderboard, radar charts, and feature importance visualizer. |
| `src/pages/Map.tsx` | Leaflet map displaying active weather stations across Indian cities. |
| `src/pages/Pipeline.tsx` | Visual diagram of the 5-stage ablation pipeline and dynamic weighting. |
| `src/charts/` | Recharts components for multi-model temperature, humidity, wind, and confidence bands. |
| `src/services/api.ts` | Axios HTTP client configured with base URL and error interceptors. |

---

### `scripts/` — CLI Tools & Automated Training

* [`fetch_and_train.py`](file:///c:/Users/Sarthak/OneDrive/Desktop/finalnwp/weather-ai-platform/scripts/fetch_and_train.py):
  Fetches 1 year of real historical data for any single Indian city (e.g. Delhi, Jaipur, Bengaluru, Mumbai) and runs the complete training pipeline.
* [`train_multi_city.py`](file:///c:/Users/Sarthak/OneDrive/Desktop/finalnwp/weather-ai-platform/scripts/train_multi_city.py):
  Batch runner across 14+ Indian cities, saving datasets to `data/` and per-city model weights to `backend/artifacts/<city>/`.
* [`train.py`](file:///c:/Users/Sarthak/OneDrive/Desktop/finalnwp/weather-ai-platform/scripts/train.py):
  Synthetic data generator and pipeline demonstrator for offline sandbox testing.

---

## 3. Data Flow Architecture

```
[ Open-Meteo API ]                [ Weather Union API ]
  - ERA5 Reanalysis (Truth)          - Live Station Observations
  - GFS, ECMWF, JMA Forecasts        - Hyperlocal Urban Bias
         │                                    │
         ▼                                    ▼
┌────────────────────────────────────────────────────────┐
│            Feature Engineering Engine                  │
│  - Shifted Lag (t-1 to t-24)                           │
│  - Rolling Windows (3h, 6h, 12h, 24h)                  │
│  - Solar / Calendar Cyclical Encodings                 │
│  - NWP Disagreement & Spread Metrics                   │
│  - Weather Union Bias Calculations                     │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│            Multi-Model Machine Learning Tier           │
│  ┌─────────────────┬─────────────────┬──────────────┐  │
│  │  Random Forest  │     XGBoost     │   AdaBoost   │  │
│  └────────┬────────┴────────┬────────┴──────┬───────┘  │
│           │                 │               │          │
│           └─────────────────┼───────────────┘          │
│                             ▼                          │
│                Dynamic Model Weighter                  │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│               Two-Head Neural Network                  │
│  Trunk: Dense(256) → Dense(128) → Dense(64) → Dense(32)│
│  ├── HEAD 1: Predicted Weather Target (e.g. Temp °C)   │
│  └── HEAD 2: Heteroscedastic Uncertainty (σ / Conf.)   │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│            FastAPI REST & WebSocket Layer             │
│  /api/forecast  •  /api/models  •  /api/health         │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│           React 18 Dashboard & Leaflet Maps            │
└────────────────────────────────────────────────────────┘
```

---

## 4. Documentation Index

For operational guides, refer to:
* **[STARTME.md](file:///c:/Users/Sarthak/OneDrive/Desktop/finalnwp/weather-ai-platform/STARTME.md)**: Localhost running commands, API key instructions, and environment variables.
* **[GITUPLOAD.md](file:///c:/Users/Sarthak/OneDrive/Desktop/finalnwp/weather-ai-platform/GITUPLOAD.md)**: Git initialization, security checklist, and GitHub push steps.
* **[DEPLOYMENT.md](file:///c:/Users/Sarthak/OneDrive/Desktop/finalnwp/weather-ai-platform/DEPLOYMENT.md)**: Production deployment options (Vercel, Render, VPS Docker, AWS/GCP).
