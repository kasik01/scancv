from sqlite3 import IntegrityError
from typing import Dict, List, Optional
from venv import logger
from requests import Session
from sqlalchemy import ARRAY, JSON, Column, DateTime, Integer, String, Text, ForeignKey
from database.db import Base
from pydantic import BaseModel
from sqlalchemy.orm import relationship
from datetime import datetime

class Candidate(Base):
    __tablename__ = "candidates"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    phone = Column(String(50), nullable=True)

    education = Column(JSON, default=[])
    work_experience = Column(JSON, default=[])
    skills = Column(ARRAY(String), default=[])
    projects = Column(JSON, default=[])
    certifications = Column(ARRAY(String), default=[])

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    raw_cv_id = Column(Integer, ForeignKey("raw_cv.id"), nullable=True)
    raw_cv = relationship("RawCV", back_populates="candidate")

def save_candidate_to_db(session: Session, extracted_data: Dict, raw_cv_id: int) -> Optional[int]:
    try:
        existing_candidate = session.query(Candidate).filter(Candidate.email == extracted_data["email"]).first()
        if existing_candidate:
            logger.info(f"Candidate with email {extracted_data['email']} already exists, ID: {existing_candidate.id}")
            existing_candidate.raw_cv_id = raw_cv_id
            existing_candidate.full_name = extracted_data["full_name"]
            existing_candidate.phone = extracted_data["phone"]
            existing_candidate.education = extracted_data.get("education", [])
            existing_candidate.work_experience = extracted_data.get("work_experience", [])
            existing_candidate.skills = extracted_data.get("skills", [])
            existing_candidate.projects = extracted_data.get("projects", [])
            existing_candidate.certifications = extracted_data.get("certifications", [])
            session.commit()
            return existing_candidate.id
        candidate = Candidate(
            full_name=extracted_data["full_name"],
            email=extracted_data["email"],
            phone=extracted_data["phone"],
            education=extracted_data.get("education", []),
            work_experience=extracted_data.get("work_experience", []),
            skills=extracted_data.get("skills", []),
            certifications=extracted_data.get("certifications", []),
            projects=extracted_data.get("projects", []),
            raw_cv_id=raw_cv_id
        )
        session.add(candidate)
        session.commit()
        logger.info(f"Saved candidate {extracted_data['full_name']}, ID: {candidate.id}")
        return candidate.id
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Duplicate email: {str(e)}")
        return None
    except Exception as e:
        session.rollback()
        logger.error(f"Error saving candidate: {str(e)}")
        return None
    
# Pydantic models
class CVInput(BaseModel):
    folder_path: Optional[str] = None
    gdrive_url: Optional[str] = None

class SearchCriteria(BaseModel):
    keywords: str
    skills: List[str] = []

class SearchInput(BaseModel):
    query: str
    top_k: Optional[int] = None