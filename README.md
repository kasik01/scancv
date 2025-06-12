# CV Analysis System
A FastAPI-based system for processing CVs and performing semantic search.

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Configure `.env` with `GEMINI_API_URL` and `GEMINI_API_KEY` and `DATABASE_URL`
3. Connect DB `python -m database.init_db`
4. Run: `uvicorn main:app --host 0.0.0.0 --port 8000`

## Endpoints
- POST /process-cvs: Process CVs from folder or Google Drive.
- POST /search: Search candidates by query (e.g., "java").
- GET /candidates: List all candidates.

## Files
- main.py: FastAPI application
- external/chroma.py: ChromaDB integration
- external/spacy.py: Text preprocessing
- cv_processing/: CV extraction logic
- models/: Database models
- database/db.py: Database setup
- test_extraction_results.json: CV extraction output
- journal.txt: Development log