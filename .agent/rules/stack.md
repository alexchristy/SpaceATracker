---
trigger: always_on
---

# Monorepo Constraints
- **Architecture:** Maintain strict domain isolation. Python code lives in `/scraper`, SvelteKit code lives in `/frontend`.
- **Backend (Scraper):** Python 3.14+. Use `uv` for dependency management. Strict async I/O using `aiohttp` and `selectolax`. The scraper runs as a stateless, event-driven Docker worker.
- **Code Quality:** Use `ruff` exclusively for linting and formatting. Use `ty` exclusively for static type checking.
- **Frontend:** SvelteKit using strict TypeScript.
- **Security:** Do not run Docker containers as root.

# Data Validation & Serialization (Pydantic)
- **Strict Adherence:** All data entering or exiting the application must be validated via Pydantic V2 `BaseModel` classes. Raw dictionaries are strictly forbidden for data transfer.
- **Type Hinting:** Use standard Python type hints (e.g., `list[str]`, `str | None`) within Pydantic models. Do not use the legacy `typing` module imports (like `List` or `Optional`) as we are on Python 3.14.
- **Advanced Validation:** For field-level constraints (e.g., ensuring a scraped URL is valid, or stripping whitespace from an extracted title), you must use Pydantic's `Annotated` combined with `Field` or `AfterValidator`.
- **Serialization:** When sending the scraped payload to the database or frontend, always use `model_dump(mode='json')` to ensure datetime objects and nested models are properly serialized.