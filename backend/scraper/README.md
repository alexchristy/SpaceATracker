# Scraper

Background workers that discover and extract Space-A terminal data from the AMC website.

## Discovery Scraper

The discovery scraper fetches the [AMC Space-A directory page](https://www.amc.af.mil/AMC-Travel-Site/AMC-Space-Available-Travel-Page/), parses every terminal listing from the accordion menu, and upserts each `MilitaryAirport` into PostgreSQL. It is designed to run as a one-shot worker — execute, sync the database, then exit.

### Environment Variables

| Variable              | Description                          | Default                                                                        |
| --------------------- | ------------------------------------ | ------------------------------------------------------------------------------ |
| `DATABASE_URL`        | Async PostgreSQL connection string   | `postgresql+asyncpg://spaceatracker:password@localhost:5432/spaceatracker`      |
| `MAIN_DIRECTORY_URL`  | URL of the AMC Space-A directory     | `https://www.amc.af.mil/AMC-Travel-Site/AMC-Space-Available-Travel-Page/`      |
| `LOG_LEVEL`           | Python log level (`DEBUG`, `INFO`, …)| `INFO`                                                                         |

All variables can also be set in a `.env` file at the scraper package root.

### Local Development (Docker)

1. **Start the local Postgres container** from the repo root:

   ```bash
   docker compose up -d postgres
   ```

2. **Install dependencies** (from `backend/scraper/`):

   ```bash
   uv sync
   ```

3. **Run the discovery worker:**

   ```bash
   uv run python -m scraper.main run-discovery
   ```

   No extra config is needed — the defaults connect to the Docker Postgres container on `localhost:5432`.

### Cloud / Managed PostgreSQL

Set `DATABASE_URL` to your managed Postgres instance's async connection string:

```bash
export DATABASE_URL="postgresql+asyncpg://<user>:<password>@<host>:5432/<db>"
```

Then run the worker exactly the same way:

```bash
uv run python -m scraper.main run-discovery
```
