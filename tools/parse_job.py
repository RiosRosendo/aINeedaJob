"""Extract structured fields from raw job description using LLM. Returns validated JSON dict."""

import re
import json
from html.parser import HTMLParser
from tools.llm import call_llm
from tools.logger import log_agent_run


class HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []
    def handle_data(self, d):
        self.text.append(d)
    def get_data(self):
        return ''.join(self.text)


def parse_job(job_id, user_id, description_raw, original_title=None):
    """Extract structured fields. Returns dict with title, company, location, etc.

    If LLM returns empty title, uses original_title as fallback.
    """
    if not description_raw or not description_raw.strip():
        raise Exception("description_raw is empty")

    # Clean and truncate
    cleaned_text = _clean_html(description_raw)
    cleaned_text = cleaned_text[:4000]

    # Extract via LLM (retry once)
    try:
        parsed = _extract_with_llm(cleaned_text, retry=True)
        _validate_fields(parsed, original_title)

        log_agent_run(
            user_id=user_id,
            job_id=job_id,
            agent='job_parsing',
            status='success',
            details={'title': parsed.get('title')}
        )

        return parsed

    except Exception as e:
        log_agent_run(
            user_id=user_id,
            job_id=job_id,
            agent='job_parsing',
            status='failed',
            details={'error': str(e)}
        )
        raise Exception(f"Job parsing failed: {str(e)}")


def _clean_html(text):
    """Remove HTML tags and excessive whitespace."""
    try:
        stripper = HTMLStripper()
        stripper.feed(text)
        cleaned = stripper.get_data()
    except:
        cleaned = text

    # Remove excessive whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = cleaned.strip()
    return cleaned


def _extract_with_llm(cleaned_text, retry=True):
    # Verify cleaned_text is not empty
    if not cleaned_text or not cleaned_text.strip():
        raise Exception("Cleaned job description is empty")

    prompt = f"""Extract the following fields from this job description.
Return only a JSON object with no extra text.

Fields:
- title (string)
- company (string)
- location (string: Format as "City, Country" if both available (e.g. "San Francisco, US"), or just location if unclear. Use "Remote" if remote-only job)
- modality (string: "remote", "hybrid", or "on-site")
- salary_min (integer, annual USD, null if not mentioned)
- salary_max (integer, annual USD, null if not mentioned)
- required_skills (list of strings) - EXTRACT ALL technical skills including:
  * Programming languages (Python, Java, C++, JavaScript, Go, Rust, etc.)
  * Frameworks and libraries (TensorFlow, PyTorch, Django, FastAPI, React, ROS, etc.)
  * Cloud platforms (AWS, GCP, Azure, Kubernetes, etc.)
  * Tools and technologies (Docker, Git, Linux, SQL, PostgreSQL, MongoDB, etc.)
  * AI/ML concepts (LLMs, RAG, computer vision, NLP, transformers, YOLO, etc.)
  * Data science tools (Pandas, NumPy, Scikit-learn, Jupyter, etc.)
  * Even if mentioned in paragraph form, extract as individual items.
  * If truly no technical skills mentioned, return []
- nice_to_have_skills (list of strings)
- experience_level (string: "junior", "mid", "senior", or "unknown")
- experience_years_min (integer, null if not mentioned)
- responsibilities (list of strings, max 5)

IMPORTANT: Be thorough with required_skills. Extract every technical skill, tool, language, and technology mentioned anywhere in the description.

Job description:
{cleaned_text}"""
    try:
        response = call_llm(prompt)
        print(f"[PARSE] Raw LLM response: {response[:200]}")

        # Check if response is empty
        if not response or not response.strip():
            raise Exception("LLM returned empty response")

        # Strip markdown code blocks
        response = response.replace("```json", "").replace("```", "").strip()
        print(f"[PARSE] Cleaned response: {response[:200]}")

        parsed = json.loads(response)
        skills = parsed.get('required_skills', [])
        print(f"[PARSE] Extracted {len(skills)} required_skills: {skills}")
        return parsed
    except json.JSONDecodeError:
        if not retry:
            raise Exception("LLM returned invalid JSON twice")
        response = call_llm(prompt + "\n\nIMPORTANT: Return ONLY valid JSON. No markdown, no code blocks. Just raw JSON.")
        print(f"[PARSE] Retry raw response: {response[:200]}")

        # Clean response again on retry
        response = response.replace("```json", "").replace("```", "").strip()
        print(f"[PARSE] Retry cleaned response: {response[:200]}")

        parsed = json.loads(response)
        skills = parsed.get('required_skills', [])
        print(f"[PARSE] Extracted {len(skills)} required_skills: {skills}")
        return parsed


def _is_valid_title(title):
    """Check if extracted title looks like a real job title (not garbage or description)."""
    if not title or not str(title).strip():
        return False

    title_str = str(title).strip()

    # Check 1: Starts with numbers (e.g., "2024 Job Description")
    if title_str and title_str[0].isdigit():
        print(f"[PARSE VALIDATION] Title starts with number: '{title_str}'")
        return False

    # Check 2: Contains salary keywords
    if any(keyword in title_str.lower() for keyword in ['salary', 'salaire', 'compensation', '$', '€', '£']):
        print(f"[PARSE VALIDATION] Title contains salary keyword: '{title_str}'")
        return False

    # Check 3: Longer than 70 characters (likely a description, not a title)
    if len(title_str) > 70:
        print(f"[PARSE VALIDATION] Title too long ({len(title_str)} chars, max 70): '{title_str}'")
        return False

    # Check 4: Contains organizational structure words (suggests description, not title)
    org_words = ['team', 'organization', 'department', 'division', 'group']
    if any(word in title_str.lower() for word in org_words):
        print(f"[PARSE VALIDATION] Title contains organizational word (likely description): '{title_str}'")
        return False

    # Check 5: Contains marketing/generic phrases
    garbage_phrases = ['join us', 'we are', 'looking for', 'rethink', 'about us', 'welcome to', 'come work with us']
    if any(phrase in title_str.lower() for phrase in garbage_phrases):
        print(f"[PARSE VALIDATION] Title contains generic phrase: '{title_str}'")
        return False

    return True


def _validate_fields(parsed, original_title=None):
    # Validate and potentially fix parsed title
    parsed_title = parsed.get('title')

    if not _is_valid_title(parsed_title):
        # Parsed title is invalid, try original title
        if original_title and _is_valid_title(original_title):
            print(f"[PARSE FALLBACK] Invalid parsed title, using original: '{original_title}'")
            parsed['title'] = original_title
        else:
            raise Exception(f"title is invalid (parsed: '{parsed_title}', original: '{original_title}')")
    else:
        print(f"[PARSE VALIDATION] Title is valid: '{parsed_title}'")

    for key in ('required_skills', 'nice_to_have_skills', 'responsibilities'):
        if key not in parsed:
            parsed[key] = []

    # Ensure location is present
    if 'location' not in parsed:
        parsed['location'] = None

    # Validate modality and experience level
    if parsed.get('modality') not in {'remote', 'hybrid', 'on-site', 'unknown'}:
        parsed['modality'] = 'unknown'
    if parsed.get('experience_level') not in {'junior', 'mid', 'senior', 'unknown'}:
        parsed['experience_level'] = 'unknown'
    return parsed
