from typing import Dict, List
from langchain.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

import logging

from requests import Session

from external.spacy import preprocess_query
from models.candidate import Candidate

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def initialize_vector_db(db_path: str = "chroma_db") -> Chroma:
    try:
        embedding_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"}  
        )
        vector_db = Chroma (
            persist_directory=db_path,
            embedding_function=embedding_model,
        )
        logger.info(f"Initialized vector DB at {db_path}")
        return vector_db
    except Exception as e:
        logger.error(f"Error initializing vector DB: {str(e)}")
        raise

def populate_vector_db(session: Session, vector_db: Chroma) -> None:
    try:
        candidates = session.query(Candidate).all()
        if not candidates:
            logger.info("No candidates found in database")
            return

        texts = []
        metadatas = []
        seen_candidate_ids = set()
        for candidate in candidates:
            if candidate.id in seen_candidate_ids:
                logger.debug(f"Skipping duplicate candidate ID: {candidate.id}")
                continue
            skills_text = ", ".join(candidate.skills) if candidate.skills else ""
            work_exp_text = "; ".join(
                [f"{w['company']} - {w['position']}: {w['description']}" 
                 for w in candidate.work_experience]
            ) if candidate.work_experience else ""
            combined_text = f"Skills: {skills_text}. Work Experience: {work_exp_text}"
            if combined_text.strip():
                logger.debug(f"Candidate {candidate.id} embedding text: {combined_text}")
                texts.append(combined_text)
                metadatas.append({
                    "candidate_id": candidate.id,
                    "full_name": candidate.full_name,
                    "email": candidate.email
                })

        if texts:
            vector_db.db.delete_collection()
            vector_db = initialize_vector_db()
            vector_db.add_texts(
                texts=texts,
                metadatas=metadatas
            )
            logger.info(f"Populated vector DB with {len(texts)} candidate embeddings")
        else:
            logger.info("No valid texts to embed")
    except Exception as e:
        logger.error(f"Error populating vector DB: {str(e)}")
        raise

def search_candidates(vector_db: Chroma, query: str, k: int = 3) -> List[Dict]:
    try:
        preprocessed_query = preprocess_query(query)
        results = vector_db.similarity_search_with_score(preprocessed_query, k=k * 2) 
        logger.debug(f"Raw search results for '{preprocessed_query}': {results}")
        
        seen_candidate_ids = {}
        for doc, score in results:
            candidate_id = doc.metadata["candidate_id"]
            if candidate_id not in seen_candidate_ids or score < seen_candidate_ids[candidate_id]["score"]:
                seen_candidate_ids[candidate_id] = {
                    "candidate_id": candidate_id,
                    "full_name": doc.metadata["full_name"],
                    "email": doc.metadata["email"],
                    "text": doc.page_content,
                    "score": score
                }
        
        deduped_results = list(seen_candidate_ids.values())[:k]  # Return top k
        logger.debug(f"Deduplicated search results: {deduped_results}")
        return deduped_results
    except Exception as e:
        logger.error(f"Error in similarity search: {str(e)}")
        return []