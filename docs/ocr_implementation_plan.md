# Implement OCR Phase with Gemini 3 Flash

This plan details the implementation of the OCR phase for SpaceATracker, utilizing Gemini 3 Flash to automatically extract structured flight data from documents (PDFs, PPTX, Images) scraped from military passenger terminals.

## User Review Required

> [!IMPORTANT]
> **Dependency Addition:** We will add `google-genai` to `backend/scraper/pyproject.toml` to interact with the new Gemini API.

> [!NOTE]
> **Data Processing Pipeline:** After the LLM extracts raw strings into Pydantic models for strict validation, the data will pass through an intermediate "Processing Pipeline". This flexible middleware pattern allows for dynamically adding future enrichment steps (like deduplication and geocoding) without modifying core OCR logic. For now, this pipeline will act as a simple pass-through before the data is transformed into database models and saved.

## Proposed Changes

### 1. Dependencies, Configuration, and Schemas

#### [MODIFY] [pyproject.toml](file:///home/alex/SpaceATracker/backend/scraper/pyproject.toml)
- Add `google-genai` to the `dependencies` list.

#### [MODIFY] [config.py](file:///home/alex/SpaceATracker/backend/scraper/scraper/core/config.py)
Update the backend settings model to securely handle the Gemini API Key.
```python
class Settings(BaseSettings):
    # ... existing settings
    GEMINI_API_KEY: str = Field(..., description="API key for Gemini API")
```
- Add `google-genai` to the `dependencies` list.

#### [NEW] [flight.py](file:///home/alex/SpaceATracker/backend/core/core/schemas/flight.py)
Create Pydantic models dedicated to the raw LLM extraction, and a separate model representing the enriched data after it passes through the pipeline.

```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from core.enums.seats import SeatStatus

class FlightExtraction(BaseModel):
    """Strictly the raw data extracted by the LLM."""
    roll_call_time: datetime
    raw_seats: str
    raw_origin: str
    raw_destination: str

class FlightExtractionList(BaseModel):
    flights: list[FlightExtraction]
    
class ProcessedFlight(FlightExtraction):
    """The enriched flight data ready for database insertion."""
    origin_id: str | None = None
    destination_id: str | None = None
    seats_available: int | None = None
    seat_status: SeatStatus | None = None
    model_config = ConfigDict(from_attributes=True)
```

### 2. OCR Service Layer

#### [NEW] [prompt.py](file:///home/alex/SpaceATracker/backend/scraper/scraper/ocr/prompt.py)
Define the system instruction following Gemini 3 Flash best practices:
- Define the persona (Aviation Data Extraction Assistant).
- Provide explicit instructions on handling edge cases (e.g., rolling days, "TBD" seats).
- **Explicit Instruction:** Ignore multi-leg flights. Treat them as a single destination flight, taking the first destination listed as the final/only destination.

#### [NEW] [client.py](file:///home/alex/SpaceATracker/backend/scraper/scraper/ocr/client.py)
Create an async `GeminiOCRClient` wrapper:
- Accepts raw file bytes and `mime_type`.
- Uses the `google_genai.Client` initialized using the securely loaded `settings.GEMINI_API_KEY` to upload the document using the Gemini File API.
- Prompts the model with the system instruction and uses `response_schema=FlightExtractionList` to guarantee the output perfectly matches our Pydantic classes.

#### [NEW] [pipeline.py](file:///home/alex/SpaceATracker/backend/scraper/scraper/ocr/pipeline.py)
Create a processing pipeline architecture (`FlightProcessingPipeline`):
- A standard interface `FlightProcessor(Protocol)` with an `async def process_batch(self, flights: list[ProcessedFlight]) -> list[ProcessedFlight]:` method.
- The pipeline will initialize all `FlightExtraction` objects into `ProcessedFlight` objects, and then accept a list of registered processors and pass the batch sequentially through each one.
- For now, we will add a trivial processor that simply passes the batch through, but in the future, we can add a `GeocodingProcessor` (to map `raw_origin` to `origin_id`) and a `SeatParsingProcessor` (to map `raw_seats` to `seats_available` and `seat_status`).

#### [NEW] [service.py](file:///home/alex/SpaceATracker/backend/scraper/scraper/ocr/service.py)
Create the `OCRService`:
- Orchestrates the flow: takes a `TerminalDocument` record and its raw bytes.
- Calls `GeminiOCRClient` to get the strictly validated `FlightExtractionList`.
- Passes the validated list through the `FlightProcessingPipeline` yielding `list[ProcessedFlight]`.
- Maps the processed extractions into SQLAlchemy `Flight` models, mapping the enriched fields (`origin_id`, `seats_available`, etc.) along with the raw fields.
- Commits the new rows to the PostgreSQL database.

### 3. Integration into Extraction Workflow

#### [MODIFY] [service.py](file:///home/alex/SpaceATracker/backend/scraper/scraper/extraction/service.py)
Update the `ExtractionService` pipeline. Immediately after a new document is downloaded, hashed, and successfully inserted into `terminal_documents`, pass the raw bytes directly to the `OCRService` to extract and store the flights, completing the pipeline "loud and early."

### Phase 2: Eval Suite (Ground Truth Testing)

Following the exact data-driven testing pattern from the extraction pipeline, we will build a dedicated "Eval" suite that physically queries the Gemini API using human-verified ground-truth documents. This suite will be built *strictly after* Phase 1 is complete and will be isolated from normal CI runs.

#### 1. Setup Eval Assets Directory
```text
backend/scraper/tests/ocr/evals/assets/
├── 09032026/                        ← snapshot dated DDMMYYYY
│   ├── ground_truth_09032026.json   ← ground-truth JSON containing expected `FlightExtractionList` structures
│   ├── travis-afb_72hr.pdf          ← raw document bytes
│   └── …other documents
```
- The `ground_truth.json` will map the filenames of the documents in the directory to their exact, manually-verified `FlightExtractionList` output.
- **NOTE:** The user will manually populate these assets and the ground-truth JSON data. The agent is only responsible for the test scaffolding.

#### 2. Eval Test Scaffolding
- **[NEW] [test_ocr_evals.py](file:///home/alex/SpaceATracker/backend/scraper/tests/ocr/evals/test_ocr_evals.py)**
    - Implement a pytest suite that automatically discovers all snapshots and documents within the `assets/` directory.
    - Create a test parameterizing over each document, passing its bytes to the live `GeminiOCRClient`, and asserting that the parsed payload matches the `ground_truth.json`.
    - Mark these tests with a custom marker (e.g., `@pytest.mark.live_llm`) so they are explicitly excluded from standard `uv run pytest` runs to save time and API costs.

## Verification Plan

### Automated Tests
1. **OCR Client Mocking:** Create a test in `backend/scraper/tests/ocr/test_service.py` that mocks the `google-genai` client response with a valid JSON string mapping to `FlightExtractionList`. Ensure the `OCRService` parses it via Pydantic and successfully translates it to SQLAlchemy `Flight` objects without crashing.
2. **Commands:** 
   ```bash
   cd /home/alex/SpaceATracker/backend/scraper
   uv run pytest tests/ocr/ -v
   ```

### Manual Verification
1. Run the local storage and database infrastructure (`docker-compose up -d`).
2. Run the extraction scraper against real live terminal websites:
   ```bash
   cd /home/alex/SpaceATracker/backend/scraper
   uv run python scraper/main.py run-extraction
   ```
3. Inspect the PostgreSQL database via a tool like `psql` or `pgAdmin` to manually verify that the `flights` table contains new rows correctly linked to `terminal_documents` with populated `raw_origin`, `raw_destination`, and `roll_call_time`.
