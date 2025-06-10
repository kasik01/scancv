import json
import logging
from typing import Dict, List
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, logger
from sqlalchemy.orm import Session
from cv_processing.info_extractor import extract_info_with_llm, validate_extracted_data
from external.chroma import initialize_vector_db, populate_vector_db, search_candidates
from models.candidate import CVInput, Candidate, SearchInput, save_candidate_to_db
from models.raw_cv import RawCV
from database.db import get_db
from cv_processing.pdf_reader import extract_text_from_pdf, download_and_extract_from_gdrive, process_local_cv_folder, save_raw_text
import os
import tempfile

from external.spacy import extract_with_spacy

app = FastAPI()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

vector_db = initialize_vector_db("chroma_db")

@app.get("/")
async def root():
    return {"message": "CV Analysis System"}

@app.post("/process_cv")
async def process_cv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF only")
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_file.write(await file.read())
            text = extract_text_from_pdf(temp_file.name)
        if not text:
            raise HTTPException(status_code=400, detail="Failed to extract text from PDF")
        output_path = save_raw_text(file.filename, text)
        raw_cv = RawCV(filename=file.filename, raw_text=text)
        db.add(raw_cv)
        db.commit()
        db.refresh(raw_cv)
        spacy_data = extract_with_spacy(text)
        extracted = extract_info_with_llm(text, spacy_data)
        is_valid = validate_extracted_data(extracted)
        candidate_id = save_candidate_to_db(db, extracted, raw_cv.id) if is_valid else None
        if candidate_id:
            populate_vector_db(db, vector_db) 
        return {
            "filename": file.filename,
            "text": text[:200],
            "saved_path": output_path,
            "db_id": raw_cv.id,
            "extracted_data": extracted,
            "is_valid": is_valid,
            "candidate_id": candidate_id
        }
    except Exception as e:
        logger.error(f"Error processing CV: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_file.name):
            os.remove(temp_file.name)


@app.post("/process_gdrive_cv")
async def process_gdrive_cv(url: str, db: Session = Depends(get_db)):
    result = download_and_extract_from_gdrive(url)
    if not result["text"]:
        raise HTTPException(status_code=400, detail="Failed to extract text from Google Drive PDF")
    output_path = save_raw_text(result["filename"], result["text"])
    raw_cv = RawCV(filename=result["filename"], raw_text=result["text"])
    db.add(raw_cv)
    db.commit()
    db.refresh(raw_cv)
    spacy_data = extract_with_spacy(result["text"])
    extracted = extract_info_with_llm(result["text"], spacy_data)
    is_valid = validate_extracted_data(extracted)
    candidate_id = save_candidate_to_db(db, extracted, raw_cv.id) if is_valid else None
    if candidate_id:
        populate_vector_db(db, vector_db)
    return {
        "filename": result["filename"],
        "text": result["text"][:200],
        "saved_path": output_path,
        "db_id": raw_cv.id,
        "extracted_data": extracted,
        "is_valid": is_valid,
        "candidate_id": candidate_id
    }     

@app.post("/extract_info")
async def extract_info(cv_id: int, db: Session = Depends(get_db)):
    try:
        raw_cv = db.query(RawCV).filter(RawCV.id == cv_id).first()
        if not raw_cv:
            logger.error(f"CV ID {cv_id} not found")
            raise HTTPException(status_code=404, detail="CV not found")
        spacy_data = extract_with_spacy(raw_cv.raw_text)
        info = extract_info_with_llm(raw_cv.raw_text, spacy_data)
        if not validate_extracted_data(info):
            logger.error("Invalid extraction result")
            raise HTTPException(status_code=400, detail="Failed to extract valid candidate info")
        existing_candidate = db.query(Candidate).filter(Candidate.email == info["email"]).first()
        if existing_candidate:
            logger.info(f"Candidate exists with email {info['email']}, ID: {existing_candidate.id}")
            return {"candidate_id": existing_candidate.id, "info": info}
        candidate_id = save_candidate_to_db(db, info, cv_id)
        if not candidate_id:
            raise HTTPException(status_code=500, detail="Failed to save candidate")
        populate_vector_db(db, vector_db) 
        logger.info(f"Extracted candidate info for CV ID {cv_id}, saved candidate ID {candidate_id}")
        return {"candidate_id": candidate_id, "info": info}
    except Exception as e:
        db.rollback()
        logger.error(f"Error extracting info: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
@app.post("/process-cvs")
async def process_cvs(cv_input: CVInput, db: Session = Depends(get_db)):
    if not cv_input.folder_path and not cv_input.gdrive_url:
        raise HTTPException(status_code=400, detail="Provide folder_path or gdrive_url")
    results = []
    if cv_input.folder_path:
        try:
            cv_data = process_local_cv_folder(cv_input.folder_path)
            for cv in cv_data:
                raw_cv = RawCV(filename=cv["filename"], raw_text=cv["text"])
                db.add(raw_cv)
                db.commit()
                db.refresh(raw_cv)
                spacy_data = extract_with_spacy(cv["text"])
                extracted = extract_info_with_llm(cv["text"], spacy_data)
                is_valid = validate_extracted_data(extracted)
                candidate_id = save_candidate_to_db(db, extracted, raw_cv.id) if is_valid else None
                results.append({
                    "filename": cv["filename"],
                    "extracted_data": extracted,
                    "is_valid": is_valid,
                    "candidate_id": candidate_id,
                    "raw_cv_id": raw_cv.id
                })
                if any(r["candidate_id"] for r in results):
                    populate_vector_db(db, vector_db)  # Update embeddings
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error processing folder: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    if cv_input.gdrive_url:
        try:
            result = download_and_extract_from_gdrive(cv_input.gdrive_url)
            raw_cv = RawCV(filename=result["filename"], raw_text=result["text"])
            db.add(raw_cv)
            db.commit()
            db.refresh(raw_cv)
            spacy_data = extract_with_spacy(result["text"])
            extracted = extract_info_with_llm(result["text"], spacy_data)
            is_valid = validate_extracted_data(extracted)
            candidate_id = save_candidate_to_db(db, extracted, raw_cv.id) if is_valid else None
            results.append({
                "filename": result["filename"],
                "extracted_data": extracted,
                "is_valid": is_valid,
                "candidate_id": candidate_id,
                "raw_cv_id": raw_cv.id
            })
            if candidate_id:
                populate_vector_db(db, vector_db)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error processing Google Drive CV: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    try:
        with open("test_extraction_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4)
        logger.info("Results saved to test_extraction_results.json")
    except Exception as e:
        logger.error(f"Error saving JSON: {str(e)}")
    return results

@app.post("/search")
async def search(search_input: SearchInput, db: Session = Depends(get_db)):
    try:
        if not search_input.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        results = search_candidates(vector_db, search_input.query, k=search_input.top_k)
        response = []
        for result in results:
            candidate = db.query(Candidate).filter(Candidate.id == result["candidate_id"]).first()
            if candidate:
                response.append({
                    "candidate_id": candidate.id,
                    "full_name": candidate.full_name,
                    "email": candidate.email,
                    "phone": candidate.phone,
                    "skills": candidate.skills,
                    "work_experience": candidate.work_experience,
                    "education": candidate.education,
                    "projects": candidate.projects,
                    "certifications": candidate.certifications,
                    "similarity_score": result["score"]
                })
        logger.info(f"Search query: {search_input.query}, found {len(response)} candidates")
        return {"results": response}
    except Exception as e:
        logger.error(f"Error searching candidates: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/candidates")
def get_candidates(db: Session = Depends(get_db)):
    candidates = db.query(Candidate).all()
    return candidates

@app.get("/candidates/{id}")
def get_candidate(id: int, db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter(Candidate.id == id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate

@app.get("/raw_cv/{cv_id}")
def get_raw_cv(cv_id: int, db: Session = Depends(get_db)):
    raw_cv = db.query(RawCV).filter(RawCV.id == cv_id).first()
    if not raw_cv:
        raise HTTPException(status_code=404, detail="Raw CV not found")
    return raw_cv

