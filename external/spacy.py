import re
from typing import Dict
from venv import logger
import spacy
from spacy.matcher import Matcher
import unidecode

nlp = spacy.load("en_core_web_sm")
skill_patterns = [
    [{"LOWER": {"in": ["python", "pythn", "pytn"]}}],
    [{"LOWER": {"in": ["javascript", "jvascript", "js"]}}],
    [{"LOWER": {"in": ["sql", "squel"]}}],
    [{"LOWER": {"in": ["java", "jva"]}}],
    [{"LOWER": {"in": ["aws", "awz"]}}]
]
matcher = Matcher(nlp.vocab)
for pattern in skill_patterns:
    matcher.add("SKILL", [pattern])

def preprocess_text(raw_text: str) -> str:
    try:
        return unidecode.unidecode(raw_text)
    except Exception as e:
        logger.error(f"Error preprocessing text: {str(e)}")
        return raw_text
    
def preprocess_query(query: str) -> str:
    try:
        logger.debug(f"Original query: {query}")
        normalized = query
        doc = nlp(normalized.lower())
        corrected = []
        matches = matcher(doc)
        token_positions = {start: (doc[start:end].text, end) for _, start, end in matches}
        original_tokens = nlp(query)
        corrections = {
            "pythn": "Python", "pytn": "Python",
            "jvascript": "JavaScript", "js": "JavaScript",
            "squel": "SQL",
            "jva": "Java",
            "awz": "AWS"
        }

        i = 0
        while i < len(doc):
            if i in token_positions:
                skill = token_positions[i][0].lower()
                corrected_skill = corrections.get(skill, original_tokens[i].text)
                logger.debug(f"Corrected skill: {skill} -> {corrected_skill}")
                corrected.append(corrected_skill)
                i = token_positions[i][1]
            else:
                corrected.append(original_tokens[i].text)
                i += 1
        result = " ".join(corrected)
        logger.info(f"Preprocessed query: {result}")
        return result
    except Exception as e:
        logger.error(f"Error preprocessing query: {str(e)}")
        return query

def extract_with_spacy(raw_text: str) -> dict:
    try:
        doc = nlp(raw_text)
        result = {
            "full_name": "",
            "email": "",
            "phone": "",
            "skills": []
        }
        for ent in doc.ents:
            if ent.label_ == "PERSON" and not result["full_name"]:
                result["full_name"] = ent.text
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", raw_text)
        if email_match:
            result["email"] = email_match.group(0)
        phone_match = re.search(r"(\+?\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4})", raw_text)
        if phone_match:
            result["phone"] = phone_match.group(0)
        matches = matcher(doc)
        for match_id, start, end in matches:
            skill = doc[start:end].text
            corrections = {
                "pythn": "Python", "pytn": "Python",
                "jvascript": "JavaScript", "js": "JavaScript",
                "squel": "SQL",
                "jva": "Java",
                "awz": "AWS"
            }
            result["skills"].append(corrections.get(skill.lower(), skill.capitalize()))
        result["skills"] = list(set(result["skills"]))
        logger.info("Extracted with spaCy")
        return result
    except Exception as e:
        logger.error(f"Error extracting with spaCy: {str(e)}")
        return {
            "full_name": "",
            "email": "",
            "phone": "",
            "skills": []
        }
