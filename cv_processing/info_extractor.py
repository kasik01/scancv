import json
import os
import re
from sqlite3 import IntegrityError
from dotenv import load_dotenv
import requests
import logging
from typing import Dict, Optional

from cv_processing.pdf_reader import download_and_extract_from_gdrive, process_local_cv_folder
from external.spacy import preprocess_text
from models.candidate import Candidate

load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

GEMINI_API_URL = os.getenv("GEMINI_API_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  

def extract_info_with_llm(raw_text: str, spacy_data: Dict) -> Dict:
    try:
        processed_text = preprocess_text(raw_text)
        headers = {"Content-Type": "application/json"}
        prompt = (
            "Extract structured information from the CV text, handling Vietnamese terms (e.g., 'Kỹ năng' or 'Ky nang' for skills, 'Giáo dục' or 'Giao duc' for education, 'Kinh nghiệm làm việc' or 'Kinh nghiem lam viec' for work experience) and misspellings (e.g., 'Pythn' to 'Python'). Return a JSON object with exact field names. If a field is missing, use empty string or list. Use spaCy data as fallback. Guidelines:\n"
            "- full_name: Full name (e.g., 'Nguyễn Văn A' or 'John Doe'), avoid skills like 'Java'.\n"
            "- email: Email address (e.g., 'example@gmail.com').\n"
            "- phone: Phone number (e.g., '+84123456789' or '123-456-7890').\n"
            "- education: List of objects with {degree: string, institution: string, year: string}.\n"
            "- work_experience: List of objects with {company: string, position: string, duration: string (e.g., '2021-2023'), description: string, achievements: list of strings}.\n"
            "- skills: List of strings, split comma-separated, correct misspellings (e.g., 'Pythn' to 'Python').\n"
            "- projects: List of objects with {name: string, description: string}.\n"
            "- certifications: List of strings (e.g., 'AWS Certified Developer').\n"
            "Ensure full_name is a person's name, not a skill. Look for Vietnamese name patterns (e.g., Nguyễn, Trần) near 'Email' or 'SĐT'. Handle table-based CVs.\n"
            f"SpaCy Data: {json.dumps(spacy_data)}\n"
            f"CV Text: {processed_text[:6000]}"
        )
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.3,
                "maxOutputTokens": 2000
            }
        }
        response = requests.post(
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
            headers=headers,
            json=data,
        )
        response.raise_for_status()
        result = json.loads(response.json()["candidates"][0]["content"]["parts"][0]["text"])
        result["full_name"] = result.get("full_name") or spacy_data.get("full_name", "")
        result["email"] = result.get("email") or spacy_data.get("email", "")
        result["phone"] = result.get("phone") or spacy_data.get("phone", "")
        result["skills"] = result.get("skills", []) or spacy_data.get("skills", [])
        logger.info("Extracted with LLM and spaCy")
        return result
    except Exception as e:
        logger.error(f"Error extracting with LLM: {str(e)}")
        return {
            "full_name": spacy_data.get("full_name", ""),
            "email": spacy_data.get("email", ""),
            "phone": spacy_data.get("phone", ""),
            "education": [],
            "work_experience": [],
            "skills": spacy_data.get("skills", []),
            "projects": [],
            "certifications": []
        }

def validate_extracted_data(data: Dict) -> bool:
    try:
        if not data.get("full_name", "").strip() or data["full_name"].lower() in ["java", "python", "sql", "javascript", "aws"]:
            logger.warning("Invalid or missing full_name")
            return False
        email = data.get("email", "")
        if not email or not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            logger.warning(f"Invalid email: {email}")
            return False
        phone = data.get("phone", "")
        if phone and not re.match(r"^\+?\d[\d\s-]{7,}$", phone):
            logger.warning(f"Invalid phone: {phone}")
        for field in ["education", "work_experience", "skills", "projects", "certifications"]:
            if not isinstance(data.get(field, []), list):
                logger.warning(f"Invalid {field}: expected list")
                return False
        if not data.get("skills", []):
            logger.warning("Empty skills list")
            return False
        logger.info("Data validated")
        return True
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        return False
