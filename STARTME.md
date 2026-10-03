# Quick Start Guide — WeatherAI Platform

This guide contains everything you need to run the entire project on `localhost` (Windows / macOS / Linux), configure API keys, train models, and test all services.

---

## Table of Contents
1. [Prerequisites](#1-prerequisites)
2. [API Keys & Configuration](#2-api-keys--configuration)
3. [Step-by-Step Localhost Setup](#3-step-by-step-localhost-setup)
   - [Option A: Native Setup (Python + Node.js)](#option-a-native-setup-python--nodejs)
   - [Option B: One-Command Docker Setup](#option-b-one-command-docker-setup)
4. [Training the Machine Learning Models](#4-training-the-machine-learning-models)
5. [Running Tests & Health Checks](#5-running-tests--health-checks)
6. [Common Troubleshooting & Tips](#6-common-troubleshooting--tips)

---

## 1. Prerequisites

Make sure the following tools are installed on your machine:
* **Python**: 3.10+ (Python 3.12 recommended)
* **Node.js**: v18+ or v20+ with `npm`
* **Docker & Docker Compose** *(Optional, if using containerized mode)*
* **Git**

---

## 2. API Keys & Configuration

### The Weather Union API Key
WeatherAI uses **Weather Union** (by Zomato) for real-time hyper-local station weather across Indian cities.

#### Where to get it:
1. Visit [https://www.weatherunion.com/](https://www.weatherunion.com/)
2. Sign up / Log in to the Developer Portal.
3. Request an External API Key (starts with a string like `wu_...` or hex tokens).

#### Where to put the key:
Open `weather-ai-platform/backend/.env` (or copy from `.env.example`):
```env
WEATHER_UNION_API_KEY=your_actual_api_key_here
```

> **IMPORTANT SECURITY NOTE**:
> * **NEVER** put the Weather Union API key into frontend code or `.env` in the `frontend/` folder.
> * The backend acts as a secure server-side proxy (`/api/weather-union/*`), caching responses for 5 minutes and hiding the key completely from the browser.
> * If you do **NOT** have an API key yet, the system **still works completely**! It automatically switches to dynamic NWP multi-model blend mode (using ECMWF, GFS, and JMA forecasts from Open-Meteo, which require no API keys).

---

## 3. Step-by-Step Localhost Setup

### Option A: Native Setup (Python + Node.js)

#### Step 1: Open Terminal & Navigate to Project
```powershell
# Windows PowerShell
cd c:\Users\Sarthak\OneDrive\Desktop\finalnwp\weather-ai-platform
```

#### Step 2: Set up Backend Virtual Environment
```powershell
# Create virtual environment (if not already created)
python -m venv .venv

# Activate virtual environment
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# (If execution policy error occurs, run: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass)

# On macOS/Linux:
# source .venv/bin/activate

# Install backend dependencies
cd backend
pip install -r requirements.txt
```

#### Step 3: Configure Environment Variables
```powershell
# In weather-ai-platform/backend/
# Copy the example environment file:
copy .env.example .env

# Edit .env and verify the settings:
# WEATHER_UNION_API_KEY=your_actual_key_here
# DATABASE_URL=sqlite+aiosqlite:///./weather_ai.db (or your PostgreSQL URL)
```

#### Step 4: Start the Backend FastAPI Server
```powershell
# From weather-ai-platform/backend/
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
* Backend API: [http://localhost:8000](http://localhost:8000)
* Interactive Swagger Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
* Health Check: [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

#### Step 5: Start the Frontend Application
Open a **new terminal tab or window**:
```powershell
cd c:\Users\Sarthak\OneDrive\Desktop\finalnwp\weather-ai-platform\frontend

# Install dependencies (only once)
npm install

# Start Vite development server
npm run dev
```
* Frontend Dashboard: [http://localhost:5173](http://localhost:5173)

---

### Option B: One-Command Docker Setup

If you have Docker Desktop installed, run everything with one command:
```powershell
cd c:\Users\Sarthak\OneDrive\Desktop\finalnwp\weather-ai-platform

# Build and launch PostgreSQL, Redis, FastAPI Backend, and React Frontend
docker-compose up --build
```
* Frontend: [http://localhost:3000](http://localhost:3000) (or 5173)
* Backend: [http://localhost:8000](http://localhost:8000)
* Interactive Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 4. Training the Machine Learning Models

The models are pre-trained on 1-year factual ERA5 + NWP data for Delhi. You can retrain or train for any city at any time:

### Train Single City (1 Year of Factual Data)
```powershell
cd c:\Users\Sarthak\OneDrive\Desktop\finalnwp\weather-ai-platform

# Train for Delhi (365 days factual data)
python scripts/fetch_and_train.py --city delhi --days 365 --save-csv

# Train for Jaipur, Bengaluru, Mumbai, Chennai, etc.
python scripts/fetch_and_train.py --city jaipur --days 365 --save-csv
python scripts/fetch_and_train.py --city bengaluru --days 365 --save-csv
python scripts/fetch_and_train.py --city mumbai --days 365 --save-csv
python scripts/fetch_and_train.py --city chennai --days 365 --save-csv
python scripts/fetch_and_train.py --city hyderabad --days 365 --save-csv
```

### Train All 14 Indian Cities in Batch
```powershell
python scripts/train_multi_city.py --days 365
```
This fetches 1 year of real historical data for Jaipur, Bengaluru, Hyderabad, Mumbai, Chennai, Delhi, Kolkata, Pune, Ahmedabad, Lucknow, Chandigarh, Bhopal, Patna, and Kochi, saves their datasets in `data/`, trains all models, and saves artifacts in `backend/artifacts/<city>/`.

---

## 5. Running Tests & Health Checks

To run the automated test suite:
```powershell
cd c:\Users\Sarthak\OneDrive\Desktop\finalnwp\weather-ai-platform
python -m pytest
```

Check backend health endpoint:
```powershell
curl http://localhost:8000/api/health
```
Expected response:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "weather_union_configured": true,
  "ml_models_loaded": true,
  "database": "connected"
}
```

---

## 6. Common Troubleshooting & Tips

| Problem | Cause | Solution |
| :--- | :--- | :--- |
| `WinError 1225: The remote computer refused the network connection` | PostgreSQL service is not started on `localhost:5432` | In `backend/.env`, set `DATABASE_URL=sqlite+aiosqlite:///./weather_ai.db` to use local SQLite instead, or start Docker container `docker-compose up -d db`. |
| `Cannot find module` in frontend | Node dependencies not installed | Run `npm install` inside `frontend/`. |
| `Weather Union key not configured` warning | Key is still set to placeholder in `.env` | Add your free API key from weatherunion.com to `backend/.env`. System will work in fallback mode in the meantime. |
| Model artifacts missing | Models haven't been trained yet | Run `python scripts/fetch_and_train.py --city delhi --days 365`. |
