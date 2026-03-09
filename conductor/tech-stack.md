# SpaceATracker: Technology Stack

## Core Technologies
- **Programming Language:** Python 3.14+
- **Package Manager:** `uv` (Fast Python package installer and workspace manager)
- **Type Checking:** `ty` (Astral's type checker for Python)
- **Data Validation & Schema:** `pydantic` (Strict type enforcement for reliability and code quality)

## Backend & Frameworks
- **HTTP Client:** `curl-cffi` (Advanced asynchronous HTTP requests)
- **Settings & Config:** `pydantic-settings` (Type-safe configuration management)
- **HTML Parsing:** `selectolax` (High-performance HTML extraction)
- **Async DB Driver:** `asyncpg` (Fast asynchronous PostgreSQL driver)
- **Cloud Storage SDK:** `aiobotocore` (Asynchronous SDK for S3-compatible storage)

## Storage & Database
- **Relational Database:** PostgreSQL 16 (Managed via `docker-compose`)
- **Blob Storage:** SeaweedFS (S3-compatible document storage)
- **Database Migrations:** `alembic` (Schema version control)

## Architecture
- **Structure:** Monorepo with `uv` workspaces
- **Components:**
  - `core`: Shared models, schemas, and database logic
  - `api`: FastAPI or similar REST interface (inferred from `api` folder)
  - `scraper`: Background worker for discovery and extraction

## Development & Quality Assurance
- **Linting & Formatting:** `ruff` (All-in-one Python tool)
- **Testing:** `pytest` (Asynchronous testing support)
- **Containerization:** `docker-compose` (For infrastructure and development environment)
