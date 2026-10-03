# GitHub Upload Guide — WeatherAI Platform

This step-by-step guide explains how to initialize Git, ensure sensitive keys and cache files are safely ignored, and push your complete **WeatherAI Platform** repository to GitHub.

---

## Table of Contents
1. [Pre-Upload Checklist (Security & Cleanliness)](#1-pre-upload-checklist)
2. [Step-by-Step GitHub Upload](#2-step-by-step-github-upload)
3. [Handling Large ML Artifacts (Git LFS)](#3-handling-large-ml-artifacts-git-lfs)
4. [GitHub Authentication (Tokens & SSH)](#4-github-authentication)
5. [Ongoing Git Workflow](#5-ongoing-git-workflow)

---

## 1. Pre-Upload Checklist

### ⚠️ Never Commit Secrets or Virtual Environments
Before running `git add`, verify that `.gitignore` contains the following:
* `.env` (contains your private Weather Union API key and database passwords)
* `.venv/` and `env/` (Python virtual environment folders)
* `node_modules/` (Node packages)
* `__pycache__/` and `*.pyc`
* `.pytest_cache/`
* `*.db` (SQLite local database)

> **Pro Tip**: Your project already includes a production-ready `.gitignore` in `weather-ai-platform/.gitignore`. Always commit `.env.example` so other collaborators know what configuration keys exist without exposing real credentials.

---

## 2. Step-by-Step GitHub Upload

### Step 1: Open PowerShell / Terminal in the Project Directory
```powershell
cd c:\Users\Sarthak\OneDrive\Desktop\finalnwp\weather-ai-platform
```

### Step 2: Initialize Git Repository
If Git is not yet initialized in this folder:
```powershell
git init
```

### Step 3: Check Git Status
```powershell
git status
```
Verify that `.env`, `.venv`, and `node_modules` are **NOT** listed in untracked files.

### Step 4: Stage All Files
```powershell
git add .
```

### Step 5: Create Initial Commit
```powershell
git commit -m "feat: complete WeatherAI platform with multi-model ML and real data pipeline"
```

### Step 6: Create a New Repository on GitHub
1. Open [https://github.com/new](https://github.com/new) in your browser.
2. Enter Repository name (e.g. `weather-ai-platform` or `finalnwp`).
3. Set visibility to **Public** or **Private**.
4. **DO NOT** check "Add a README file", ".gitignore", or "license" (we already have them locally).
5. Click **Create repository**.

### Step 7: Link Your Local Repository to GitHub
Copy the repository URL from GitHub and run:
```powershell
# Rename default branch to main
git branch -M main

# Add GitHub as the remote origin (replace YOUR_USERNAME and YOUR_REPO)
git remote add origin https://github.com/YOUR_USERNAME/weather-ai-platform.git
```

### Step 8: Push to GitHub
```powershell
git push -u origin main
```

---

## 3. Handling Large ML Artifacts (Git LFS)

GitHub enforces a maximum file size limit of **100 MB** per file.
In this project:
* `neural_network.pt` is ~395 KB (safe)
* `xgboost.joblib` is ~1.8 MB (safe)
* `adaboost.joblib` is ~515 KB (safe)
* `random_forest.joblib` is ~40 MB (fits standard GitHub push, but recommended for Git LFS if tree depth grows)

### Optional: Enable Git LFS (Large File Storage)
If you wish to store trained model weights with Git LFS:
```powershell
# Install git-lfs (run once)
git lfs install

# Track model binaries
git lfs track "*.joblib"
git lfs track "*.pt"

# Commit gitattributes
git add .gitattributes
git commit -m "chore: track ML model weights with Git LFS"
git push
```

---

## 4. GitHub Authentication

When you run `git push`, GitHub will prompt for authentication:

### Method 1: GitHub Personal Access Token (PAT)
GitHub no longer accepts your account password for Git operations over HTTPS.
1. Go to **GitHub** → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**.
2. Click **Generate new token (classic)**.
3. Name it (e.g. `Laptop-Dev`) and check the `repo` scope.
4. Copy the token (starts with `ghp_...`).
5. When prompted in terminal:
   * **Username**: Your GitHub username
   * **Password**: Paste your Personal Access Token (`ghp_...`).

### Method 2: GitHub Desktop (GUI)
1. Open [GitHub Desktop](https://desktop.github.com/).
2. Click **File** → **Add Local Repository** → select `weather-ai-platform`.
3. Click **Publish repository** to GitHub.

---

## 5. Ongoing Git Workflow

Whenever you make new changes or train new models:
```powershell
# 1. View changes
git status

# 2. Stage modified files
git add .

# 3. Commit with a clear message
git commit -m "docs: update deployment and multi-city training scripts"

# 4. Push updates to GitHub
git push
```
