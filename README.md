# SpendPulse - Full Stack Portfolio Project

A full-stack app (FastAPI + React Typescript) that helps you see where your money goes.
- Import bank statements from multiple banks: extracting, normalizing, de-duplicating, auto-calculating spending categories, and storing them in a DB.
- View your transactions in a searchable modern dashboard, and manually adjust the spending categories to keep track of your spending.

The app was built to solve a personal budget management problem - I couldn't find an app that both (1) synced with bank accounts from multiple countries and (2) allowed me to customize categorization and analytics views.

The project demonstrates full-stack development skills including: data processing, domain modeling, modular architecture, REST APIs, and modern frontend. It features Python (FastAPI) Backend, React + TypeScript Frontend, PostgreSQL DB and deployment on Koyeb (Backend) + Cloudflare Pages (Frontend).

## Live Application
**[Try the live application](https://spendpulse.justas.tech)**

You can either sign up or click on __Try demo__ to try it out without creating an account.

### Screenshots
#### Login / Signup
![Login Screen](/screenshots/login.png)

#### Importing Statements
![Import-Select](/screenshots/import-select.png)

![Import-Select](/screenshots/import-scheduling.png)

![Import-Select](/screenshots/import-result.png)

#### Updating Spending Categories
![Import-Select](/screenshots/dashboard.png)


## How to run locally
### Docker
The project is packaged in a Docker container. The fastest way to run both frontend and backend is to copy the .env.docker files and run the container. From the project root directory (`spending-tracker/`), run:
```bash
    cp .env.docker.example .env.docker
    cp ./frontend/.env.docker.example ./frontend/.env.docker
    docker compose up --build
```

Sample statements to run can be found in `./sample_data/statements/`.

Note that this runs the project in demo mode using a test user. That is because auth requires a running supabase instance for auth and file storage and pulling the docker images for supabase may takes a while. To use the full features follow the instructions below.

### Manual Setup
The full project requires running an instance of postgres and supabase (either use a managed project or run a [local instance](https://supabase.com/docs/guides/local-development)) and updating the environment variables.

**Backend**

Requirements: Python 3.13+, PostgreSQL, Supabase project (or compatible Postgres + storage), `uv` / `pip` for dependencies
```bash
# from repo root
cp .env.example .env          # then fill in Postgres + Supabase credentials
uv sync
uvicorn app.main:app --reload
```

**Frontend**

Requirements: Node + npm
```bash
cd frontend
cp .env.example .env          # then fill in VITE_API_BASE_URL with the backend URL (including the API version suffix) and supabase creds
npm install
npm run dev
```
Visit the printed localhost URL.

---

## Summary
- **Scope**: Full-stack SPA (React + TypeScript frontend, Python/FastAPI backend) with bank statement import, transactions dashboard, and spending category tagging. Supabase for auth and file storage, PostgreSQL for data.
- **Architecture**: REST APIs, modular backend (API / DB / domain / file storage / statement extractors), background import jobs, demo mode.
- **Quality**: 90%+ test coverage via unit and integration tests (pytest), static type checking, linting/formatting, pre-push hook and GitHub Actions CI.
- **Deployment**: Backend on Koyeb, frontend on Cloudflare Pages, managed Supabase for Auth + storage, PostgreSQL.
- **Security & Auth**: Frontend login/signup, and session management, endpoints protected via JWT-based auth (Supabase) ; secrets managed via `.env`
- **Key source code**:
  - Backend (`app/`): `main.py`, `api/statement_imports.py`, `import_job_runner.py`, `statement_extractors/`, `business_rules/`
  - Frontend (`frontend/`): `src/App.tsx`, `src/pages/dashboard.tsx`, `src/contexts/AuthContext.tsx`, `src/hooks/transactions/`
  - see [Project Structure](#project-structure) for more info
---

## Table of Contents

- [Live Demo](#live-demo)
- [How to run locally](#how-to-run-locally)
- [Summary](#summary)
- [Key Features](#key-features)
- [High Level Architecture](#high-level-architecture)
- [Project Structure](#project-structure)
- [Statement Import Pipeline](#statement-import-pipeline)
- [Statement Extractors](#statement-extractors)

## Key Features

### Importing Bank Statements
  - `POST /api/v1/statement-imports`: uploading bank statements to import transactions.
    - Validates statement file, store it in Supabase file storage, enqueues background import job.
    - Background job downloads file, runs a bank‑specific extractor (Revolut, Swedbank), applies business rules, deduplicates, converts to standard currency, enriches with spending category, and persists transactions.
    - Each extractor implements a "deduplication key" calculation logic to ensure idempotent imports.
    - Job id, status and failure reasons are persisted for observability, rollbacks, re-runs.
  - Frontend UI flow that allows to upload file, gives user feedback on job status and displayes result (success, failure)

For technical details of the workflow, see: [Statement Import Pipeline](#statement-import-pipeline)

### Managing Transactions
  - `GET /api/v1/transactions`: list transactions for the authenticated user. Supports pagination, sorting, and filtering (by counterparty, id, category, note, and "untagged debit only")
  - Frontend Dashboard view:
    - Transactions table with search and filter UI (option to view "untagged debit only")
    - Assign category to a transaction (pick existing or create a new one)

## High Level Architecture
### Backend (`app/`):
- Python **FastAPI** app with versioned **REST API** under `/api/v1`. See **[API Documentation](https://api.spendpulse.justas.tech/docs)** for more details.
- **SQLModel / SQLAlchemy** for persistence (PostgreSQL).
- **Pydantic** used heavily to validate source data at the boundaries (API requests / responses, File I/O)
- **Supabase** for auth and for storage of uploaded statement files.
- Import job workflow that processes statement files and imports transactions in the background.
- Postgres DB for data persistence

### Frontend (`frontend/`)
- **React + TypeScript**, **Tailwind CSS**, shadcn‑style radix-ui components.
- **React Query** for data fetching/caching against the FastAPI backend.
- Routing (wouter), Context (AuthContext)
- Feature‑oriented structure (auth, transactions, categories) with reusable UI primitives.
- Dashboard with paginated, filterable transactions table and category assignment flows.

## Project Structure
```
spending-tracker/
├── app/                    # Backend (FastAPI)
│   ├── api/                # REST API layer
│   ├── db/                 # DB access Layer
│   ├── main.py             # Entry point for the FastAPI
|   |── ...
├── frontend/src            # React + TypeScript (Vite)
├── tests/                  # Backend test suite
│   ├── integration/        # Testing API flows
│   └── unit/               # Backend logic unit tests
├── .github/workflows/      # CI Workflow (lint, test, typecheck)
├── docker-compose.yml
├── backend.Dockerfile
├── pyproject.toml
├── .env.example            # environment variablese used by local server
├── .env.docker.example     # environment variables used by Docker
```

## Statement Import Pipeline

The workflow which imports transactions from bank
statements is a core element of the project. When a user uploads a bank statement, the app needs to parse it, figure out which transactions are new, convert to standard currency, tag spending categories, and store the new transactions. This section describes how that workflow is designed and the reasoning behind the key decisions.

### Asynchronous Flow - POST API vs Job Runner

The API endpoint (`POST /api/v1/statement-imports`) validates the uploaded file and stores it in Supabase file storage, but it does **not** parse or import as part of the same request. Instead it creates an **import job record** in the database and schedules a background task. The client gets a job ID back immediately so that it can poll for job status updates.

Why: parsing and importing can be slow for large files or complex parsing logic. Running it as part of request can block the client or timeout. Storing the original file and a job record also means jobs could be **re-run** (e.g. after a bug fix), **debugged** without asking the user to re-upload, or rolled back (deleting bad transactions data associated with a job).

### Pluggable Statement Extractors

Every bank has a different statement file format and data structure (E.g. Revolut exports XLSX, Swedbank exports CSV, etc.). To keep the rest of the pipeline bank-agnostic, each bank's parsing logic lives in its own extractor module (`app/statement_extractors/`) and exposes a standard interface:

> `(file_bytes) -> list[ExtractedTransaction]` (see "Typed transaction stages" )


A **registry** (`app/statement_extractors/registry.py`) maps each bank name to its extractor and the file types that it accepts. Adding support for a new bank means writing one extractor that fulfils the extractor interface contract and adding it to the registry — nothing else in the pipeline changes.

### Transaction Stages and Data Contracts

As a transaction moves through the pipeline, it passes through distinct data types. Each type acts as a contract between steps, making it explicit what data is available at each stage:

| Stage | Type | What it represents |
|-------|------|--------------------|
| Raw | Bank-specific model | The bank's own row format. Internal to the extractor, not shared. |
| Extracted | `ExtractedTransaction` | Shared shape for all banks. Contains key attributes: date, counterparty, amount, currency, side, dedup key. No standard currency amount yet. |
| Importable | `ImportableTransaction` | Adds normalised `eur_amount` (required for enrichment), optional `spending_category` and `meal_type`. Used as Input for enrichment and persistence. |
| Persisted | `Transaction` (DB model) | Adds `user_id`, `import_job_id`, and DB-level fields. |

Types are defined in `app/core/project_types.py` (domain) and `app/db/transactions.py` (persistence).

Business logic (filter rules, spending category rules, enrichment) depends only on the domain types — not on any bank format or the DB schema. That means the same `ImportableTransaction` contract could be produced by a different source (e.g. a CLI script loading historical data) and the enrichment and persistence steps would work unchanged.

### Pipeline steps

The import job runner (`app/import_job_runner.py`) executes a fixed sequence of standalone functions:

1. **Load** the statement file from file storage.
2. **Extract** — run the registered bank extractor to produce `list[ExtractedTransaction]`.
3. **Filter** — apply business rules to drop irrelevant rows (e.g. own-account transfers).
4. **Deduplicate** — compare deduplication keys against the user's existing transactions (see _"Idempotent Imports"_ below); split into new vs. existing.
5. **Normalise** — convert original-currency amounts to EUR, producing `list[ImportableTransaction]`.
6. **Enrich** — assign spending categories if transactions match any category rule function.
7. **Persist** — convert to DB models and batch-insert.

Each step is a separate function with typed inputs and outputs. This means individual steps can be reused outside the import flow — for example, the enrichment module can be called on a manually added transaction without involving the rest of the pipeline.

**Design approach** Three design approaches were considered: (1) **streaming** — process each row end-to-end as it is read; (2) **single-pass batch** — one loop that applies all transformations per row; (3) **multi-pass batch** (current) — each step processes the full list before the next step starts. Multi-pass was chosen because:

- **Deduplication requires batch state.** Fetching existing dedup keys once and comparing the whole set is simpler and more efficient than a per-row DB lookup. A streaming or single-pass approach would complicate this.
- **Fail-fast per step.** If any critical step fails, the whole batch is aborted cleanly before data reaches the DB. A single-pass loop would make it harder to reason about which rows had already been partially transformed.
- **Scope makes memory a non-issue.** Bank statements are typically a few thousand rows at most. In practice, even multi-year statements have completed in under a minute. At this scale the extra memory of holding intermediate lists is negligible.

### Idempotent imports

Users are likely to upload multiple statements with overlapping date ranges. So uploading the same file twice must not create duplicate transactions. Since we can't rely on bank statements for unique transaction IDs, each extractor computes a unique **deduplication key** from the fields available in that bank's format (e.g. date + reference + amount). Before inserting, the pipeline fetches existing dedup keys for the user, splits rows into new vs. already-imported, and only inserts the new ones. The database also enforces a unique constraint on `(user_id, dedup_key)` as a safety net.

### Batch insert

New transactions are inserted in a **single batch** rather than one-by-one or via upsert. This is a deliberate trade-off:
- **Performance** — one batch operation (single DB transaction) is fast.
- **Atomicity** — if anything fails, the entire batch insert is rolled back, avoiding partially imported, inconsistent data.
- **Observability** — because deduplication happens in application code *before* the insert, the pipeline knows exactly how many rows are new vs. duplicates and records those counts on the job. A DB-level `ON CONFLICT DO NOTHING` would silently discard duplicates, making accurate counts and logging harder.

### Job Tracking and Observability

Every import is tracked as a row in `statement_import_jobs`: status (pending / running / completed / failed), timestamps, `imported_txn_count`, `duplicate_txn_count`, and on failure a `failure_reason` mapped to a stable error code (e.g. `CURRENCY_CONVERSION_ERROR`, `EXTRACTOR_NOT_FOUND`). Structured logging covers each pipeline step. Together these provide an audit trail for debugging, analysis, and potential rollback (e.g. deleting data from a bad run and re-importing the file).

### Statement Extractors

The existing extractors follow a common pattern. A new extractor doesn't have to mirror this structure — it only needs to return `list[ExtractedTransaction]` — but it may be useful as a reference.

Each extractor has four parts:

1. **File reader** — reads the raw file into a list of row dictionaries. Revolut reads XLSX via `openpyxl`; Swedbank reads CSV via `DictReader`. This isolates file-format concerns from the rest of the logic.
2. **Raw model** — a Pydantic `BaseModel` that maps bank-specific column names to typed fields (e.g. Revolut's `"Started Date"` → `started_at: datetime`). Pydantic validators on the model handle bank-specific filtering (e.g. Revolut drops non-"COMPLETED" rows and unsupported transaction types like `EXCHANGE` or `TOPUP`; Swedbank drops summary rows). Rows that fail validation are counted and skipped, not fatal.
3. **Conversion function** — `convert_to_standardized_transaction(raw) → ExtractedTransaction`. Maps bank-specific fields to the shared domain shape: determines `side`, `transaction_type`, `counterparty`, and computes the **dedup key**. Each bank's dedup key uses whichever fields reliably identify a unique transaction in that format (Swedbank has a built-in unique ID; Revolut hashes a composite of date, description, amount, and balance).
4. **Logging** — on completion, each extractor logs total rows, successfully extracted count, and rejected count.

## Future Work
Currently, the app is mostly useful as a personal solution because it hardcodes the business rules (e.g. how to auto-calculate spending categories). I'd like to make it into a flexible and configurable app:
- Make the category rules and filter rules flexible with a config UI
- Create referential tables for categories, with a hierarchical taxonomy to allow analyzing data at multiple levels (e.g. EATING_OUT and FOOD_DELIVERIES -> FOOD level 2 category)
- UI for users to create new extractors logic using LLMs (e.g. to parse PDFs, auto suggest column mapping)
- Allow setting category budgets to track spending against goals