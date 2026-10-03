# Production Deployment Guide — WeatherAI Platform

This guide explains **where** and **how** to deploy every tier of the WeatherAI Platform:
* **Frontend** (React + Vite + TypeScript)
* **Backend** (FastAPI + PyTorch + Scikit-learn + XGBoost)
* **Database & Cache** (PostgreSQL + Redis)
* **Docker & Virtual Environments** (Best practices)

---

## Table of Contents
1. [Architecture & Component Breakdown](#1-architecture--component-breakdown)
2. [Virtual Environment (.venv) vs Docker in Production](#2-venv-vs-docker-in-production)
3. [Recommended Free / Low-Cost Cloud Deployment (PaaS)](#3-recommended-free--low-cost-cloud-deployment-paas)
   - [A. Database: Supabase or Neon (Free Managed Postgres)](#a-database-supabase-or-neon-free-managed-postgres)
   - [B. Backend: Render or Railway](#b-backend-render-or-railway)
   - [C. Frontend: Vercel or Netlify](#c-frontend-vercel-or-netlify)
4. [Single-Server VPS Deployment (Docker Compose)](#4-single-server-vps-deployment-docker-compose)
5. [Enterprise Cloud Deployment (AWS / GCP)](#5-enterprise-cloud-deployment-aws--gcp)
6. [Post-Deployment Health Verification](#6-post-deployment-health-verification)

---

## 1. Architecture & Component Breakdown

```
[Users / Browsers]
        │
        ▼ (HTTPS)
┌─────────────────────────────────┐
│   Frontend (React SPA)          │  Deployed to: Vercel / Netlify / Cloudflare Pages
│   Static HTML + JS + CSS Bundle │
└───────────────┬─────────────────┘
                │ (API Calls: /api/*)
                ▼
┌─────────────────────────────────┐
│   Backend (FastAPI + ML Engine) │  Deployed to: Render / Railway / AWS EC2 / Docker
│   Runs Uvicorn + PyTorch/XGBoost│
└───────┬─────────────────┬───────┘
        │                 │
        ▼                 ▼
┌──────────────┐   ┌──────────────┐
│  PostgreSQL  │   │  Redis Cache │  Deployed to: Supabase / Neon / AWS RDS / Docker
│  (Database)  │   │  (5m TTL)    │
└──────────────┘   └──────────────┘
```

---

## 2. `.venv` vs Docker in Production

> **CRITICAL RULE**:
> **NEVER upload or copy your local `.venv` directory to production servers!**
> A `.venv` folder contains compiled binaries, dynamic link libraries (DLLs/so), and hardcoded local file paths for your local Windows machine. 

### How environments are handled in production:
* **Option A (Containerized)**: Use **Docker** (`Dockerfile`). Docker creates a clean, isolated Linux container and runs `pip install -r requirements.txt` during the image build.
* **Option B (Native Cloud PaaS)**: Platforms like Render/Railway automatically read `requirements.txt` and build a fresh virtual environment in their Linux runtime for you.

---

## 3. Recommended Free / Low-Cost Cloud Deployment (PaaS)

This is the fastest, zero-maintenance architecture.

### A. Database: Supabase or Neon (Free Managed Postgres)
1. Sign up at [https://supabase.com/](https://supabase.com/) or [https://neon.tech/](https://neon.tech/).
2. Create a new PostgreSQL project named `weather-ai-db`.
3. Go to **Settings** → **Database** → **Connection String** (choose URI mode).
4. Copy the connection string. It will look like:
   ```
   postgresql+asyncpg://postgres:[PASSWORD]@[HOST]:5432/postgres
   ```
5. *(Optional)* Run initial migrations from `database/migrations/001_initial_schema.sql` via Supabase SQL Editor.

---

### B. Backend: Render or Railway

#### Deploying on Render (Free Tier):
1. Sign up at [https://render.com/](https://render.com/) and connect your GitHub repository.
2. Click **New +** → **Web Service**.
3. Select your `weather-ai-platform` repository.
4. Set the following build settings:
   * **Name**: `weather-ai-backend`
   * **Region**: Singapore or Frankfurt (closest to India)
   * **Root Directory**: `backend`
   * **Runtime**: `Python 3`
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Under **Environment Variables**, add:
   * `WEATHER_UNION_API_KEY` = your Weather Union key
   * `DATABASE_URL` = your Supabase connection string
   * `ALLOWED_ORIGINS` = `https://your-frontend.vercel.app,http://localhost:5173`
   * `MODEL_ARTIFACT_DIR` = `./artifacts`
6. Click **Create Web Service**. Render will deploy your API and provide a URL like `https://weather-ai-backend.onrender.com`.

---

### C. Frontend: Vercel or Netlify

#### Deploying on Vercel (Free & Instant CDN):
1. Sign up at [https://vercel.com/](https://vercel.com/) and click **Add New** → **Project**.
2. Import your GitHub repository.
3. Configure the Project:
   * **Framework Preset**: `Vite`
   * **Root Directory**: Click edit and select `frontend`
   * **Build Command**: `npm run build`
   * **Output Directory**: `dist`
4. Under **Environment Variables**, add:
   * `VITE_API_URL` = `https://weather-ai-backend.onrender.com` (your backend URL)
5. Click **Deploy**. Vercel will build and assign you a global HTTPS domain like `https://weather-ai-platform.vercel.app`.

---

## 4. Single-Server VPS Deployment (Docker Compose)

If you have a Linux VPS (DigitalOcean Droplet, AWS EC2 Ubuntu instance, Hetzner, or Linode):

### Step 1: Install Docker & Docker Compose on VPS
```bash
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo systemctl enable --now docker
```

### Step 2: Clone Your Repository
```bash
git clone https://github.com/YOUR_USERNAME/weather-ai-platform.git
cd weather-ai-platform
```

### Step 3: Configure Environment Variables
```bash
cp .env.example .env
nano .env   # Enter your WEATHER_UNION_API_KEY and secure database passwords
```

### Step 4: Launch the Full Stack
```bash
docker compose up -d --build
```
This runs:
* PostgreSQL on port 5432
* Redis on port 6379
* FastAPI backend on port 8000
* React frontend on port 80/3000

### Step 5: Configure Domain & Free SSL (Let's Encrypt / Certbot)
```bash
sudo apt install -y certbot python3-certbot-nginx nginx
# Point your DNS A record to your VPS IP, then run:
sudo certbot --nginx -d weather.yourdomain.com
```

---

## 5. Enterprise Cloud Deployment (AWS / GCP)

For enterprise high-availability:

| Service | AWS Solution | GCP Solution |
| :--- | :--- | :--- |
| **Frontend** | AWS S3 Bucket + CloudFront CDN | GCP Cloud Storage + Cloud CDN |
| **Backend** | AWS ECS Fargate (Docker) + ALB | GCP Cloud Run (Serverless Container) |
| **Database** | AWS RDS PostgreSQL (Multi-AZ) | GCP Cloud SQL for PostgreSQL |
| **Cache** | AWS ElastiCache (Redis) | GCP Memorystore for Redis |
| **Secrets** | AWS Secrets Manager | GCP Secret Manager |

---

## 6. Post-Deployment Health Verification

Once your deployment is live, verify the services:

1. **Backend Health Check**:
   ```bash
   curl https://your-backend-url/api/health
   ```
   Should return:
   ```json
   {
     "status": "ok",
     "weather_union_configured": true,
     "ml_models_loaded": true,
     "database": "connected"
   }
   ```

2. **Frontend Test**:
   Open `https://your-frontend-url` in your browser:
   * Verify the forecast chart renders predictions and confidence intervals.
   * Verify the city selector switches coordinates and triggers forecasts.
   * Open Developer Tools (F12) → Console to confirm no CORS errors.
