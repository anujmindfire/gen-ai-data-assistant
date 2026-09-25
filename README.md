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
│   ├── rag/                  # Document ingestion, chunking, embeddings & retriever modules
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

## Document Pipeline, Embeddings & Qdrant Indexing

### Ingestion & Indexing Flow
```text
Document Upload
      ↓
File Storage (data/documents/<uuid>_<filename>)
      ↓
Document Parser (PyPDFLoader, Docx2txtLoader, TextLoader)
      ↓
Document Chunker (RecursiveCharacterTextSplitter)
      ↓
Embedding Generation (GoogleGenerativeAIEmbeddings: text-embedding-004)
      ↓
Vector Indexing (Qdrant PointStruct with payload & cosine distance)
      ↓
Metadata Persistence (PostgreSQL documents table) & API Response
```

### Embedding & Qdrant Configuration
Vector embeddings are generated using Google Gemini's `text-embedding-004` model (768-dimensional dense vectors) and indexed into Qdrant collection `company_documents`.

- **Embedding Model (`GEMINI_EMBEDDING_MODEL`)**: `text-embedding-004`
- **Embedding Batch Size (`EMBEDDING_BATCH_SIZE`)**: `16` chunks per batch
- **Qdrant Collection (`QDRANT_COLLECTION`)**: `company_documents`
- **Vector Size (`QDRANT_VECTOR_SIZE`)**: `768` (Cosine Distance)

Environment configuration (`.env`):
```env
GEMINI_EMBEDDING_MODEL=text-embedding-004
EMBEDDING_BATCH_SIZE=16
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_COLLECTION=company_documents
QDRANT_VECTOR_SIZE=768
CHUNK_SIZE=500
CHUNK_OVERLAP=100
```

### Qdrant Point Payload Schema
Each text chunk is indexed as a Qdrant point vector with complete payload metadata for future retrieval:
```json
{
  "document_id": "1728275e-c75b-479e-87d8-8aaab5b3dd44",
  "chunk_id": "00000000-0000-0000-0000-000000000001",
  "filename": "employee_handbook.pdf",
  "file_type": "pdf",
  "page": 1,
  "chunk_index": 0,
  "text": "Extracted text chunk content body..."
}
```

*Note: In the next feature branch (`feat/rag-retrieval`), vector retrieval and semantic search will be implemented.*

---

## API Endpoints & Specification

| Method | Endpoint | Status | Description |
|---|---|---|---|
| `GET` | `/health` | **200 OK** | Health check returning service, Qdrant connectivity, & Gemini configuration status |
| `POST` | `/chat` | **200 OK** | Direct chat completion endpoint using Google Gemini API |
| `POST` | `/documents/ingest` | **201 Created** | Upload, parse, chunk, embed document, index in Qdrant, and return chunk count |
| `GET` | `/documents` | **200 OK** | List all uploaded document records |
| `DELETE` | `/documents/{id}` | **200 OK** | Delete document record, purge file from disk, and remove vectors from Qdrant |

---

## Usage Examples

### 1. Upload, Chunk, & Embed a Document

```bash
curl -X POST "http://localhost:8000/documents/ingest" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@employee_handbook.pdf"
```

**Response (`201 Created`)**:
```json
{
  "id": "1728275e-c75b-479e-87d8-8aaab5b3dd44",
  "filename": "employee_handbook.pdf",
  "status": "ingested",
  "chunks_created": 42
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
    "id": "1728275e-c75b-479e-87d8-8aaab5b3dd44",
    "filename": "employee_handbook.pdf",
    "type": "pdf"
  }
]
```

### 3. Delete a Document

```bash
curl -X DELETE "http://localhost:8000/documents/1728275e-c75b-479e-87d8-8aaab5b3dd44"
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

Run the Pytest suite (including mocked embedding unit tests):
```bash
make test
```

### Code Formatting & Linting

Verify and fix code formatting using Ruff:
```bash
make lint
make format
```
