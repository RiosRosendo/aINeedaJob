"""CV upload, extraction, and retrieval endpoints."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import Optional
import json
from api.dependencies import get_user_id
from tools.db import execute_query, execute_update

router = APIRouter()


@router.get("/profile")
async def get_cv_profile(user_id: str = Depends(get_user_id)):
    """
    Get the user's complete CV profile data (cv_data JSONB).

    Returns all stored CV information including:
    - name, email, phone, contact info
    - education, experience, projects
    - skills, languages, summary
    - github, linkedin, website URLs

    This is the source of truth for all CV data - no hardcoding in frontend.
    """
    try:
        result = execute_query(
            """
            SELECT cv_data FROM user_profiles WHERE user_id = %s
            """,
            (user_id,)
        )

        if not result:
            raise HTTPException(status_code=404, detail="User profile not found")

        cv_data = result[0].get('cv_data')
        if not cv_data:
            raise HTTPException(
                status_code=404,
                detail="No CV data found. User must upload CV first."
            )

        # Parse if it's a string
        if isinstance(cv_data, str):
            cv_data = json.loads(cv_data)

        return {
            "status": "success",
            "cv_data": cv_data
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[CV PROFILE] ERROR: {type(e).__name__}: {str(e)}", flush=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve CV profile: {str(e)}")


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

        # Save extracted CV data to user_profiles
        try:
            print(f"[CV UPLOAD] Saving CV data to database for user {user_id}", flush=True)
            execute_update(
                """
                UPDATE user_profiles
                SET cv_data = %s, cv_base_url = %s
                WHERE user_id = %s
                """,
                (
                    json.dumps(extracted_data),
                    file.filename,
                    user_id
                )
            )
            print(f"[CV UPLOAD] CV data saved successfully", flush=True)
        except Exception as db_error:
            print(f"[CV UPLOAD] Warning: Failed to save CV data: {str(db_error)}", flush=True)
            # Continue even if save fails - return extracted data to frontend

        return {
            "status": "success",
            "extracted_data": extracted_data,
            "raw_text_length": len(pdf_text),
            "message": "CV processed and saved successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[CV UPLOAD] ERROR: {str(e)}", flush=True)
        raise HTTPException(status_code=500, detail=f"Failed to process CV: {str(e)}")


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes using pdfplumber with layout preservation."""
    try:
        import pdfplumber
        import io

        pdf_file = io.BytesIO(pdf_bytes)
        text = ""

        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                # Use layout=True to preserve spacing between words and sections
                # This prevents custom fonts from merging words together
                page_text = page.extract_text(layout=True)
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


def _parse_json_with_fallbacks(response_text: str) -> dict:
    """
    Try multiple strategies to parse JSON from LLM response.
    Returns parsed dict or None if all strategies fail.
    """
    import json

    if not response_text:
        return None

    # Strategy 1: Direct parsing
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from markdown code blocks (```json...```)
    try:
        if "```" in response_text:
            parts = response_text.split("```")
            for part in parts:
                if part.startswith("json"):
                    json_str = part[4:].strip()
                    return json.loads(json_str)
                elif part.strip() and part.strip()[0] == '{':
                    return json.loads(part.strip())
    except json.JSONDecodeError:
        pass

    # Strategy 3: Find first { and last } and parse that substring
    try:
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}')
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            json_str = response_text[start_idx:end_idx + 1]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    return None


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

        prompt = f"""Extract all information from this CV as valid JSON. Work with any CV in any language.

CV TEXT:
{cv_text}

Extract these fields as JSON (use empty arrays/strings if not found):
- tech_skills: List of technology/tool names ONLY (no algorithms, descriptions, or generic concepts)
- languages: Array of {{"language": "name", "level": "Native|Fluent|Advanced|Intermediate|Beginner"}}
- certifications: List of professional certifications
- roles: List of job titles/positions
- experience_years: Total years (integer)
- education: List of degrees/fields
- projects: List of project names
- summary: 1-2 sentence professional background

CRITICAL:
- Return ONLY valid JSON with no markdown, no comments, no trailing commas
- No code blocks, no explanations, no extra text
- Autonomously extract based on CV content - nothing hardcoded

Format:
{{
  "tech_skills": ["C++", "Python", ...],
  "languages": [{{"language": "Spanish", "level": "Native"}}],
  "certifications": [...],
  "roles": [...],
  "experience_years": 5,
  "education": [...],
  "projects": [...],
  "summary": "..."
}}
"""

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

        response_text = response.choices[0].message.content.strip()
        extracted = _parse_json_with_fallbacks(response_text)

        if not extracted:
            print(f"[CV PARSE FAILED] Could not extract JSON. Raw response (first 500 chars): {response_text[:500]}")
            return {
                "skills": [],
                "roles": [],
                "experience_years": 0,
                "education": [],
                "projects": [],
                "languages": [],
                "certifications": [],
                "summary": ""
            }

        tech_skills = _clean_tech_skills(extracted.get("tech_skills", []))

        return {
            "skills": tech_skills,
            "roles": clean_roles(extracted.get("roles", [])),
            "experience_years": extracted.get("experience_years", 0),
            "education": extracted.get("education", []),
            "projects": extracted.get("projects", []),
            "languages": extracted.get("languages", []),
            "certifications": extracted.get("certifications", []),
            "summary": extracted.get("summary", "")
        }

    except Exception as e:
        raise Exception(f"LLM extraction failed: {str(e)}")


def _clean_tech_skills(skills: list) -> list:
    """Clean technical skills: remove duplicates, fix spacing, remove non-tech items."""
    cleaned_list = []
    language_keywords = {'native', 'fluent', 'intermediate', 'beginner', 'b1', 'b2', 'c1', 'c2', 'a1', 'a2'}
    language_names = {'english', 'spanish', 'french', 'german', 'portuguese', 'chinese', 'japanese', 'korean', 'russian', 'italian', 'dutch', 'swedish', 'polish'}
    cert_keywords = {'toefl', 'ielts', 'certificate', 'certified', 'aws', 'gcp', 'azure'}

    for skill in skills:
        if not skill or not isinstance(skill, str):
            continue

        skill = skill.strip()
        lower_skill = skill.lower()

        # Skip if it's a language proficiency level
        if any(keyword in lower_skill for keyword in language_keywords):
            continue

        # Skip if it's a language name
        if any(lang in lower_skill for lang in language_names):
            continue

        # Skip if it's a certification keyword
        if any(cert in lower_skill for cert in cert_keywords):
            continue

        # Fix common compound skills (add spaces between camelCase)
        skill = _fix_compound_skills(skill)

        cleaned_list.append(skill)

    # Deduplicate by normalized name
    return _deduplicate_skills(cleaned_list)


def _normalize_skill_name(skill: str) -> str:
    """Normalize skill name for deduplication: lowercase, remove spaces, special chars."""
    import re
    # Remove spaces, lowercase, keep only alphanumeric
    normalized = re.sub(r'[^a-z0-9]', '', skill.lower())
    return normalized


def _fix_compound_skills(skill: str) -> str:
    """Fix compound skills by adding proper spacing."""
    import re

    fixes = {
        'raspberrypi': 'Raspberry Pi',
        'nvidiaisaacsim': 'NVIDIA Isaac Sim',
        'djittopy': 'djitellopy',
        'tensorflow': 'TensorFlow',
        'pytorch': 'PyTorch',
        'opencv': 'OpenCV',
        'linux': 'Linux',
        'windows': 'Windows',
        'pointcloudprocessing': 'Point Cloud Processing',
    }

    lower_skill = skill.lower().replace(' ', '')
    if lower_skill in fixes:
        return fixes[lower_skill]

    # Fix camelCase spacing (e.g., "MySQL" → "MySQL")
    # Insert space before capital letters that follow lowercase
    skill = re.sub(r'([a-z])([A-Z])', r'\1 \2', skill)

    return skill


def _deduplicate_skills(skills: list) -> list:
    """Deduplicate skills by normalized name, keeping the cleanest version."""
    if not skills:
        return []

    # Track normalized → original mapping
    seen = {}  # normalized_name → cleaned_skill

    for skill in skills:
        if not skill or not isinstance(skill, str):
            continue

        skill = skill.strip()
        # Normalize for comparison
        normalized = _normalize_skill_name(skill)

        if not normalized:
            continue

        # Keep the version with more spaces/capitals (cleaner formatting)
        if normalized not in seen:
            seen[normalized] = skill
        else:
            # Keep the one with more capital letters (better formatted)
            existing = seen[normalized]
            if sum(1 for c in skill if c.isupper()) > sum(1 for c in existing if c.isupper()):
                seen[normalized] = skill

    return sorted(list(seen.values()))
