# Spending Tracker

A personal spending tracker backend: a REST API that ingests bank statement files, normalises transactions, and exposes them for querying. Built with **FastAPI**, **SQLModel**, and **Supabase** (auth + object storage). The project is still **work in progress** and not yet set up for one-click clone-and-run.

## Features

- **REST API** (versioned under `/api/v1`): statement import, auth (HTTP Basic → JWT via Supabase), and transaction listing.
- **Statement import** (`POST /api/v1/statement-imports`): multipart upload of statement files; validates metadata (source, size, type), uploads to object storage, creates an import job, and schedules job run in the background. Returns `202` with job ID and status. Fully covered by unit tests, with logging and explicit exception handling.
- **Import job pipeline**: for each job, the runner downloads the file, extracts transactions with a bank-specific extractor (Revolut, Swedbank), applies business filter rules, deduplicates by `dedup_key` (idempotent re-imports), converts amounts to EUR, enriches with spending category and meal type, then inserts new transactions. Job status and failure reasons are persisted.
- **Transactions** (`GET /api/v1/transactions`): list all transactions for the authenticated user.

## Code structure

- **`app/main.py`** — FastAPI app, lifespan (DB engine, Supabase admin, file storage), auth, CORS, request-logging middleware.
- **`app/api/`** — Route modules: `statement_imports.py` (create job, get job by ID), `transactions.py` (list transactions).
- **`app/core/`** — Config (`config.py`), dependencies (`dependencies.py`), shared types and enums (`project_types.py`).
- **`app/db/`** — SQLModel/SQLAlchemy: `statement_import_jobs.py`, `transactions.py`.
- **`app/statement_extractors/`** — Per-bank statementextractors (e.g. Revolut, Swedbank) and a registry; parse statement files into `ExtractedTransaction` models.
- **`app/import_job_runner.py`** — Background job workflow: load job, download file, extract → filter → dedupe → enrich → insert; job status updates and failure classification.
- **`app/business_rules/`** — Filter rules and spending categories used during import.
- **`app/storage/`** — File storage abstraction (Supabase buckets) for upload/download of statement files.
- **`app/enrichment.py`** — EUR conversion and category/meal-type enrichment.
- **`app/statement_validation.py`** — Pydantic validation for statement metadata (source, size, type).

Tests live under **`tests/`**: unit tests for the job runner, validation, DB layer, extractors, and business rules; integration tests for the statement-import API (e.g. Revolut Excel) with a test DB and fake storage.

## Tech stack

Python 3.13+, FastAPI, SQLModel (SQLAlchemy), Pydantic / pydantic-settings, Supabase (auth + storage), PostgreSQL, `currencyconverter`, openpyxl for statement parsing. Dev: pytest, uv.
