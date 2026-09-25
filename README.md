# ResearchOS

ResearchOS is a local-first research workflow assistant for turning a collection
of academic PDFs into searchable evidence, structured analyses, comparisons,
research ideas, draft workspace content, and compilable LaTeX. It has a Next.js
web application and a FastAPI service. MongoDB holds application records,
Chroma stores vector embeddings, uploaded files remain on local disk, and Groq
is used for AI-assisted generation.

## What it does

- Upload, list, inspect, parse, extract, search, and delete research papers.
- Extract PDF text, split it into chunks, embed those chunks, and retrieve the
  most relevant evidence for a question.
- Answer questions about an uploaded paper with retrieved source chunks.
- Produce structured paper comparisons and evidence-grounded peer-review style
  reports.
- Search external literature from OpenAlex and arXiv, with source-aware
  relevance ranking.
- Identify research gaps and generate research ideas from selected papers.
- Create research workspaces, generate cited draft content, and retain saved
  versions.
- Edit LaTeX, compile it through Tectonic, surface compiler diagnostics, and
  preview the generated PDF in the browser.

The interface starts at `/dashboard` and also includes pages for papers,
search, comparison, review simulation, ideation, manuscript drafting, and
workspaces.

## Architecture

```text
Browser (Next.js 16 / React 19)       http://localhost:3000
             |
             | REST (NEXT_PUBLIC_API_BASE)
             v
FastAPI backend                         http://127.0.0.1:8000
  |-- MongoDB: paper, chunk, extraction, review, workspace metadata
  |-- Chroma: persistent semantic vectors in backend/vector_store/
  |-- Local files: uploads in backend/uploads/
  |-- Groq: extraction, answers, reviews, ideation, and drafts
  |-- OpenAlex + arXiv: literature-discovery results
  `-- Tectonic: temporary LaTeX compilation to PDF
```

## Repository layout

```text
researchOS/
├── frontend/                         Next.js application
│   ├── app/                          App Router pages and global styling
│   ├── components/                   Layout, paper, comparison, search, and workspace UI
│   └── lib/                          API client and TypeScript types
├── backend/                          FastAPI application
│   ├── app/
│   │   ├── routers/                  Mounted paper, search, answer, review, discovery, LaTeX routes
│   │   ├── api/routes/               Mounted compare, ideation, and workspace routes
│   │   ├── services/                 PDF, chunking, vector, AI, discovery, and LaTeX logic
│   │   ├── schemas/                  Request and response models
│   │   └── db.py                     MongoDB collections
│   ├── tests/                        PDF parser and Groq client tests
│   ├── .env.example                  Backend environment template
│   ├── requirements.txt              Python dependencies
│   ├── uploads/                      Created at runtime; original uploaded PDFs
│   └── vector_store/                 Created at runtime; Chroma persistence
└── README.md
```

## Prerequisites

- Node.js compatible with Next.js 16 (Node 20.9+ is a safe choice) and npm.
- Python 3.10+; Python 3.11 is recommended.
- A running MongoDB instance. The local default is `mongodb://127.0.0.1:27017`.
- At least one Groq API key for AI-powered features.
- Internet access for OpenAlex/arXiv discovery and Groq requests.
- Tectonic only if LaTeX PDF compilation is needed.

## Quick start

### 1. Start MongoDB

Run MongoDB locally, or point `MONGODB_URL` at an accessible MongoDB server.
No database setup is needed beforehand: ResearchOS uses the `researchos`
database by default and creates collections when records are written.

### 2. Configure and start the backend

In PowerShell:

```powershell
cd backend
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Set `GROQ_API_KEY` (or `GROQ_API_KEYS`) in `backend/.env` before using AI
generation. On systems where PowerShell script execution is restricted, use
the virtual environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Verify it at [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health).
FastAPI also exposes interactive API documentation at
[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 3. Configure and start the frontend

In a second PowerShell window:

```powershell
cd frontend
npm ci
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The root page redirects
to `/dashboard`.

The frontend defaults to `http://127.0.0.1:8000`. To use a different backend,
create `frontend/.env.local`:

```dotenv
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
```

Restart the Next.js dev server after changing environment variables.

### Important current repository gaps

The project code imports the `groq` and `arxiv` Python packages, but neither is
currently pinned in `backend/requirements.txt`. If the backend fails with a
`ModuleNotFoundError` after installing the requirements, install them in the
active virtual environment:

```powershell
pip install groq arxiv
```

In addition, `backend/app/services/embedding_service.py` references
`settings.EMBEDDING_MODEL`, but the current `Settings` class does not define
that setting. Semantic indexing will therefore need that code/configuration gap
resolved before parsing and vector search can run successfully. A typical
Sentence Transformers model value would be `all-MiniLM-L6-v2`, but adding it is
an application-code change, not merely an environment-file change with the
current configuration class.

## Configuration

Backend settings are read from `backend/.env`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_NAME` | `ResearchOS Backend` | API application title |
| `APP_ENV` | `development` | Runtime environment label |
| `FRONTEND_URL` | `http://localhost:3000` | Intended frontend origin setting |
| `MONGODB_URL` | `mongodb://127.0.0.1:27017` | MongoDB connection URL |
| `MONGODB_DB` | `researchos` | MongoDB database name |
| `STORAGE_DIR` | `backend/uploads` | Uploaded-PDF directory |
| `VECTOR_DIR` | `backend/vector_store` | Persistent Chroma directory |
| `GROQ_API_KEY` | empty | One Groq API key; used when no key list is set |
| `GROQ_API_KEYS` | empty | Comma-, newline-, or semicolon-separated Groq keys; takes precedence and is round-robin rotated |
| `GROQ_MODEL` | `openai/gpt-oss-20b` | Groq model identifier |
| `OPENALEX_API_KEY` | empty | Optional OpenAlex API key, read by the discovery service |
| `OPENALEX_EMAIL` | `developer@researchos.local` | OpenAlex `mailto` contact |

Never commit `.env` files or API keys. The repository ignores environment
files but keeps `.env.example` as a safe template.

### CORS and deployment

The backend currently permits `http://localhost:3000` and
`http://127.0.0.1:3000`. Add the deployed frontend origin in
`backend/app/main.py` before hosting the UI elsewhere. The backend is designed
around local persistence; use managed MongoDB and durable volumes for uploads
and Chroma if deploying it.

### LaTeX compiler

LaTeX compilation uses Tectonic in untrusted mode with a 300-second timeout
and 250,000-character limits for both LaTeX and BibTeX input. 
Update `TECTONIC_EXECUTABLE` in `backend/app/services/latex_compile_service.py`
to match the machine running the backend, or make that executable available at
the configured path. The compiler writes only to a newly created temporary
directory for each request; successful PDFs are returned to the browser and
are not persisted.

## Typical workflow

1. Upload a PDF from the Papers view.
2. Parse/index it to extract text, create chunks, and write semantic vectors.
3. Run extraction for structured paper details.
4. Search inside the paper or ask an evidence-grounded question.
5. Select papers to compare, generate a review, or run research-gap ideation.
6. Create a workspace from the selected papers and an idea.
7. Generate a cited draft, save versions, edit its LaTeX, and compile a PDF.

## API reference

The source of truth for parameter schemas and example payloads is the live
Swagger UI at `/docs`. The mounted routes are summarized below.

| Area | Endpoint | Purpose |
| --- | --- | --- |
| Service | `GET /` | API status message |
| Service | `GET /health` | Lightweight health check |
| Papers | `POST /papers/upload` | Upload a paper as multipart form field `file` |
| Papers | `GET /papers/` | List papers |
| Papers | `GET /papers/{paper_id}` | Retrieve one paper |
| Papers | `DELETE /papers/{paper_id}` | Delete paper data, chunks/vectors, extraction, and file when available |
| Papers | `POST /papers/{paper_id}/parse` | Parse PDF, chunk it, and index it |
| Papers | `POST /papers/{paper_id}/extract` | Parse/index and generate structured extraction |
| Papers | `GET /papers/{paper_id}/extraction` | Get saved extraction |
| Papers | `POST /papers/{paper_id}/search` | Semantic search one paper; JSON `query`, `top_k` |
| Papers | `POST /papers/{paper_id}/answer` | Grounded answer; JSON `question`, `top_k` |
| Papers | `PATCH /papers/{paper_id}/status` | Update paper status |
| Search | `POST /search/query` | Semantic search over selected indexed papers |
| Discovery | `GET /search/discovery` | Search OpenAlex and arXiv |
| Discovery | `GET /discovery/search` | Alternate discovery endpoint with the same service |
| Compare | `POST /compare` | Compare selected papers; JSON `paper_ids` |
| Review | `POST /reviews/{paper_id}` | Create an evidence-grounded review |
| Ideation | `POST /ideation/analyze` | Analyze gaps and generate research ideas |
| Workspaces | `POST /workspaces` | Create a research workspace |
| Workspaces | `GET /workspaces` | List workspaces |
| Workspaces | `GET` / `PATCH /workspaces/{workspace_id}` | Retrieve or update a workspace |
| Workspaces | `POST /workspaces/{workspace_id}/generate` | Generate workspace content |
| Workspaces | `POST /workspaces/{workspace_id}/versions` | Save a draft version |
| Workspaces | `GET /workspaces/{workspace_id}/versions` | List saved versions |
| LaTeX | `POST /workspaces/{workspace_id}/latex/compile/status` | Validate/compile and return log plus parsed errors |
| LaTeX | `POST /workspaces/{workspace_id}/latex/compile` | Compile and return `application/pdf` |

For discovery, `query` must be 2–300 characters and `limit` is 1–10. The
limit is per source, so a value of 5 can return up to five OpenAlex and five
arXiv results. Semantic search expects papers to have been parsed/indexed.

## Development commands

```powershell
# Frontend (run from frontend/)
npm run dev
npm run lint
npm run build
npm run start

# Backend (run from backend/ with the virtual environment active)
pytest
python -m pytest
uvicorn app.main:app --reload
```

Current backend tests cover PDF front-matter author extraction and round-robin
Groq client selection. The frontend uses ESLint and TypeScript through the
Next.js build toolchain.

## Data model and local state

- MongoDB collections: `papers`, `chunks`, `extractions`, `reviews`,
  `workspaces`, and `workspace_versions`.
- Chroma persists semantic vectors under `backend/vector_store/`.
- PDFs uploaded through the API are stored under `backend/uploads/` by default.
- The repository also contains `backend/storage/papers/`, which holds existing
  local sample/reference PDFs. Treat these as local project data, not as a
  replacement for a formal dataset pipeline.

Back up MongoDB, the upload directory, and the vector-store directory together
if you need to preserve a complete local ResearchOS workspace.

## Troubleshooting

| Symptom | Likely cause and resolution |
| --- | --- |
| `API 500` when uploading, listing, or parsing | Confirm MongoDB is running and `MONGODB_URL` is reachable. |
| AI features fail or return a missing-key error | Put a valid `GROQ_API_KEY` or `GROQ_API_KEYS` value in `backend/.env`, then restart the backend. |
| Search has no useful results | Parse/index the paper first. This creates chunks and their Chroma vectors. |
| Browser blocks backend calls | Ensure the frontend uses the correct `NEXT_PUBLIC_API_BASE` and add its exact origin to the backend CORS allow-list. |
| Discovery returns fewer results | OpenAlex or arXiv may be unavailable, rate-limited, or have limited matches; the service queries both sources independently. |
| LaTeX compilation says Tectonic is unavailable | Install Tectonic and update `TECTONIC_EXECUTABLE` to a valid executable path. |
| LaTeX compilation times out | Simplify the document or its dependencies; compilation is capped at five minutes. |

