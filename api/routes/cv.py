"""CV upload and extraction endpoints."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import Optional
import json
from api.dependencies import get_user_id
from tools.db import execute_query

router = APIRouter()


@router.post("/upload")
async def upload_cv(
    file: UploadFile = File(...),
    user_id: str = Depends(get_user_id)
):
    """
    Upload and extract CV data using LLM.

    Accepts PDF file, extracts text, sends to Groq LLM for parsing.
    Returns extracted profile data (skills, roles, experience, education, etc).
    """
    try:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

        # Read file content
        contents = await file.read()
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="File is empty")

        # Extract text from PDF
        pdf_text = extract_pdf_text(contents)
        if not pdf_text or len(pdf_text.strip()) < 100:
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")

        print(f"[CV UPLOAD] Extracted {len(pdf_text)} characters from PDF for user {user_id}", flush=True)

        # Extract structured data using LLM
        extracted_data = extract_cv_data(pdf_text)

        print(f"[CV UPLOAD] Extracted profile: {json.dumps(extracted_data, indent=2)}", flush=True)

        return {
            "status": "success",
            "extracted_data": extracted_data,
            "raw_text_length": len(pdf_text)
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[CV UPLOAD] ERROR: {str(e)}", flush=True)
        raise HTTPException(status_code=500, detail=f"Failed to process CV: {str(e)}")


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes using pdfplumber."""
    try:
        import pdfplumber
        import io

        pdf_file = io.BytesIO(pdf_bytes)
        text = ""

        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        return text
    except ImportError:
        raise HTTPException(status_code=500, detail="pdfplumber not installed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF extraction failed: {str(e)}")


def clean_roles(roles: list) -> list:
    """
    Clean extracted roles by removing special characters, splitting compounds, and mapping to known titles.

    - Removes: |, ·, —, →, etc.
    - Splits: "Robotics | AI Engineer" → ["Robotics Engineer", "AI Engineer"]
    - Maps: "Roboticist" → "Robotics Engineer", etc.
    - Filters: Keeps only known job titles
    """
    KNOWN_ROLES = {
        "Robotics Engineer",
        "AI Engineer",
        "Embedded Systems Engineer",
        "ROS2 Developer",
        "Software Engineer",
        "Machine Learning Engineer",
        "Computer Vision Engineer",
        "Systems Engineer",
        "Firmware Engineer",
    }

    ROLE_MAPPINGS = {
        "roboticist": "Robotics Engineer",
        "robotics": "Robotics Engineer",
        "ai engineer": "AI Engineer",
        "artificial intelligence": "AI Engineer",
        "ml engineer": "Machine Learning Engineer",
        "machine learning": "Machine Learning Engineer",
        "embedded engineer": "Embedded Systems Engineer",
        "embedded systems": "Embedded Systems Engineer",
        "cv engineer": "Computer Vision Engineer",
        "computer vision": "Computer Vision Engineer",
        "ros developer": "ROS2 Developer",
        "ros2 developer": "ROS2 Developer",
    }

    cleaned = set()
    special_chars = ['|', '·', '—', '→', '•', '◦']

    for role in roles:
        if not role or not isinstance(role, str):
            continue

        # Remove special characters
        for char in special_chars:
            role = role.replace(char, ' ')

        # Split by common delimiters (|, /, &, etc.)
        parts = [part.strip() for part in role.split('/')]

        for part in parts:
            # Further split if there are '|' or '&' characters
            subparts = [sp.strip() for sp in part.replace('|', ' ').replace('&', ' ').split()]
            for subpart in subparts:
                if not subpart:
                    continue

                # Try exact match with known roles
                if subpart in KNOWN_ROLES:
                    cleaned.add(subpart)
                    continue

                # Try case-insensitive match with mappings
                lower_part = subpart.lower()
                if lower_part in ROLE_MAPPINGS:
                    cleaned.add(ROLE_MAPPINGS[lower_part])
                    continue

                # Try to find a matching known role by substring
                for known_role in KNOWN_ROLES:
                    if lower_part in known_role.lower() or known_role.lower() in lower_part:
                        cleaned.add(known_role)
                        break

    return sorted(list(cleaned))


def extract_cv_data(cv_text: str) -> dict:
    """Extract structured data from CV text using Groq LLM."""
    from groq import Groq
    import os
    import json

    try:
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            raise Exception("GROQ_API_KEY not set")

        client = Groq(api_key=groq_api_key)

        prompt = f"""Analyze this CV and extract the following information as JSON:

CV TEXT:
{cv_text}

Extract and return ONLY a JSON object (no markdown, no code blocks) with these fields:
{{
  "skills": ["list", "of", "technical", "skills", "extracted"],
  "roles": ["list", "of", "job", "titles", "or", "roles"],
  "experience_years": <integer: total years of professional experience>,
  "education": ["degree", "field", "university"],
  "projects": ["project1", "project2"],
  "languages": ["English", "Spanish"],
  "summary": "1-2 sentence summary of professional background"
}}

If a field is not found, use an empty list or 0 for numbers.
Return ONLY valid JSON, no other text."""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        # Parse the response
        response_text = response.choices[0].message.content.strip()

        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        extracted = json.loads(response_text)

        return {
            "skills": extracted.get("skills", []),
            "roles": clean_roles(extracted.get("roles", [])),
            "experience_years": extracted.get("experience_years", 0),
            "education": extracted.get("education", []),
            "projects": extracted.get("projects", []),
            "languages": extracted.get("languages", []),
            "summary": extracted.get("summary", "")
        }

    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse LLM response as JSON: {str(e)}")
    except Exception as e:
        raise Exception(f"LLM extraction failed: {str(e)}")
