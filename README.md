# ⚡ ContextGPT

> **Tagline:** *Understand more. Ask anything.*

ContextGPT is an enterprise-grade, multi-source AI summarization and question-answering platform built with **FastAPI**, **SQLAlchemy 2.x**, **PostgreSQL / pgvector**, **LangChain**, and **Streamlit**.

It allows users to ingest documents (PDFs, Word documents, Excel sheets, text files, CSVs, JSON, XML), public webpages, REST APIs, and authorized read-only databases, produce tailored AI summaries, and ask questions grounded strictly in retrieved source context through an end-to-end Retrieval-Augmented Generation (RAG) pipeline.

---

## 📑 Table of Contents

- [1. Architecture and Pipeline Workflow](#1-architecture-and-pipeline-workflow)
- [2. Supported Knowledge Sources](#2-supported-knowledge-sources)
- [3. Technology Stack & Why Each is Used](#3-technology-stack--why-each-is-used)
- [4. Complete Project Structure](#4-complete-project-structure)
- [5. Prerequisites](#5-prerequisites)
- [6. Step-by-Step Local Setup Guide](#6-step-by-step-local-setup-guide)
  - [A. Clone & Navigate](#a-clone--navigate)
  - [B. Virtual Environment Setup](#b-virtual-environment-setup)
  - [C. Environment Configuration (.env)](#c-environment-configuration-env)
  - [D. Database Migrations (Alembic)](#d-database-migrations-alembic)
  - [E. Running FastAPI Backend](#e-running-fastapi-backend)
  - [F. Running Streamlit Frontend](#f-running-streamlit-frontend)
- [7. Docker & Docker Compose Deployment](#7-docker--docker-compose-deployment)
- [8. Automated Testing Suite](#8-automated-testing-suite)
- [9. End-to-End Walkthrough Example](#9-end-to-end-walkthrough-example)
- [10. API Endpoint Reference](#10-api-endpoint-reference)
- [11. Security Architecture](#11-security-architecture)
- [12. Troubleshooting & FAQ](#12-troubleshooting--faq)
- [13. Current Limitations & Roadmap](#13-current-limitations--roadmap)

---

## 1. Architecture and Pipeline Workflow

```mermaid
flowchart TD
    subgraph ClientLayer ["Client & Presentation Layer"]
        UI["Streamlit Frontend (Port 8501)"]
        APIClient["Centralized API Client (frontend/api_client.py)"]
        UI --> APIClient
    end

    subgraph APILayer ["FastAPI Application Gateway (Port 8000)"]
        FastAPI["FastAPI App (backend/app/main.py)"]
        AuthMiddleware["JWT & Argon2 Auth Security (backend/app/core/security.py)"]
        APIClient -->|HTTP / JSON / Bearer JWT| FastAPI
        FastAPI --> AuthMiddleware
    end

    subgraph ServiceLayer ["ContextGPT Business Logic"]
        SourceSvc["Source Ingestion Service"]
        LoaderReg["Loader Registry & SSRF Validator"]
        SummarySvc["Summarization Engine (Direct & Map-Reduce)"]
        EmbedSvc["Embedding & Text Splitter Service"]
        Retriever["Retrieval & Cosine Similarity Service"]
        ChatSvc["Grounded RAG Chat Service"]

        AuthMiddleware --> SourceSvc
        AuthMiddleware --> SummarySvc
        AuthMiddleware --> ChatSvc

        SourceSvc --> LoaderReg
        SourceSvc --> EmbedSvc
        ChatSvc --> Retriever
    end

    subgraph ExternalServices ["External AI & Network Resources"]
        OpenAI_LLM["OpenAI GPT Models (gpt-4o-mini / gpt-4o)"]
        OpenAI_Embed["OpenAI text-embedding-3-small"]
        ExtWeb["External Webpages & REST APIs"]
        LoaderReg --> ExtWeb
        SummarySvc --> OpenAI_LLM
        EmbedSvc --> OpenAI_Embed
        ChatSvc --> OpenAI_LLM
    end

    subgraph StorageLayer ["Persistence Layer"]
        DB[(PostgreSQL 16 + pgvector)]
        Tables["users, sources, summaries, refresh_tokens, conversations, messages, document_chunks"]
        DB --- Tables
    end

    SourceSvc --> DB
    EmbedSvc --> DB
    SummarySvc --> DB
    Retriever --> DB
    ChatSvc --> DB
```

---

## 2. Supported Knowledge Sources

| Source Type | Extractor Module | Features & Protections |
| :--- | :--- | :--- |
| **PDF Documents** | `backend/app/loaders/pdf_loader.py` | Extracts text and page metadata via PyPDF / LangChain Community. Detects encrypted PDFs, empty PDFs, and informs users when PDFs are scanned images lacking OCR. |
| **Plain Text & Markdown** | `backend/app/loaders/text_loader.py` | Multi-encoding fallback (`utf-8`, `utf-8-sig`, `latin-1`, `cp1252`) and whitespace validation via LangChain Community TextLoader. |
| **Webpages (HTML)** | `backend/app/loaders/webpage_loader.py` | Extracts main article body and titles via BeautifulSoup. Protected by **anti-SSRF validation** blocking localhost, private subnets (RFC 1918), and cloud metadata IP (`169.254.169.254`). |
| **REST APIs (JSON)** | `backend/app/loaders/api_loader.py` | Queries external endpoints safely via HTTP GET, parses structured JSON, respects timeouts, and redacts sensitive authorization tokens from logs. |
| **Stock Market API** | `backend/app/loaders/stock_loader.py` | Custom LangChain BaseLoader connecting to Alpha Vantage daily time-series data, producing structured daily stock records. |
| **Read-Only Database** | `backend/app/loaders/database_loader.py` | Connects to PostgreSQL to run safe `SELECT` queries with keyword allowlisting to prevent mutation. MySQL is explicitly blocked for security. Credentials masked in stored metadata. |
| **Images (Vision)** | `backend/app/loaders/image_loader.py` | Analyzes PNG, JPEG, and WEBP formats using OpenAI Vision (`gpt-4o`). Validates dimensions and explains vision requirements when offline. |
| **Office Documents** | `backend/app/loaders/office_loader.py` | Extracts text and tables from Word (`.docx`) and workbooks/sheets from Excel (`.xlsx`). |
| **CSV Tabular Files** | `backend/app/loaders/csv_loader.py` | Parses tabular comma/semicolon/tab-separated files into formatted Markdown tables via LangChain Community CSVLoader. |
| **JSON & XML** | `backend/app/loaders/json_xml_loader.py` | Parses structured configuration, objects, and XML elements into readable indented text. |
| **YouTube Transcripts** | `backend/app/loaders/youtube_loader.py` | Ingests official video captions and transcripts via `youtube-transcript-api 1.2+` across watch, short (youtu.be), and embed URLs without scraping. |

---

## 3. Technology Stack & Why Each is Used

| Technology | Role | Rationale |
| :--- | :--- | :--- |
| **Python 3.12 / 3.10+** | Core Programming Language | High performance, modern typing, and universal support across data/AI ecosystems. |
| **FastAPI** | Backend Web Framework | High-speed ASGI performance, automatic OpenAPI / Swagger generation, and strict Pydantic validation. |
| **Uvicorn** | ASGI Web Server | Lightning-fast asynchronous server for production Python deployments. |
| **SQLAlchemy 2.x** | Object Relational Mapper (ORM) | Industry standard type-safe database queries, relationship management, and cascading deletions. |
| **Psycopg 3** | PostgreSQL Driver | Native modern async/sync driver with connection pooling and binary PostgreSQL protocol support. |
| **PostgreSQL 16 + pgvector** | Primary Relational & Vector Database | Full ACID compliance, robust user/asset persistence, and native vector storage via pgvector with Psycopg 3. |
| **Alembic** | Database Migrations | Version-controlled database schema migrations tracking all model tables and indexes. |
| **LangChain & Community** | AI Document Orchestration | Clean document loaders (`BaseLoader`, `PyPDFLoader`, `CSVLoader`, `TextLoader`), token-bounded chunking, and PromptTemplates. |
| **OpenAI / NVIDIA NIM** | LLMs and Embeddings | High intelligence summarization and text embeddings (`gpt-4o-mini`, `text-embedding-3-small`, or NVIDIA NIM models via `OPENAI_BASE_URL`). |
| **pwdlib (Argon2)** | Password Hashing | State-of-the-art memory-hard password hashing recommended by OWASP. |
| **PyJWT** | Authentication Tokens | Stateless, cryptographically signed JWT access tokens with individual `jti` entropy and revocable refresh tokens. |
| **Streamlit** | Frontend User Interface | Reactive, rapid Python-based UI with interactive components, real-time metrics, and custom CSS styling. |
| **Docker & Compose** | Containerized Deployment | Consistent multi-container orchestration for backend, frontend, and PostgreSQL (`pgvector/pgvector:pg16`). |
| **Pytest** | Testing Framework | Comprehensive automated unit, integration, and security testing. |

---

## 4. Complete Project Structure

```text
ContextGPT/
│
├── frontend/
│   ├── app.py                          # Streamlit main entrypoint & routing
│   ├── api_client.py                   # Centralized HTTP API client with token auto-refresh
│   ├── components/
│   │   ├── navigation.py               # Branded sidebar navigation & auth status
│   │   ├── source_input.py             # 4-tab knowledge source ingestion component
│   │   ├── summary_view.py             # Summary display card & copy actions
│   │   └── chat_view.py                # Conversational bubbles & verifiable citation expanders
│   ├── pages/
│   │   ├── login.py                    # User authentication screen
│   │   ├── register.py                 # User registration screen
│   │   ├── dashboard.py                # Live metrics, recent sources, and quick actions
│   │   ├── sources.py                  # Source catalog, status tracking, and deletion
│   │   ├── summaries.py                # Multi-style summarization generator & view
│   │   ├── chat.py                     # Context-grounded RAG chat interface
│   │   └── history.py                  # Searchable archives & thread deletion
│   └── utils/
│       ├── session.py                  # Streamlit session-state manager
│       └── formatting.py               # Timestamps & byte-size display helpers
│
├── backend/
│   └── app/
│       ├── __init__.py
│       ├── main.py                     # FastAPI application factory, lifespan & CORS
│       ├── core/
│       │   ├── config.py               # Pydantic Settings & environment variables
│       │   ├── security.py             # Argon2 hashing, JWT signing, and token rotation
│       │   └── logging.py              # Centralized logging configuration
│       ├── api/
│       │   ├── dependencies.py         # DB session & JWT Bearer user injection
│       │   └── routes/
│       │       ├── auth.py             # Register, login, refresh, logout, /me
│       │       ├── users.py            # User profile routes
│       │       ├── sources.py          # Upload, webpage, API, database sources
│       │       ├── summaries.py        # Summarization creation & inspection
│       │       ├── chat.py             # RAG query execution & conversation threads
│       │       └── health.py           # Liveness (/health) & Readiness (/health/ready)
│       ├── db/
│       │   ├── session.py              # Engine creation, connection pooling, and get_db
│       │   ├── base.py                 # DeclarativeBase class
│       │   └── models/
│       │       ├── __init__.py         # Model package exports
│       │       ├── user.py             # User account model
│       │       ├── source.py           # Ingested knowledge sources
│       │       ├── summary.py          # Stored summaries & token metrics
│       │       ├── refresh_token.py    # Revocable refresh token store
│       │       ├── conversation.py     # Conversation and Message models
│       │       └── chunk.py            # DocumentChunk & vector embeddings
│       ├── schemas/
│       │   ├── user.py                 # Pydantic auth schemas
│       │   ├── source.py               # Source input/output schemas
│       │   ├── summary.py              # Summarization schemas
│       │   └── chat.py                 # RAG & conversation schemas
│       ├── services/
│       │   ├── auth_service.py         # User registration & token rotation logic
│       │   ├── source_service.py       # Ingestion orchestration & file validation
│       │   ├── embedding_service.py    # Text chunking & vector generation
│       │   ├── retrieval_service.py    # Similarity retrieval & bounded context
│       │   ├── summary_service.py      # Direct & hierarchical Map-Reduce summarizer
│       │   └── chat_service.py         # Conversational RAG pipeline
│       ├── loaders/
│       │   ├── base.py                 # BaseSourceLoader & SSRF validator
│       │   ├── text_loader.py          # Plain text & markdown loader
│       │   ├── pdf_loader.py           # PDF extractor
│       │   ├── webpage_loader.py       # Webpage HTML extractor
│       │   ├── api_loader.py           # REST API JSON extractor
│       │   ├── database_loader.py      # Read-only database query loader
│       │   ├── image_loader.py         # Vision-based image extractor
│       │   ├── csv_loader.py           # CSV tabular loader
│       │   ├── office_loader.py        # Word (.docx) & Excel (.xlsx) loader
│       │   ├── json_xml_loader.py      # JSON and XML format loader
│       │   ├── youtube_loader.py       # YouTube transcript loader
│       │   └── loader_registry.py      # Loader registry pattern
│       └── prompts/
│           ├── summarization.py        # Prompts for short, detailed, and map-reduce
│           └── rag.py                  # Grounded RAG prompts & injection guards
│
├── alembic/
│   ├── versions/
│   │   └── 001_initial_schema.py       # Initial migration: all tables & foreign keys
│   ├── env.py                          # Alembic runtime config
│   └── script.py.mako                  # Migration template
│
├── tests/
│   ├── conftest.py                     # Isolated test fixtures & TestClient
│   ├── test_health.py                  # Liveness and readiness tests
│   ├── test_auth.py                    # Registration, Argon2 hashing, and token rotation
│   ├── test_sources.py                 # Source ingestion & anti-SSRF tests
│   ├── test_summaries.py               # Multi-style summarization tests
│   └── test_rag.py                     # Chunking, vector search, citations, and isolation
│
├── .env.example                        # Template environment variables
├── .gitignore                          # Git tracking exclusions
├── .dockerignore                       # Docker build exclusions
├── requirements.txt                    # Pinned, tested dependency requirements
├── pyproject.toml                      # Build tool, ruff, and pytest configuration
├── alembic.ini                         # Alembic database migration settings
├── Dockerfile.backend                  # Slim containerfile for FastAPI
├── Dockerfile.frontend                 # Containerfile for Streamlit
├── compose.yaml                        # Multi-service Docker Compose specification
└── README.md                           # Comprehensive documentation
```

---

## 5. Prerequisites

Before installing ContextGPT, ensure your workstation has:
1. **Python 3.10+** (Tested on Python 3.12).
2. **Git** for version control.
3. *(Optional)* **Docker & Docker Compose** for running containerized PostgreSQL and microservices.
4. *(Optional)* An **OpenAI API Key** if you wish to run live generative LLM synthesis. ContextGPT includes full offline simulation mode so you can run the app and all tests without paid API keys.

---

## 6. Step-by-Step Local Setup Guide

### A. Clone & Navigate
```bash
git clone <your-repository-url>
cd ContextGPT
```

### B. Virtual Environment Setup

**On Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**On macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### C. Environment Configuration (.env)

Copy `.env.example` to `.env`:
```bash
# On Windows PowerShell
Copy-Item .env.example .env

# On macOS / Linux
cp .env.example .env
```

Open `.env` in your text editor and configure your database and API settings:
```dotenv
APP_NAME=ContextGPT
APP_ENV=development
LOG_LEVEL=INFO

# AI & LLM Model Configuration (Supports OpenAI & NVIDIA NIM)
# For OpenAI:
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small

# For NVIDIA NIM (optional alternative):
# OPENAI_BASE_URL=https://integrate.api.nvidia.com/v1
# OPENAI_API_KEY=nvapi-...
# OPENAI_MODEL=nvidia/nemotron-3.5-super-vl-120b-a12b

# Primary PostgreSQL Database (e.g., created via DBeaver or Docker on port 5432):
POSTGRES_DB=contextgpt
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_postgres_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
DATABASE_URL=postgresql+psycopg://postgres:your_postgres_password@localhost:5432/contextgpt

# Authentication Secret (generate with: openssl rand -hex 32):
JWT_SECRET_KEY=change-this-to-a-very-secure-random-secret-key-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# Network settings:
API_BASE_URL=http://localhost:8000
BACKEND_CORS_ORIGINS=["http://localhost:8501","http://127.0.0.1:8501"]
```

> **Setting up the Database in DBeaver:**
> 1. In **DBeaver**, connect to your local PostgreSQL server (`localhost:5432`).
> 2. Right-click **Databases** -> **Create New Database**, name it `contextgpt`, and click **OK**.
> 3. Ensure `DATABASE_URL` in your `.env` matches your username and password.

### D. Database Migrations (Alembic)

Run the database migration to create all tables:
```bash
# Windows
.\.venv\Scripts\alembic upgrade head

# Linux / macOS
alembic upgrade head
```

You can inspect current migration status at any time:
```bash
alembic current
```

### E. Running FastAPI Backend

Start the Uvicorn server:
```bash
# Windows
.\.venv\Scripts\uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

# Linux / macOS
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Once started, explore the interactive documentation:
- **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Probe:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### F. Running Streamlit Frontend

Open a second terminal window (with `.venv` activated) and run:
```bash
# Windows
.\.venv\Scripts\streamlit run frontend/app.py

# Linux / macOS
streamlit run frontend/app.py
```

The Streamlit UI will open in your browser at:
- **URL:** [http://localhost:8501](http://localhost:8501)

---

## 7. Docker & Docker Compose Deployment

ContextGPT comes ready with production-optimized Dockerfiles and `compose.yaml` orchestrating:
1. **`db`:** PostgreSQL 16 with `pgvector` pre-installed (`pgvector/pgvector:pg16`).
2. **`backend`:** FastAPI container connected to PostgreSQL via `postgresql+psycopg://`.
3. **`frontend`:** Streamlit container connected to backend via Docker internal network (`http://backend:8000`).

### Running with Docker Compose

```bash
# 1. Validate docker compose configuration
docker compose config

# 2. Build and start services in detached mode
docker compose up --build -d

# 3. Check service health status
docker compose ps

# 4. View logs
docker compose logs -f backend
docker compose logs -f frontend

# 5. Stop containers (preserves database volume)
docker compose down

# WARNING: docker compose down -v will delete persistent database volumes
```

---

## 8. Automated Testing Suite

ContextGPT has a comprehensive, automated test suite that tests all core layers using isolated test database fixtures and mockable AI fallbacks:
- Application startup and health checks
- User registration, duplicate validation, and Argon2 password hashing
- JWT access tokens and refresh token rotation with revocation
- Source extraction, file uploads, and SSRF blocking
- Multi-style document summarization
- RAG chunking, vector embeddings, similarity retrieval, and citation tracking
- Strict multi-user ownership isolation

To run the test suite:
```bash
# Windows
.\.venv\Scripts\pytest -v

# Linux / macOS
pytest -v
```

All 18 tests execute in under 5 seconds with 100% pass rates.

---

## 9. End-to-End Walkthrough Example

Let's trace what happens when an analyst uses ContextGPT to research Python iterator functions:

### Scenario
The user uploads a PDF file titled `python_iterators.pdf`, requests a detailed summary, and then asks:
> *"What is the difference between `map()` and `filter()` according to this document?"*

### Step-by-Step Flow:

1. **Authentication:**
   - The user registers and signs in.
   - The backend hashes the password using **Argon2** via `pwdlib` and returns a **JWT access token** (1 hour / 60 min) via `PyJWT` and a secure cryptographic **refresh token** (7 days).
   - The frontend stores the token in `st.session_state` and attaches `Authorization: Bearer <token>` to all subsequent requests.

2. **Ingestion & Loader:**
   - The user selects the PDF in the Streamlit UI and clicks "Upload & Index Document".
   - The file is sent via `POST /api/v1/sources/upload`.
   - `SourceService` receives the upload, validates the size (< 20MB) and extension, and routes it to `PDFLoader`.
   - `PDFLoader` reads each page with PyPDF, strips corrupt data, checks for scanned-document limitations, and extracts the plain text.
   - The source record is saved in PostgreSQL with `processing_status = "completed"`.

3. **Text Chunking & Embeddings:**
   - `EmbeddingService` splits the extracted text using `RecursiveCharacterTextSplitter` into overlapping chunks (1,000 characters with 150-character overlap).
   - Each chunk receives an embedding vector (`text-embedding-3-small` or deterministic fallback) and is saved into the `document_chunks` table linked to `user_id` and `source_id`.

4. **Summarization:**
   - The user selects the source and chooses "Detailed Summary".
   - The frontend calls `POST /api/v1/summaries`.
   - `SummaryService` checks document length. If it fits within the context window, it calls the LLM with `get_summarization_prompt("detailed")`. If the document is massive (> 16,000 chars), it triggers a hierarchical **Map-Reduce** workflow: summarizing chunks sequentially and combining the intermediate summaries into an unified analysis.
   - The summary is persisted to the database and displayed on the user's dashboard.

5. **Conversational RAG Question:**
   - The user navigates to "Ask ContextGPT" and submits: *"What is the difference between map() and filter() according to this document?"*
   - The frontend calls `POST /api/v1/chat/ask`.
   - `RetrievalService` generates an embedding of the user's question and computes vector cosine similarities against all chunks **strictly filtered by `user_id == current_user.id`**.
   - The top 5 matching chunks are retrieved.
   - `construct_context()` builds a bounded prompt containing only the verified passages with citation labels (`[Source 1: python_iterators.pdf (Section 2)]`).
   - The LLM receives the system prompt enforcing strict grounding:
     > *"Answer using ONLY the retrieved source passages. If insufficient evidence exists, state that clearly. Never guess or invent facts."*
   - The model generates the grounded answer:
     > *"According to [Source 1], `map()` applies a function to every item in an iterable to transform items, whereas `filter()` selects only elements for which the function returns true."*
   - The user and assistant messages, along with exact citation references and similarity scores, are saved in the database under `conversations` and `messages`.

---

## 10. API Endpoint Reference

| Method | Endpoint | Description | Protected |
| :--- | :--- | :--- | :---: |
| `GET` | `/health` | Liveness health check | No |
| `GET` | `/health/ready` | Readiness check (tests database ping) | No |
| `POST` | `/api/v1/auth/register` | Register a new user | No |
| `POST` | `/api/v1/auth/login` | Authenticate and obtain JWT access + refresh tokens | No |
| `POST` | `/api/v1/auth/refresh` | Rotate and issue new access & refresh tokens | No |
| `POST` | `/api/v1/auth/logout` | Revoke a refresh token | No |
| `GET` | `/api/v1/auth/me` | Get profile of the current authenticated user | Yes |
| `GET` | `/api/v1/users/me` | Alias for current user profile | Yes |
| `POST` | `/api/v1/sources/upload` | Upload and index document files | Yes |
| `POST` | `/api/v1/sources/webpage` | Extract and index a public webpage URL | Yes |
| `POST` | `/api/v1/sources/api` | Extract and index a REST API response | Yes |
| `POST` | `/api/v1/sources/database` | Execute authorized read-only SQL query | Yes |
| `GET` | `/api/v1/sources` | List all sources owned by user | Yes |
| `GET` | `/api/v1/sources/{id}` | Get specific source details & status | Yes |
| `DELETE`| `/api/v1/sources/{id}` | Delete source and cascade delete chunks | Yes |
| `POST` | `/api/v1/summaries` | Generate a summary for a source | Yes |
| `GET` | `/api/v1/summaries` | List user's summaries | Yes |
| `GET` | `/api/v1/summaries/{id}` | Get specific summary details | Yes |
| `DELETE`| `/api/v1/summaries/{id}` | Delete a summary | Yes |
| `POST` | `/api/v1/chat/ask` | Ask a question via grounded RAG | Yes |
| `POST` | `/api/v1/chat/conversations` | Create a new chat session thread | Yes |
| `GET` | `/api/v1/chat/conversations` | List user's chat sessions | Yes |
| `GET` | `/api/v1/chat/conversations/{id}`| Get conversation message history | Yes |
| `DELETE`| `/api/v1/chat/conversations/{id}`| Delete conversation session | Yes |

---

## 11. Security Architecture

1. **Anti-SSRF Protection (`backend/app/loaders/base.py`):**
   - Resolves target hostnames against DNS and blocks private IP ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, and link-local `169.254.169.254`).
   - Blocks access to localhost, internal container networks, and cloud instance metadata endpoints.
   - Validates redirects recursively.

2. **Database Query Safeguards (`backend/app/loaders/database_loader.py`):**
   - Strictly enforces read-only `SELECT` statements.
   - Regex token matching blocks destructive SQL keywords (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `EXEC`).
   - Masks sensitive database connection passwords from logs and frontend API responses.

3. **Multi-Tenant Ownership Isolation:**
   - Every source, chunk, summary, and conversation row in the database enforces foreign key ownership (`user_id`).
   - Queries always include `WHERE user_id == current_user.id`.
   - Access attempts to resources owned by other users return `404 Not Found` to prevent resource enumeration.

4. **Argon2 Password Hashing & JWT Rotation:**
   - Passwords hashed using Argon2 with individual cryptographic salts.
   - Refresh tokens are hashed before storage (`SHA-256`).
   - Refresh token rotation revokes old refresh tokens upon each use.

5. **Prompt Injection Resistance:**
   - System prompts explicitly declare retrieved document text as passive untrusted data.
   - Instructions inside retrieved documents attempting to override rules are ignored.

---

## 12. Troubleshooting & FAQ

### Q: Why do I see "ContextGPT Offline Demonstration Mode" in summaries or chat answers?
**A:** This occurs when `OPENAI_API_KEY` is blank or invalid in your `.env` file. ContextGPT includes an offline mode so you can test all UI navigation, ingestion, chunking, and database operations without paid API credentials. To enable live AI synthesis, simply add your OpenAI API key to `.env` and restart the backend.

### Q: How do I create and connect the database in DBeaver?
**A:** 
1. Open **DBeaver** and connect to your local PostgreSQL server (`localhost:5432`).
2. Right-click on **Databases** -> **Create New Database**, name it `contextgpt`, and click **OK**.
3. In your `.env` file, ensure `DATABASE_URL` is set:
   ```dotenv
   DATABASE_URL=postgresql+psycopg://postgres:your_password@localhost:5432/contextgpt
   ```
4. Run `alembic upgrade head` (or launch the backend with `uvicorn`, which automatically initializes all tables on startup). Refresh DBeaver to inspect all tables created under the `public` schema.

### Q: What happens when I delete a source?
**A:** Thanks to SQLAlchemy foreign key cascade rules (`ondelete="CASCADE"`), deleting a source automatically cleans up all associated `document_chunks` and resets or removes linked summaries.

---

## 13. Current Limitations & Roadmap

- **Scanned PDFs & OCR:** The current PDF loader processes text-based PDFs. Rasterized or scanned image PDFs without selectable text will report that OCR is not yet enabled.
- **Audio / Video Transcription:** YouTube captions are supported. Direct audio MP3/WAV transcription via Whisper is planned for the next release.
- **Vector Acceleration:** Similarity search is accelerated using PostgreSQL + pgvector when the extension is active, with seamless in-database vector cosine similarity fallback ensuring full functionality across standard PostgreSQL installations.

---

**ContextGPT** — Understand more. Ask anything.
