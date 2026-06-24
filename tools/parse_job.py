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


def parse_job(job_id, user_id, description_raw):
    """Extract structured fields. Returns dict with title, company, location, etc."""
    if not description_raw or not description_raw.strip():
        raise Exception("description_raw is empty")

    # Clean and truncate
    cleaned_text = _clean_html(description_raw)
    cleaned_text = cleaned_text[:4000]

    # Extract via LLM (retry once)
    try:
        parsed = _extract_with_llm(cleaned_text, retry=True)
        _validate_fields(parsed)

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
- location (string)
- modality (string: "remote", "hybrid", or "on-site")
- salary_min (integer, annual USD, null if not mentioned)
- salary_max (integer, annual USD, null if not mentioned)
- required_skills (list of strings)
- nice_to_have_skills (list of strings)
- experience_level (string: "junior", "mid", "senior", or "unknown")
- experience_years_min (integer, null if not mentioned)
- responsibilities (list of strings, max 5)

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

        return json.loads(response)
    except json.JSONDecodeError:
        if not retry:
            raise Exception("LLM returned invalid JSON twice")
        response = call_llm(prompt + "\n\nIMPORTANT: Return ONLY valid JSON. No markdown, no code blocks. Just raw JSON.")
        print(f"[PARSE] Retry raw response: {response[:200]}")

        # Clean response again on retry
        response = response.replace("```json", "").replace("```", "").strip()
        print(f"[PARSE] Retry cleaned response: {response[:200]}")

        return json.loads(response)


def _validate_fields(parsed):
    if not parsed.get('title') or not str(parsed.get('title')).strip():
        raise Exception("title is required")
    for key in ('required_skills', 'nice_to_have_skills', 'responsibilities'):
        if key not in parsed:
            parsed[key] = []
    if parsed.get('modality') not in {'remote', 'hybrid', 'on-site', 'unknown'}:
        parsed['modality'] = 'unknown'
    if parsed.get('experience_level') not in {'junior', 'mid', 'senior', 'unknown'}:
        parsed['experience_level'] = 'unknown'
    return parsed
