from database.db import Base, engine
from models.candidate import Candidate
from models.raw_cv import RawCV

Base.metadata.create_all(bind=engine)