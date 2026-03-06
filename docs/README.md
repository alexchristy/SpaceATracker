# SpaceATracker Quickstart Guide

This quickstart explains how to set up the local environment, discover military terminals, and extract their associated documents (PDFs, images) using the background scraper.

## Prerequisites
- Docker and Docker Compose
- `uv` (Fast Python package installer)
- Python 3.14+

## 1. Start Storage Infrastructure
SpaceATracker relies on PostgreSQL for relational data and SeaweedFS (S3-compatible) for document storage. Ensure they are running via Docker:

```bash
docker-compose up -d
```

## 2. Initialize the Database
The project utilizes `alembic` to manage database schema migrations. First, ensure your core dependencies are installed and then run the migrations to create the tables.

```bash
cd backend/core
uv sync
uv run alembic upgrade head
```

## 3. Run the Discovery Scraper
The Discovery scraper parses the centralized Air Mobility Command (AMC) directory. It detects all active Space-A terminals, extracts their website URLs, and registers them in the database footprint so that documents can be searched later.

```bash
cd ../scraper
uv sync
uv run python scraper/main.py run-discovery
```

*This step runs very quickly and discovers ~60+ active passenger terminals.*

## 4. Run the Extraction Scraper
The Extraction scraper acts upon the terminals found during the discovery phase. It visits every individual terminal website, parses out the 72-hour schedules, 30-day schedules, and Roll Call reports, then dedupes and uploads the PDFs/Images directly to the local SeaweedFS bucket (`s3://localhost:8333/terminals`).

```bash
# Still in the backend/scraper directory
uv run python scraper/main.py run-extraction
```

*This downloads the raw document bytes, calculates a SHA-256 hash to prevent storing duplicate files, and securely streams them into the storage bucket.*

## Verify
If you completed the above steps, you can check the storage cluster for the newly downloaded PDFs:
* **SeaweedFS S3 Endpoint:** `http://localhost:8333`
* **Bucket name:** `terminals`
