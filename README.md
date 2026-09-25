# GenAI Data Assistant Monorepo

A scalable, production-ready monorepo boilerplate for a **Generative AI Data Assistant** built with Python 3.12, FastAPI, LangChain, LangGraph, Google Gemini API, PostgreSQL, Qdrant, Docker Compose, `uv`, SQLAlchemy, Alembic, Ruff, and Pytest.

---

## Architecture Overview

The GenAI Data Assistant acts as an intelligent router and orchestration engine. Incoming user queries are parsed by a LangGraph Router node, which delegates tasks to either:
1. **RAG Pipeline**: Retrieves vector context from Qdrant for document/unstructured data queries.
2. **SQL Agent**: Formulates and executes safe SQL queries against PostgreSQL for structured business analytics (e.g., revenue queries on customers, products, and orders).

Direct `/chat` requests are powered by **Google Gemini** (`gemini-2.5-flash`).

```mermaid
flowchart TD
    User([User / Client]) -->|HTTP Request| FastAPI[FastAPI App]
    FastAPI -->|Invoke Workflow| Router[LangGraph Router Node]
    
    subgraph Execution Routing
        Router -->|Unstructured Document Query| RAG[RAG Pipeline]
        Router -->|Structured Data Query| SQLAgent[SQL Agent]
    end
    
    RAG -->|Vector Search| Qdrant[(Qdrant Vector DB)]
    SQLAgent -->|SQL Queries| PostgreSQL[(PostgreSQL DB)]
    
    Qdrant -->|Context Docs| Combine[Combine & Synthesize Node]
    PostgreSQL -->|Query Results| Combine
    
    Combine -->|Prompt & Context| Gemini[Google Gemini API]
    Gemini -->|LLM Response| Respond[Respond Node]
    Respond -->|HTTP Response| User
```

---

## Project Structure

```text
genai-data-assistant/
│
├── apps/
│   └── api/                  # FastAPI Application Service
│       ├── app/
│       │   ├── api/          # Route handlers (/health, /chat, /documents)
│       │   ├── core/         # Logging middleware, exception handlers, config
│       │   ├── services/     # Service layer business logic interfaces
│       │   ├── models/       # Pydantic API schemas
│       │   ├── dependencies/ # FastAPI dependency injectors
│       │   └── main.py       # App initialization & middleware binding
│       ├── tests/            # Integration & unit test suite (pytest)
│       ├── Dockerfile        # Production Dockerfile (python:3.12-slim, non-root user)
│       ├── pyproject.toml    # API dependencies & Ruff/Pytest configuration
│       └── uv.lock           # Locked dependency tree
│
├── packages/                 # Shared Monorepo Packages
│   ├── rag/                  # Document ingestion, embeddings & retriever skeletons
│   ├── sql_agent/            # DB schema inspector, query validator & SQL agent skeletons
│   ├── graph/                # LangGraph state definition, router & workflow DAG
│   ├── shared/               # Shared settings, Gemini client, logging & utilities
│   └── config/               # Alembic database migrations & Third-party integrations
│
├── data/
│   ├── documents/            # Volume placeholder for document storage
│   └── postgres/             # PostgreSQL persistent data storage
│
├── infra/
│   ├── docker-compose.yml    # Multi-container setup (API, Postgres, Qdrant)
│   ├── postgres/
│   │   └── init.sql          # Seed script: customers, products, orders schema & data
│   └── qdrant/               # Qdrant volume storage
│
├── scripts/
│   ├── setup.sh              # Local development setup script
│   └── wait-for-services.sh  # Readiness check for DB & Qdrant before boot
│
├── .env.example              # Environment variables template
├── .gitignore                # Version control ignore rules
├── Makefile                  # Helper commands for local dev & docker management
└── README.md                 # Project documentation
```

---

## Google Gemini API Setup Guide

To use the Google Gemini LLM integration:

### 1. Get a Free Google Gemini API Key
1. Go to [Google AI Studio](https://aistudio.google.com/).
2. Sign in with your Google account.
3. Click on **Create API Key**.
4. Copy your generated API key string.

### 2. Configure `.env` File
Create or update your `.env` file in the project root:
```bash
cp .env.example .env
```

Set `GEMINI_API_KEY` and optionally `GEMINI_MODEL`:
```env
GEMINI_API_KEY=AIzaSyYourActualGeminiApiKeyHere
GEMINI_MODEL=gemini-2.5-flash
```

---

## Quick Start & Running the Project

### Running with Docker Compose

Spin up the entire stack (FastAPI, PostgreSQL 16, and Qdrant) using Docker Compose:

```bash
make up
# OR
docker compose -f infra/docker-compose.yml up --build -d
```

### Accessing Services

- **FastAPI Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **Interactive Swagger Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **PostgreSQL Database**: `localhost:5432` (`db: assistant`, `user: genai`, `pass: genai`)
- **Qdrant REST API**: `localhost:6333`

---

## API Endpoints & Usage Example

| Method | Endpoint | Status | Description |
|---|---|---|---|
| `GET` | `/health` | **200 OK** | Health check returning service & Gemini configuration status |
| `POST` | `/chat` | **200 OK** | Direct chat completion endpoint using Google Gemini API |
| `POST` | `/documents/ingest` | **501 Not Implemented** | Future endpoint for RAG document ingestion pipeline |
| `GET` | `/documents` | **501 Not Implemented** | Future endpoint for listing ingested vector documents |
| `DELETE` | `/documents/{id}` | **501 Not Implemented** | Future endpoint for purging document embeddings |

### Example `/chat` Request

Send a message prompt to the assistant:

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Explain quantum computing in one sentence."}'
```

### Example `/chat` Response

```json
{
  "answer": "Quantum computing uses the principles of quantum mechanics to process complex information in ways that classical computers cannot.",
  "provider": "gemini",
  "model": "gemini-2.5-flash"
}
```

### Example `/health` Response

```json
{
  "status": "healthy",
  "services": {
    "api": true,
    "postgres": true,
    "qdrant": true,
    "gemini_configured": true
  }
}
```

---

## Development & Testing

### Running Tests

Run the Pytest suite (including mocked Gemini unit tests):
```bash
make test
```

### Code Formatting & Linting

Verify and fix code formatting using Ruff:
```bash
make lint
make format
```
