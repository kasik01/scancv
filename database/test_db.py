# database/test_db.py
from sqlalchemy.orm import Session
from sqlalchemy import text
from database.db import get_db

def test_connection():
    db: Session = next(get_db())
    db.execute(text("SELECT 1"))
    print("PostgreSQL connected successfully!")

if __name__ == "__main__":
    test_connection()