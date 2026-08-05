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
        print(f"[CV UPLOAD DEBUG] Raw PDF text (first 500 chars): {pdf_text[:500]}", flush=True)

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
    """Extract text from PDF bytes using PyMuPDF (fitz) with proper spacing."""
    try:
        import fitz

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except ImportError:
        raise HTTPException(status_code=500, detail="PyMuPDF not installed")
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
        print(f"[CV PARSE DEBUG] response_text is empty or None", flush=True)
        return None

    # Strategy 1: Direct parsing
    try:
        result = json.loads(response_text)
        print(f"[CV PARSE DEBUG] Strategy 1 (direct parsing) SUCCESS", flush=True)
        return result
    except json.JSONDecodeError as e:
        print(f"[CV PARSE DEBUG] Strategy 1 (direct parsing) FAILED: {str(e)}", flush=True)
        pass

    # Strategy 2: Extract from markdown code blocks (```json...```)
    try:
        if "```" in response_text:
            print(f"[CV PARSE DEBUG] Strategy 2: Found markdown code blocks", flush=True)
            parts = response_text.split("```")
            for i, part in enumerate(parts):
                if part.startswith("json"):
                    json_str = part[4:].strip()
                    result = json.loads(json_str)
                    print(f"[CV PARSE DEBUG] Strategy 2 (markdown json) SUCCESS at block {i}", flush=True)
                    return result
                elif part.strip() and part.strip()[0] == '{':
                    result = json.loads(part.strip())
                    print(f"[CV PARSE DEBUG] Strategy 2 (markdown object) SUCCESS at block {i}", flush=True)
                    return result
        else:
            print(f"[CV PARSE DEBUG] Strategy 2: No markdown code blocks found", flush=True)
    except json.JSONDecodeError as e:
        print(f"[CV PARSE DEBUG] Strategy 2 (markdown parsing) FAILED: {str(e)}", flush=True)
        pass

    # Strategy 3: Find first { and last } and parse that substring
    try:
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}')
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            json_str = response_text[start_idx:end_idx + 1]
            print(f"[CV PARSE DEBUG] Strategy 3: Extracted JSON substring (len={len(json_str)})", flush=True)
            result = json.loads(json_str)
            print(f"[CV PARSE DEBUG] Strategy 3 (substring extraction) SUCCESS", flush=True)
            return result
        else:
            print(f"[CV PARSE DEBUG] Strategy 3: Could not find {{ and }} in response", flush=True)
    except json.JSONDecodeError as e:
        print(f"[CV PARSE DEBUG] Strategy 3 (substring parsing) FAILED: {str(e)}", flush=True)
        pass

    # Strategy 4: Use json-repair to fix malformed JSON
    try:
        import json_repair
        print(f"[CV PARSE DEBUG] Strategy 4: Attempting json-repair", flush=True)
        repaired = json_repair.repair_json(response_text)
        result = json.loads(repaired)
        print(f"[CV PARSE DEBUG] Strategy 4 (json-repair) SUCCESS", flush=True)
        return result
    except Exception as e:
        print(f"[CV PARSE DEBUG] Strategy 4 (json-repair) FAILED: {str(e)}", flush=True)
        pass

    print(f"[CV PARSE DEBUG] All parsing strategies FAILED", flush=True)
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

        # Limit CV to 4000 chars - LLM finds sections autonomously
        cv_text = cv_text[:4000]

        prompt = f"""Extract ONLY these fields from this CV. Be concise. Return ONLY valid JSON, no markdown, no explanations.

CV:
{cv_text}

Extract ONLY these fields:
- name: person's full name from CV header/top
- tech_skills: list of technology names only
- languages: spoken languages with levels
- roles: job titles
- education: degrees only
- experience: job titles and companies only (no descriptions)
- projects: project names only (no descriptions)
- nationality: if mentioned

EXHAUSTIVE TECHNOLOGY EXTRACTION:
Extract EVERY technology, tool, library, framework, platform, and programming language mentioned ANYWHERE in this CV:
- In Skills/Technologies sections
- In project descriptions and implementation details
- In experience/job responsibility bullets
- In coursework and education sections
- Hardware platforms, microcontrollers, boards
- Communication protocols and interfaces (CAN, UART, I2C, etc.)
- Simulation environments and IDEs
- Build systems and tools

CRITICAL RULES:
- Preserve the EXACT spelling and capitalization of technology names as they appear in the CV
- Do not add spaces within compound words or modify capitalization
- If CV says 'ArUco', extract 'ArUco' - not 'Ar Uco'
- If CV says 'FreeRTOS', extract 'FreeRTOS' - not 'Free RTOS'
- If CV says 'LiDAR', extract 'LiDAR' - not 'Li DAR'
- If CV says 'MediaPipe', extract 'MediaPipe' - not 'Media Pipe'
- Copy technology names character-for-character from the CV text
- Be exhaustive - extract ALL technologies found, not just common ones
- Expect minimum 25+ skills from a technical CV
- NO languages (Spanish, English, etc.) - extract only to languages field
- NO certifications - extract only to certifications field
- NO algorithms with symbols (A*, D*, RRT*)
- NO generic concepts (optimization, filtering, planning - unless they're tool names)
- Each item in tech_skills must be a single, standalone technology name
- Do not combine multiple technologies into one item
- The LLM decides autonomously what constitutes a single technology

ROLE EXTRACTION (Multi-language support):
This CV may be in any language (English, Spanish, French, German, Portuguese, Chinese, Japanese, etc).
Extract ALL job titles, positions, and professional roles mentioned in:
- Job titles in experience section
- Position descriptions
- Academic or professional roles
- Project lead or team roles

LANGUAGE-AGNOSTIC TRANSLATION:
- If CV is in Spanish: 'Ingeniero Robótico' → Extract as 'Robotics Engineer'
- If CV is in French: 'Ingénieur Logiciel' → Extract as 'Software Engineer'
- If CV is in German: 'Eingebettete Systeme Ingenieur' → Extract as 'Embedded Systems Engineer'
- Return all roles in English regardless of CV language
- The LLM translates autonomously based on context - no hardcoded translations
- Be comprehensive - extract all distinct roles found

For languages: Format: [{{"language": "Spanish", "level": "Native"}}]
Levels: Native, Fluent, Advanced, Intermediate, Beginner, or B1/B2/C1/C2

NAME EXTRACTION:
Extract the person's full name from the CV:
- Look for name at the very top/header of CV (usually first line)
- If no header, look in contact info section or introduction
- Extract complete full name as written in CV (e.g., "ROSENDO ADRIAN DE LOS RIOS MORENO")
- Return as string
- If no name found, return null

NATIONALITY EXTRACTION:
Extract the person's nationality/citizenship from the CV if mentioned:
- Look for: "Mexican national", "Mexican citizen", "Nationality: Mexican", "I am Mexican", "From Mexico", location in address section
- Extract the actual country/nationality as written in the CV
- If CV is in Spanish/French/German, translate nationality to English (e.g., "Mexicano" → "Mexican", "Français" → "French")
- Return as string (not array)
- If no nationality found, return null

EXPERIENCE LEVEL DETECTION:
Analyze the CV holistically to determine experience level:
- Consider: graduation year, years since graduation, number of jobs held, seniority of roles, complexity of projects, academic level (BSc/MSc/PhD), internships vs full-time positions
- Return detected_experience_level as one of: Intern, Junior, Semi-Senior, Senior, Lead/Manager
- The LLM decides autonomously based on the full picture, not just years of experience
- Intern: No professional work experience, recent graduate, internships only
- Junior: 0-3 years professional experience, entry-level roles, mostly individual contributor
- Semi-Senior: 3-7 years experience, some technical leadership, mentoring junior developers, leading small projects
- Senior: 7+ years, technical depth, mentoring multiple people, leading significant projects, architecture decisions
- Lead/Manager: People management, team/project leadership, strategic decisions, C-level or director roles

EXPERIENCE EXTRACTION:
Extract detailed work experience from the CV:
- Each experience entry represents ONE job position
- Multiple bullet points from the same job should be combined into one entry with a comprehensive description
- Each job entry should have: title (job title), company, duration (e.g., "2021-2023" or "2+ years"), description (key responsibilities/achievements)
- Return as list of objects
- Return empty list if no experience found

PROJECTS EXTRACTION:
Extract personal or professional projects from the CV:
- Each project should have: name, description (what was built/done), technologies (list of tech used)
- Return as list of objects
- Return empty list if no projects found

EDUCATION EXTRACTION:
Extract educational background from the CV:
- Each entry should have: degree (e.g., "Bachelor of Science"), institution (university/school name), year (graduation year), gpa (if available, else null)
- Return as list of objects
- Return empty list if no education found

Return:
{{
  "name": "Rosendo Adrian De Los Rios Moreno",
  "tech_skills": ["Python", "C++", "ROS2", "Gazebo", "Docker"],
  "languages": [{{"language": "Spanish", "level": "Native"}}],
  "roles": ["Robotics Engineer"],
  "nationality": "Mexican",
  "detected_experience_level": "Senior",
  "experience_years": 5,
  "experience": [{{"title": "Robotics Engineer", "company": "Acme Corp", "duration": "2021-2023", "description": "Led autonomous robot development"}}],
  "projects": [{{"name": "Autonomous Nav", "description": "Built ROS2 navigation stack", "technologies": ["ROS2", "Python", "Docker"]}}],
  "education": [{{"degree": "Bachelor of Science", "institution": "University of Tech", "year": 2021, "gpa": 3.8}}],
  "certifications": []
}}
"""

        print(f"[CV EXTRACT DEBUG] LLM prompt (first 300 chars): {prompt[:300]}", flush=True)

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        response_text = response.choices[0].message.content.strip()
        print(f"[CV EXTRACT DEBUG] Raw LLM response: {response_text}", flush=True)
        extracted = _parse_json_with_fallbacks(response_text)

        if not extracted:
            print(f"[CV PARSE FAILED] Could not extract JSON. Raw response (first 500 chars): {response_text[:500]}")
            return {
                "name": None,
                "skills": [],
                "roles": [],
                "experience_years": 0,
                "experience": [],
                "education": [],
                "projects": [],
                "languages": [],
                "certifications": [],
                "nationality": None,
                "summary": ""
            }

        tech_skills = _clean_tech_skills(extracted.get("tech_skills", []))
        languages = extracted.get("languages", [])
        experience = _deduplicate_experience(extracted.get("experience", []))

        print(f"[CV EXTRACT] Raw languages from LLM: {languages}", flush=True)
        print(f"[CV EXTRACT] Raw tech_skills from LLM: {extracted.get('tech_skills', [])}", flush=True)
        print(f"[CV EXTRACT] Cleaned tech_skills: {tech_skills}", flush=True)

        return {
            "name": extracted.get("name", None),
            "skills": tech_skills,
            "roles": clean_roles(extracted.get("roles", [])),
            "experience_years": extracted.get("experience_years", 0),
            "experience": experience,
            "education": extracted.get("education", []),
            "projects": extracted.get("projects", []),
            "languages": languages,
            "certifications": extracted.get("certifications", []),
            "nationality": extracted.get("nationality", None),
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

        # Preserve exact spelling - do not modify capitalization or spacing
        # (LLM now extracts exact names from CV text)
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


def _deduplicate_experience(experience: list) -> list:
    """Deduplicate experience entries by (title, company). Keep unique combinations."""
    if not experience:
        return []

    seen = {}  # (title, company) → experience entry

    for entry in experience:
        if not isinstance(entry, dict):
            continue

        title = (entry.get('title') or '').strip().lower()
        company = (entry.get('company') or '').strip().lower()

        if not title or not company:
            continue

        key = (title, company)

        if key not in seen:
            seen[key] = entry
        else:
            # Merge descriptions if same job appears multiple times
            existing_desc = (seen[key].get('description') or '').strip()
            new_desc = (entry.get('description') or '').strip()
            if new_desc and new_desc != existing_desc:
                seen[key]['description'] = f"{existing_desc}\n{new_desc}".strip()

    return list(seen.values())
