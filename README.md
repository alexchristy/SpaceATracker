# SpaceATracker

Discover, track, and fly Space Available flights.

## Architecture Overview

* **Runtime:** Go (compiled binary in distroless container)
* **Backing Services:** PostgresSQL 18

## Prerequisites

* [Docker](https://docs.docker.com/get-started/get-docker/) (v29.4)
* [Docker Compose](https://docs.docker.com/compose/install/) (v5.1+)
* [Go](https://go.dev/doc/install) (1.26+ for local development)

## Quick Start

```bash
# 1. Configure env vars 
cp .env.example .env
vim .env

# 2. Start app
docker compose up --build -d

# 3. Tear down
docker compose down -v
```

## Tests

```bash
go test -cover -race -shuffle=on ./...
```

## Linting

```bash
golangci-lint run
```
