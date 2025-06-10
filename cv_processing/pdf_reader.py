import re
from typing import Dict, List
from venv import logger
from fastapi import HTTPException
import fitz
import os
import gdown
import tempfile
from pathlib import Path

def extract_gdrive_id(url: str) -> str:
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    raise ValueError("Invalid Google Drive URL")

def extract_text_from_pdf(pdf_path: str) -> str:
    try:
        doc = fitz.open(pdf_path)
        text = "".join(page.get_text("text") for page in doc)
        doc.close()
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting PDF text: {str(e)}")
        return ""

def process_local_cv_folder(folder_path: str) -> List[Dict]:
    folder = Path(folder_path)
    if not folder.exists():
        raise HTTPException(status_code=404, detail="Folder not found")
    results = []
    for file in folder.glob("*.pdf"):
        try:
            text = extract_text_from_pdf(str(file))
            results.append({"filename": file.name, "text": text})
        except Exception as e:
            logger.error(f"Error processing {file.name}: {str(e)}")
    return results

def download_and_extract_from_gdrive(url: str) -> Dict:
    try:
        file_id = extract_gdrive_id(url)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            gdown.download(url, temp_file.name, quiet=False, fuzzy=True)
            text = extract_text_from_pdf(temp_file.name)
            filename = f"{file_id}.pdf"
            return {"filename": filename, "text": text}
    except Exception as e:
        logger.error(f"Error downloading from Google Drive: {str(e)}")
        raise
    finally:
        if 'temp_file' in locals() and os.path.exists(temp_file.name):
            os.remove(temp_file.name)

def save_raw_text(filename: str, text: str, output_dir: str = "temp") -> str:
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{filename}.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    return output_path