# 🚀 Step-by-Step Deployment Guide: Render (Backend) + Vercel (Frontend)

This guide walks you through deploying the **Weather AI Platform** to the cloud:
- **Backend API & ML Engine**: Deployed on [Render](https://render.com) (`https://weather-ai-backend.onrender.com`)
- **Frontend SPA UI**: Deployed on [Vercel](https://vercel.com) (`https://weather-ai-platform.vercel.app`)

---

## 1. Push Code to GitHub

Make sure your latest code and trained model artifacts are committed and pushed to GitHub:

```bash
git add .
git commit -m "Deploy: Updated synoptic weather AI platform with 14-city verification leaderboard"
git push origin main
```

---

## 2. Deploy Backend on Render

1. Go to [https://dashboard.render.com](https://dashboard.render.com) and sign in.
2. Click **New +** → **Blueprint** (or **Web Service**).
   - If using **Blueprint**: Render will automatically detect `render.yaml` in your repository!
   - If using **Web Service** manually, set these parameters:
     - **Name**: `weather-ai-backend`
     - **Root Directory**: `backend`
     - **Environment**: `Python 3`
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Add **Environment Variables**:
   - `ENVIRONMENT` = `production`
   - `MODEL_ARTIFACT_DIR` = `./artifacts`
   - `ALLOWED_ORIGINS` = `*`
   - *(Optional)* `WEATHER_UNION_API_KEY` = your Weather Union API key
4. Click **Deploy Web Service**.
5. Once deployed, Render will generate your backend URL:
   `https://weather-ai-backend.onrender.com`

---

## 3. Deploy Frontend on Vercel

1. Go to [https://vercel.com/new](https://vercel.com/new) and import your GitHub repository.
2. Configure your project:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Select `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
3. Add **Environment Variables**:
   - **Name**: `VITE_API_URL`
   - **Value**: `https://weather-ai-backend.onrender.com` (Use your actual Render URL from Step 2)
4. Click **Deploy**.
5. Vercel will build and launch your global live URL:
   `https://weather-ai-platform.vercel.app`

---

## 4. Post-Deployment Health Verification

After both services are live:
- Visit `https://weather-ai-backend.onrender.com/api/health` to verify backend status.
- Visit `https://weather-ai-backend.onrender.com/api/models/verification` to verify the 14-City Synoptic verification leaderboard payload.
- Open your live Vercel URL `https://weather-ai-platform.vercel.app` in your browser!
