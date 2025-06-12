# CV Analysis System Development Journal

**Project**: A FastAPI-based CV analysis system for processing CVs and performing semantic search using ChromaDB, spaCy, and Gemini LLM.  
**Timeline**: June 9–12, 2025  
**Author**: Khoa Nguyen  
**Submission Deadline**: June 12, 2025

## Overview
The CV Analysis System processes CVs from local folders or Google Drive, extracts structured data (e.g., name, skills, experience), stores it in a PostgreSQL database, and enables semantic search for candidates based on skills or keywords (e.g., "java", "tech"). Key components include FastAPI endpoints, ChromaDB for vector search, spaCy for text preprocessing, and Gemini LLM for data extraction.

### June 4, 2025
- **Tasks**
  - Research Python/FastAPI
  - Set up PostgreSQL
  - Intergrate PyMuPDF lib for data extraction, analysis, conversion & manipulation of PDF
  - Developed CV processing module with PyMuPDF and gdown.

### June 5, 2025
- **Tasks**
  - Research LLM 
  - Intergrate SpaCy, Langchain
  - Design prompt for structured extraction (name, email, skills)
  - Completed candidate database, schema documentation
  - Created FastAPI endpoints for local and Google Drive CV processing.
  - Stored raw text in files and PostgreSQL.
  - Tested with 3-5 CV samples.

### June 6, 2025
- **Tasks**
  - Use spaCy/LLM to generate embeddings
  - Search: Compare job description embeddings with stored vectors.
  - Build information extraction module using Langchain and LLM.

### June 7, 2025
- **Tasks**
  - Involve a search endpoint candidates (e.g, by skills, workd experiences)
  - Test function with 3-5 cvs

### June 9, 2025
- **Tasks**:
  - Fixed `NameError` in `utils/spacy.py`.
  - Implemented `/process-cvs`, `/process_cv`, `/process_gdrive_cv`, and `/extract_info` endpoints.
  - Enhanced spaCy regex for Vietnamese names (e.g., Nguyễn, Trần).
  - Refined Gemini LLM prompt to handle Vietnamese terms (e.g., "Kỹ năng", "Giáo dục") and table-based CVs.
  - Fixed database saving to handle duplicate emails.
  - Generated `test_extraction_results.json` for 5+ CVs.
- **Challenges**:
  - Incorrect name extraction (e.g., skills like "Java" as names).
  - Empty fields in extracted data.
  - Null candidate IDs for invalid CVs.
- **Solutions**:
  - Added Vietnamese name regex near "Email" or "SĐT".
  - Updated LLM prompt for better field detection.
  - Implemented duplicate email checks in `save_candidate_to_db`.
- **Status**: Completed

### June 10, 2025
- **Tasks**:
  - Integrated ChromaDB for vector-based search.
  - Used `sentence-transformers/all-MiniLM-L6-v2` for embeddings.
  - Stored metadata (candidate_id, email, name) in ChromaDB.
  - Tested similarity searches for queries like "Python" and "SQL".
- **Challenges**:
  - Duplicate embeddings for candidates
### June 11, 2025
- **Tasks**:
  - Implemented `/search` endpoint for semantic search.
  - Handled Vietnamese queries (e.g., "Kỹ năng") and misspellings (e.g., "Pythn" → "Python").
### June 11–12, 2025
- **Tasks**:
  - Fixed infinite loop in `preprocess_query` (`external/spacy.py`) causing `/search` to hang.
  - Addressed ChromaDB collection error (`Collection does not exist`) in `populate_vector_db`.
  - Conducted comprehensive code review, fixing logging inconsistencies, SQLite references, and validation logic.
  - Prepared API documentation (`README.md`) and submission package.
- **Challenges**:
  - Invalid phone number validation rejected valid formats.
  - Noted OCR for table CVs as a future improvement.