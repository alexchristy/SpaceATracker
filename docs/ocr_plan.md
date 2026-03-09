# OCR Implementation Plan - Task Tracker

## Phase 1: Core Implementation

### 1. Dependencies, Configuration, and Schemas
- [x] Add `google-genai` dependency to `backend/scraper/pyproject.toml` `bda6ae0`
- [x] Add `GEMINI_API_KEY` to `Settings` in `scraper/core/config.py` `bda6ae0`
- [x] Create `backend/core/core/schemas/flight.py` with extraction schemas `bda6ae0`

### 2. OCR Service Layer
- [x] Create `scraper/ocr/prompt.py` with system instruction `de7cb56`
- [x] Create `scraper/ocr/client.py` with `GeminiOCRClient` `de7cb56`
- [x] Create `scraper/ocr/pipeline.py` with `FlightProcessingPipeline` `de7cb56`
- [x] Create `scraper/ocr/service.py` with `OCRService` `de7cb56`

### 3. Integration
- [~] Integrate `OCRService` into `ExtractionService`

## Phase 2: Eval Suite
- [ ] Create eval assets directory structure
- [ ] Create `test_ocr_evals.py` scaffolding
