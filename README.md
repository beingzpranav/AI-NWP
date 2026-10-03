# WeatherAI — Adaptive AI–NWP Multi-Model Weather Forecasting Platform

A production-grade weather forecasting system that intelligently combines multiple Numerical Weather Prediction (NWP) models, real-time Weather Union observations, and a machine-learning ensemble (Random Forest + XGBoost + AdaBoost + Two-Head ANN) to produce localized, uncertainty-aware forecasts.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [ML Methodology](#ml-methodology)
4. [Weather Union Integration](#weather-union-integration)
5. [NWP Integration](#nwp-integration)
6. [Feature Engineering](#feature-engineering)
7. [Dynamic Weighting](#dynamic-weighting)
8. [Two-Head ANN Architecture](#two-head-ann-architecture)
9. [⚠️ Where to Put the Weather Union API Key](#️-where-to-put-the-weather-union-api-key)
10. [Installation](#installation)
11. [Environment Variables](#environment-variables)
12. [Training](#training)
13. [Running Locally](#running-locally)
14. [API Documentation](#api-documentation)
15. [Testing](#testing)
16. [Docker Deployment](#docker-deployment)
17. [Security](#security)
18. [Limitations](#limitations)
19. [Future Improvements](#future-improvements)

---

## Project Overview

WeatherAI does **not** simply average NWP model outputs. It learns:

- Which NWP model is currently more reliable under which conditions
- How local Weather Union observations differ from NWP grid forecasts
- How to correct systematic NWP biases using localized observations
- How confident each forecast is, via a heteroscedastic uncertainty head

**Forecasting pipeline in brief:**

```
GFS + ECMWF + JMA (via Open-Meteo)
        +
Weather Union real-time observations
        ↓
Feature Engineering (lag, rolling, bias, cyclical, disagreement)
        ↓
RF + XGBoost + AdaBoost  →  Dynamic Weighting
        ↓
Two-Head ANN
  ├── HEAD 1: Weather Prediction
  └── HEAD 2: Uncertainty / Confidence
        ↓
Final Corrected Forecast + Confidence Bands
```

---

## Architecture

```
weather-ai-platform/
├── backend/                   # FastAPI + SQLAlchemy + ML
│   ├── app/
│   │   ├── api/               # REST endpoints
│   │   ├── core/              # Config, DB, cache, logging
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── weather_union/ # WU API client (server-side only)
│   │   │   ├── nwp/           # Open-Meteo NWP client
│   │   │   ├── forecasting/   # Forecasting engine
│   │   │   └── ingestion/     # DB seeder
│   │   └── ml/
│   │       ├── features/      # Feature engineering
│   │       ├── models/        # RF, XGBoost, AdaBoost, DW, ANN
│   │       ├── training/      # Full training pipeline
│   │       └── metrics/       # Evaluation & ablation
│   └── tests/
├── frontend/                  # React + Vite + TypeScript
│   └── src/
│       ├── pages/             # Dashboard, Forecast, Models, Map, Pipeline
│       ├── components/        # Reusable UI components
│       ├── charts/            # Recharts visualizations
│       ├── maps/              # Leaflet map
│       ├── hooks/             # React Query hooks
│       ├── services/          # Axios API client
│       └── types/             # TypeScript interfaces
├── database/
│   └── migrations/            # SQL schema
├── scripts/
│   └── train.py               # Training runner
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## ML Methodology

### Data Leakage Prevention

All features are strictly leakage-safe:

- **Lag features** use `shift(n)` where `n ≥ 1` — never `n = 0`
- **Rolling features** apply `shift(1)` before `.rolling()` — excludes current timestep
- **Train/val/test split** is chronological (70/15/15) — never random shuffle
- **Scaler** (`StandardScaler`) is fit on the training set only, then applied to val/test
- **Targets** are shifted back by `horizon_hours` so row `t` predicts `t + horizon`
- **Weather Union** observations at `t` are valid inputs when forecasting `t + h`, but observations at `t + h` are never used

### Chronological Validation

```python
train = df.iloc[:int(n * 0.70)]
val   = df.iloc[int(n * 0.70):int(n * 0.85)]
test  = df.iloc[int(n * 0.85):]
```

Time-series data must never be randomly split. Random splitting creates future leakage and produces optimistically biased metrics.

---

## Weather Union Integration

[Weather Union](https://www.weatherunion.com/) (Zomato) provides a dense network of hyper-local weather stations across Indian cities.

### Role in the system

| Purpose | How it's used |
|---|---|
| Real-time observations | Current temperature, humidity, wind, rainfall at the station level |
| NWP bias correction | `bias_gfs_temp = WU_temp - GFS_temp` — fed as a feature |
| WU correction feature | Decays with forecast horizon: `correction_weight = max(0, 1 - h/48)` |
| Confidence boost | WU availability increases confidence at short horizons |
| Ablation study | The system measures whether WU actually improves accuracy |

### How WU corrects the forecast

```
ECMWF → 31.8°C
GFS   → 32.4°C
JMA   → 31.5°C
WU observation → 33.1°C  (local urban heat)

bias_ecmwf = 33.1 - 31.8 = +1.3°C  (ECMWF underestimates locally)

correction_weight at h=0  = 1.00
correction_weight at h=6  = 0.875
correction_weight at h=24 = 0.50
correction_weight at h=48 = 0.00

corrected_temp = blended_nwp + correction_weight × bias × 0.6
```

---

## NWP Integration

NWP data is fetched via [Open-Meteo](https://open-meteo.com/) — free, no API key required.

| Model | Source | Resolution | Notes |
|---|---|---|---|
| GFS | NOAA | 0.25° | Global Forecast System |
| ECMWF IFS | ECMWF | 0.25° | Integrated Forecast System |
| JMA GSM | JMA | 0.25° | Global Spectral Model |

Each model is fetched independently so the system can:
- Compute per-model bias vs Weather Union
- Calculate model disagreement features
- Apply dynamic reliability-based weighting

NWP data is cached in Redis for 1 hour to prevent redundant API calls.

---

## Feature Engineering

Full feature set built in `backend/app/ml/features/engineer.py`:

### Temporal features (cyclical encoding)
```python
hour_sin = sin(2π × hour / 24)
hour_cos = cos(2π × hour / 24)
dow_sin, dow_cos, doy_sin, doy_cos, month_sin, month_cos
```

### Lag features (leakage-safe, shift ≥ 1)
```
temperature_c_lag_1h, _lag_2h, _lag_3h, _lag_6h, _lag_12h, _lag_24h
(same for humidity, wind, pressure, precipitation)
```

### Rolling features (shift(1) before rolling)
```
temperature_c_roll_mean_3h, _roll_std_6h, _roll_min_12h, _roll_max_24h
```

### NWP disagreement features
```
nwp_mean_temperature_c    — mean across models
nwp_std_temperature_c     — std across models (model uncertainty)
nwp_range_temperature_c   — max - min (model spread)
nwp_gfs_ecmwf_diff_temperature_c
nwp_gfs_jma_diff_temperature_c
nwp_ecmwf_jma_diff_temperature_c
```

### Weather Union bias features
```
bias_gfs_temperature_c    = WU_temp - GFS_temp
bias_ecmwf_temperature_c  = WU_temp - ECMWF_temp
bias_jma_temperature_c    = WU_temp - JMA_temp
(same for humidity, wind, pressure)
```

### Source availability flags
```
gfs_available, ecmwf_available, jma_available, weather_union_available
```

---

## Dynamic Weighting

Model weights are **never hardcoded**. They are computed from recent forecast errors:

```python
# 1. Compute MAE for each model over a rolling window
mae_gfs   = mean(|actual - gfs_pred|)   # e.g. 1.4°C
mae_ecmwf = mean(|actual - ecmwf_pred|) # e.g. 0.8°C  ← most accurate
mae_jma   = mean(|actual - jma_pred|)   # e.g. 1.9°C

# 2. Convert to reliability scores (inverse MAE)
rel_gfs   = 1 / (mae_gfs   + ε) = 0.71
rel_ecmwf = 1 / (mae_ecmwf + ε) = 1.25
rel_jma   = 1 / (mae_jma   + ε) = 0.53

# 3. Normalize → weights sum to 1.0
w_gfs   = 0.71 / (0.71 + 1.25 + 0.53) = 0.284
w_ecmwf = 1.25 / 2.49                  = 0.502
w_jma   = 0.53 / 2.49                  = 0.213

# 4. Apply minimum floor (5%) and exponential smoothing (α=0.3)
# 5. Final blend
forecast = 0.284×GFS + 0.502×ECMWF + 0.213×JMA
```

Key properties:
- Weights always sum to 1.0
- Every model gets at least 5% (min floor prevents total exclusion)
- Exponential smoothing (α=0.3) prevents rapid oscillation
- Separate weights computed per variable, per location, per horizon

---

## Two-Head ANN Architecture

```
Input (n_features)
    ↓
Dense(256) → BatchNorm → GELU → Dropout(0.3)
    ↓
Dense(128) → BatchNorm → GELU → Dropout(0.2)
    ↓
Dense(64)  → GELU
    ↓
Dense(32)  → Shared Representation
    ├──────────────────────────────
    │                              │
HEAD 1 (Forecast)          HEAD 2 (Uncertainty)
Dense(16) → GELU           Dense(16) → GELU
Dense(n_targets)           Dense(n_targets)
[linear activation]        [log-variance output]
    │                              │
predicted values           σ = exp(0.5 × log_var)
```

### Loss function — Heteroscedastic NLL

```
Loss = 0.5 × log_var + 0.5 × (y - ŷ)² × exp(-log_var)
```

This forces the model to be **calibrated** — it cannot reduce loss simply by predicting large uncertainty everywhere. The uncertainty must reflect actual prediction errors.

### Confidence score

```python
confidence = 1.0 / (1.0 + mean_std_dev)  # bounded [0, 1]
```

High model disagreement (large σ) → low confidence. The score is derived from measured uncertainty, not arbitrary.

---

## ⚠️ Where to Put the Weather Union API Key

**The API key must ONLY exist on the backend server. Never paste it into frontend code.**

### Step-by-step

**1.** Open the backend environment file:
```
weather-ai-platform/backend/.env
```
(Copy from `.env.example` if it doesn't exist yet)

**2.** Find this line:
```
WEATHER_UNION_API_KEY=PASTE WEATHER UNION API KEY
```

**3.** Replace it with your real key:
```
WEATHER_UNION_API_KEY=your_actual_key_here
```

**4.** Save the file and restart the backend:
```bash
# Local
uvicorn app.main:app --reload

# Docker
docker-compose restart backend
```

**5.** Verify it's working:
```bash
curl http://localhost:8000/api/weather/weather-union/status?lat=28.6139&lon=77.2090
```

A successful response looks like:
```json
{"configured": true, "connected": true, "message": "Connected and receiving observations"}
```

> ⛔ **Never** paste the API key into any frontend `.tsx`, `.ts`, `.js`, or `.env` file in the `frontend/` folder. Never commit `.env` to git.

---

## Installation

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+ (or use Docker)
- Redis 7+ (or use Docker — falls back to in-memory if unavailable)

### Backend setup

```bash
cd weather-ai-platform/backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp ../.env.example .env
# Edit .env — add your WEATHER_UNION_API_KEY
```

### Frontend setup

```bash
cd weather-ai-platform/frontend
npm install
```

### Database setup

```bash
# Create database
psql -U postgres -c "CREATE USER weather_user WITH PASSWORD 'weather_pass';"
psql -U postgres -c "CREATE DATABASE weather_ai_db OWNER weather_user;"

# Run migration
psql -U weather_user -d weather_ai_db -f ../database/migrations/001_initial_schema.sql
```

---

## Environment Variables

All configuration is via environment variables. Copy `.env.example` to `.env` and fill in values.

| Variable | Description | Required |
|---|---|---|
| `WEATHER_UNION_API_KEY` | Weather Union API key — **server-side only** | Yes (for WU) |
| `DATABASE_URL` | PostgreSQL async connection string | Yes |
| `REDIS_URL` | Redis connection string | No (in-memory fallback) |
| `SECRET_KEY` | JWT signing key (min 32 chars) | Yes |
| `ENVIRONMENT` | `development` or `production` | No |
| `ALLOWED_ORIGINS` | CORS allowed origins (comma-separated) | No |
| `OPEN_METEO_BASE_URL` | Open-Meteo API URL (no key needed) | No |
| `MODEL_ARTIFACT_DIR` | Where trained models are saved | No |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING` | No |

---

## Training

Run the training pipeline with synthetic data:

```bash
cd weather-ai-platform

# Train temperature model (horizon = 6h)
python scripts/train.py

# Train humidity model (horizon = 12h)
python scripts/train.py --target humidity_pct --horizon 12

# Train with more data
python scripts/train.py --target temperature_c --horizon 6 --data-hours 5000

# Custom artifact directory
python scripts/train.py --artifact-dir ./backend/artifacts
```

**In production**, replace `generate_synthetic_data()` in `scripts/train.py` with a database query that fetches real historical NWP hindcasts and observations. The pipeline interface does not change.

### How to verify Weather Union is improving the model

The training script runs an ablation study automatically. After training, compare:

```
RF_baseline   MAE=1.2400
XGB           MAE=0.9800
ANN_two_head  MAE=0.8200
```

Lower MAE = better. If the ANN (which uses WU bias features) outperforms the RF baseline (which has similar but no WU features), Weather Union is contributing. The percent improvement vs baseline is printed for every model.

---

## Running Locally

### Backend

```bash
cd weather-ai-platform/backend
uvicorn app.main:app --reload --port 8000
```

API docs available at: http://localhost:8000/api/docs

### Frontend

```bash
cd weather-ai-platform/frontend
npm run dev
```

Dashboard available at: http://localhost:5173

The Vite dev server proxies `/api` to `http://localhost:8000` automatically.

---

## API Documentation

Interactive docs at **http://localhost:8000/api/docs** (Swagger UI) or **/api/redoc**.

### Key endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | System health + WU status |
| `GET` | `/api/locations/` | List saved locations |
| `GET` | `/api/locations/search/?q=delhi` | Search locations |
| `GET` | `/api/forecast/?lat=28.6&lon=77.2&hours=48` | Forecast by coordinates |
| `GET` | `/api/forecast/{location_id}` | Forecast by saved location |
| `GET` | `/api/forecast/{location_id}/hourly` | 24-hour hourly forecast |
| `GET` | `/api/weather/current?lat=28.6&lon=77.2` | Current conditions |
| `GET` | `/api/weather/weather-union/status` | WU connectivity status |
| `GET` | `/api/models/performance` | All stored model metrics |
| `GET` | `/api/models/weights` | Current dynamic model weights |
| `GET` | `/api/models/comparison` | Model comparison summary |

### Sample forecast response

```json
{
  "location": {"name": "New Delhi", "latitude": 28.6139, "longitude": 77.209},
  "generated_at": "2026-10-01T10:00:00Z",
  "data_sources": {"GFS": true, "ECMWF": true, "JMA": true, "weather_union": true},
  "points": [
    {
      "valid_time": "2026-10-01T11:00:00Z",
      "horizon_hours": 1,
      "temperature_c": 33.2,
      "humidity_pct": 58.0,
      "wind_speed_kmh": 14.3,
      "precipitation_mm": 0.0,
      "uncertainty": {"temperature_sigma": 0.8, "confidence_score": 0.91},
      "gfs":   {"temperature_c": 32.4},
      "ecmwf": {"temperature_c": 32.9},
      "jma":   {"temperature_c": 31.8},
      "weights": {"gfs": 0.284, "ecmwf": 0.502, "jma": 0.214, "ml": 0.0}
    }
  ]
}
```

---

## Testing

```bash
cd weather-ai-platform/backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Run specific test files
pytest tests/test_features.py -v
pytest tests/test_dynamic_weighting.py -v
pytest tests/test_weather_union.py -v
pytest tests/test_api.py -v
pytest tests/test_models.py -v
```

### Test coverage

| File | What's tested |
|---|---|
| `test_features.py` | Leakage prevention, cyclical encoding, lag/rolling safety, WU bias |
| `test_dynamic_weighting.py` | Weights sum to 1, low-error model gets higher weight, fallback |
| `test_weather_union.py` | Observation parsing, missing values, unconfigured client |
| `test_api.py` | All endpoints, API key never in response, validation |
| `test_models.py` | RF/XGB/AdaBoost fit+predict, ANN two-head, blend with None |

---

## Docker Deployment

```bash
cd weather-ai-platform

# 1. Configure environment
cp .env.example .env
# Edit .env — add WEATHER_UNION_API_KEY and change SECRET_KEY

# 2. Build and start all services
docker-compose up --build

# 3. Check status
docker-compose ps
docker-compose logs backend

# 4. Stop
docker-compose down
```

Services:
- **PostgreSQL**: `localhost:5432`
- **Redis**: `localhost:6379`
- **Backend API**: `localhost:8000`
- **Frontend**: `localhost:3000`

---

## Security

- `WEATHER_UNION_API_KEY` lives **only** in `backend/.env` — never in frontend code, never committed to git
- `.env` is listed in `.gitignore`
- The API key header (`x-zomato-api-key`) is set server-side in `WeatherUnionClient` — the frontend never sees it
- All API responses are audited in tests to verify no credential leakage
- The health endpoint only reports `weather_union_configured: true/false` — never the key itself
- Structured logging explicitly redacts fields named `api_key`, `password`, `secret`, `token`
- Non-root Docker user (`appuser`, uid 1001)

---

## Limitations

1. **Training data** — The training script ships with synthetic data. Real accuracy gains require historical NWP hindcast archives and ground-truth observations.

2. **NWP source** — Open-Meteo provides GFS/ECMWF/JMA as convenient proxies, but real operational NWP archives (NOMADS, ECMWF MARS) would give more precise model-run timestamps and longer hindcast periods.

3. **Weather Union coverage** — Station density varies by city. Rural areas may have no nearby stations; the system gracefully degrades to NWP-only in those cases.

4. **Dynamic weights** — Until enough forecast+observation pairs accumulate in the database, the system uses fallback weights (ECMWF 40%, GFS 30%, JMA 20%, ML 10%). Full dynamic weighting activates after ~72 hours of operation.

5. **ANN training time** — Training the PyTorch ANN on CPU can take 5–15 minutes for 3000 hours of data. GPU training is automatically used if CUDA is available.

---

## Future Improvements

- **Real NWP ingestion** — Scheduled job to pull NOMADS/Open-Meteo hindcasts into the database nightly
- **Online learning** — Update model weights as new observations arrive
- **Multi-location training** — A single global model that generalizes across locations
- **Precipitation classification** — Separate rain/no-rain classification head alongside the regression heads
- **Radar data** — Integrate IMD radar data for short-range precipitation nowcasting
- **Alerting** — Push notifications when confidence drops below threshold or WU disconnects
- **Model versioning UI** — Compare training runs in the dashboard
- **ONNX export** — Export the ANN to ONNX for faster CPU inference
