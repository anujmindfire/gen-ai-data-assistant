# GenAI Data Assistant Monorepo

A scalable, production-ready monorepo boilerplate for a **Generative AI Data Assistant** built with Python 3.12, FastAPI, LangChain, LangGraph, Google Gemini API, PostgreSQL, Qdrant, Docker Compose, `uv`, SQLAlchemy, Alembic, Ruff, and Pytest.

---

## Architecture Overview

The GenAI Data Assistant acts as an intelligent router and orchestration engine. Incoming user queries are parsed by a LangGraph Router node, which delegates tasks to either:
1. **RAG Pipeline**: Retrieves vector context from Qdrant for document/unstructured data queries.
2. **SQL Agent**: Formulates and executes safe SQL queries against PostgreSQL for structured business analytics (e.g., revenue queries on customers, products, and orders).

Direct `/chat` requests are powered by **Google Gemini** (`gemini-3.6-flash`).

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
│   ├── rag/                  # Document ingestion, embeddings & retriever modules
│   ├── sql_agent/            # DB schema inspector, query validator & SQL agent skeletons
│   ├── graph/                # LangGraph state definition, router & workflow DAG
│   ├── shared/               # Shared settings, Gemini client, logging & utilities
│   └── config/               # Alembic database migrations & Third-party integrations
│
├── data/
│   ├── documents/            # Physical document storage location (data/documents/<uuid>_<filename>)
│   └── postgres/             # PostgreSQL persistent data storage
│
├── infra/
│   ├── docker-compose.yml    # Multi-container setup (API, Postgres, Qdrant)
│   ├── postgres/
│   │   └── init.sql          # Seed script: customers, products, orders, documents schema & data
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

## Document Ingestion & Storage

### Supported File Formats
- `.pdf` (Parsed using `PyPDFLoader`)
- `.docx` (Parsed using `Docx2txtLoader`)
- `.txt` (Parsed using `TextLoader`)
- `.md` (Parsed using `TextLoader`)

### Storage Location
Uploaded physical files are stored under:
```text
data/documents/<uuid>_<filename>
```
File metadata (id, filename, file_type, file_path, size, pages, uploaded_at) is persisted in the PostgreSQL `documents` table.

---

## API Endpoints & Specification

| Method | Endpoint | Status | Description |
|---|---|---|---|
| `GET` | `/health` | **200 OK** | Health check returning service & Gemini configuration status |
| `POST` | `/chat` | **200 OK** | Direct chat completion endpoint using Google Gemini API |
| `POST` | `/documents/ingest` | **201 Created** | Upload, parse, and register document file metadata |
| `GET` | `/documents` | **200 OK** | List all uploaded document records |
| `DELETE` | `/documents/{id}` | **200 OK** | Delete document record and purge physical file from disk |

---

## Usage Examples

### 1. Upload & Ingest a Document

```bash
curl -X POST "http://localhost:8000/documents/ingest" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@employee_handbook.pdf"
```

**Response (`201 Created`)**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "employee_handbook.pdf",
  "type": "pdf",
  "size": 120394,
  "status": "ingested"
}
```

### 2. List Ingested Documents

```bash
curl -X GET "http://localhost:8000/documents"
```

**Response (`200 OK`)**:
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "employee_handbook.pdf",
    "type": "pdf"
  }
]
```

### 3. Delete a Document

```bash
curl -X DELETE "http://localhost:8000/documents/550e8400-e29b-41d4-a716-446655440000"
```

**Response (`200 OK`)**:
```json
{
  "message": "Document deleted"
}
```

---

## Development & Testing

### Running Tests

Run the Pytest suite (including document ingestion tests):
```bash
make test
```

### Code Formatting & Linting

Verify and fix code formatting using Ruff:
```bash
make lint
make format
```
