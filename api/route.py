from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.db import SessionLocal
from models.candidate import Candidate

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/candidates")
def get_candidates(db: Session = Depends(get_db)):
    return db.query(Candidate).all()
