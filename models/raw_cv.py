from sqlalchemy import Column, Integer, String, Text
from database.db import Base
from sqlalchemy.orm import relationship

class RawCV(Base):
    __tablename__ = "raw_cv"
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    raw_text = Column(Text, nullable=False)

    candidate = relationship("Candidate", back_populates="raw_cv", uselist=False)