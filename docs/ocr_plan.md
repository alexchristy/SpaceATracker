# OCR Implementation Plan - Task Tracker

## Phase 1: Core Implementation

### 1. Dependencies, Configuration, and Schemas
- [~] Add `google-genai` dependency to `backend/scraper/pyproject.toml`
- [~] Add `GEMINI_API_KEY` to `Settings` in `scraper/core/config.py`
- [~] Create `backend/core/core/schemas/flight.py` with extraction schemas

### 2. OCR Service Layer
- [ ] Create `scraper/ocr/prompt.py` with system instruction
- [ ] Create `scraper/ocr/client.py` with `GeminiOCRClient`
- [ ] Create `scraper/ocr/pipeline.py` with `FlightProcessingPipeline`
- [ ] Create `scraper/ocr/service.py` with `OCRService`

### 3. Integration
- [ ] Integrate `OCRService` into `ExtractionService`

## Phase 2: Eval Suite
- [ ] Create eval assets directory structure
- [ ] Create `test_ocr_evals.py` scaffolding
