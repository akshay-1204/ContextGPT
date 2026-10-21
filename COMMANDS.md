# ContextGPT — Commands & Execution Guide

This document contains all commands to set up, run, test, and manage ContextGPT.

---

## 🚀 Quick Start (Running the Application)

Run these in two separate terminal windows inside the `ContextGPT` directory:

### Terminal 1 — Backend (FastAPI API on Port 8000)
```powershell
# 1. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Start the FastAPI backend with auto-reload
uvicorn backend.app.main:app --reload --port 8000
```
> **Backend URL:** [http://localhost:8000](http://localhost:8000)  
> **Swagger API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)  
> **Health Probe:** [http://localhost:8000/health/ready](http://localhost:8000/health/ready)  

---

### Terminal 2 — Frontend (Streamlit Dashboard on Port 8501)
```powershell
# 1. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Start Streamlit UI
streamlit run frontend/app.py --server.port 8501
```
> **Frontend Web UI:** [http://localhost:8501](http://localhost:8501)  

---

## 🛠️ One-Click Scripts (Windows)

You can run the helper scripts directly from PowerShell or double-click them in Windows Explorer:

- **Run Backend:**
  ```powershell
  .\run_backend.ps1
  # OR (CMD / double-click):
  .\run_backend.bat
  ```

- **Run Frontend:**
  ```powershell
  .\run_frontend.ps1
  # OR (CMD / double-click):
  .\run_frontend.bat
  ```

---

## 🐘 Database Commands (PostgreSQL)

### 1. Create the Database (Run Once in PostgreSQL)
```powershell
psql -U postgres -c "CREATE DATABASE contextgpt;"
```

### 2. Initialize / Create All SQLAlchemy Tables
```powershell
.\.venv\Scripts\python.exe -c "from backend.app.db.base import Base; from backend.app.db.session import engine; import backend.app.db.models; Base.metadata.create_all(bind=engine); print('SUCCESS: Tables created!')"
```

### 3. Check Existing Tables
```powershell
.\.venv\Scripts\python.exe -c "from sqlalchemy import inspect; from backend.app.db.session import engine; print(inspect(engine).get_table_names())"
```

---

## 🧪 Testing Commands

### Run Full Test Suite (All 21 Tests)
```powershell
.\.venv\Scripts\pytest.exe -v
```

### Run Specific Test Modules
```powershell
# Authentication tests
.\.venv\Scripts\pytest.exe -v tests\test_auth.py

# Document ingestion & loaders tests
.\.venv\Scripts\pytest.exe -v tests\test_sources.py

# Summarization & loader prompt tests
.\.venv\Scripts\pytest.exe -v tests\test_summaries.py

# RAG & Vector similarity tests
.\.venv\Scripts\pytest.exe -v tests\test_rag.py
```

---

## 📦 Dependency Commands

```powershell
# Install all required packages
pip install -r requirements.txt
```

---

## 🐳 Docker Compose (All-in-One Containerized)

To start PostgreSQL, FastAPI Backend, and Streamlit Frontend together:
```powershell
# Build and start all 3 services
docker compose up --build

# Stop all services
docker compose down

# View container logs
docker compose logs -f
```
