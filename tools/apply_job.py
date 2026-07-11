"""
Autonomous job application agent using browser automation.

Uses Playwright to navigate job pages and Groq LLM to decide application method.
Handles email applications, form submissions, and manual application detection.
"""

import os
import asyncio
import concurrent.futures
import json
import re
from typing import Optional, Dict
from datetime import datetime
from groq import Groq
from playwright.async_api import async_playwright
from tools.db import execute_query, execute_update
from tools.generate_cover_letter import should_generate_cover_letter, generate_cover_letter, save_cover_letter, get_cover_letter


async def apply_for_job(user_id: str, job_id: str, application_id: str, job_url: str, cv_url: str) -> Dict:
    """
    Autonomously apply for a job using browser automation.

    Uses LLM to analyze the job page and decide on application method:
    - email: Send email to recruiter
    - form: Fill and submit application form
    - manual: Requires user intervention

    Returns:
        {
            "application_id": str,
            "status": "applied" | "requires_manual",
            "method": "email" | "form" | "manual",
            "action": str (description of what was done),
            "error": str (if failed)
        }
    """
    result = {
        "application_id": application_id,
        "status": None,
        "method": None,
        "action": None,
        "what_i_tried": None,
        "why_i_need_help": None,
        "error": None
    }

    browser = None
    try:
        print(f"[APPLY_JOB] Starting application for job {job_id}, user {user_id}", flush=True)

        # Get user CV data and job details
        cv_result = execute_query(
            "SELECT cv_data FROM user_profiles WHERE user_id = %s",
            (user_id,)
        )

        if not cv_result or not cv_result[0].get('cv_data'):
            result["error"] = "No CV found for user"
            result["status"] = "requires_manual"
            result["method"] = "manual"
            print(f"[APPLY_JOB] {result['error']}", flush=True)
            return result

        cv_data = cv_result[0].get('cv_data')

        # Get job details for cover letter generation
        job_result = execute_query(
            "SELECT title, company, description_raw FROM jobs WHERE id = %s AND user_id = %s",
            (job_id, user_id)
        )

        job_title = job_result[0].get('title') if job_result else "Unknown Position"
        company = job_result[0].get('company') if job_result else "Unknown Company"
        job_description = job_result[0].get('description_raw') if job_result else ""

        # Get user's languages from CV data for multilingual support
        user_languages = cv_data.get('languages', []) if cv_data else []
        languages_str = ", ".join(user_languages) if user_languages else "English"
        print(f"[APPLY_JOB] User languages: {languages_str}", flush=True)

        # Check if cover letter is needed and generate if so
        if job_description and should_generate_cover_letter(job_description):
            print(f"[APPLY_JOB] Cover letter mentioned in job description, generating", flush=True)
            cover_letter = generate_cover_letter(user_id, job_id, job_title, company, job_description)
            if cover_letter:
                save_cover_letter(user_id, job_id, cover_letter)
                print(f"[APPLY_JOB] Cover letter generated and saved", flush=True)
        else:
            cover_letter = None
            print(f"[APPLY_JOB] No cover letter needed for this job", flush=True)

        # Launch browser
        async with async_playwright() as p:
            print(f"[APPLY_JOB] Launching Chromium browser", flush=True)
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # Navigate to job page
            print(f"[APPLY_JOB] Navigating to {job_url}", flush=True)
            try:
                await page.goto(job_url, wait_until='domcontentloaded', timeout=10000)
            except Exception as e:
                result["error"] = f"Failed to load job page: {str(e)}"
                result["status"] = "requires_manual"
                result["method"] = "manual"
                print(f"[APPLY_JOB] {result['error']}", flush=True)
                return result

            # Try to follow redirect to actual apply page (if this is a listing page)
            print(f"[APPLY_JOB] Checking for apply button redirect", flush=True)
            redirect_success = await _follow_redirect_to_apply_page(page)
            if redirect_success:
                print(f"[APPLY_JOB] Successfully followed redirect to: {page.url}", flush=True)
            else:
                print(f"[APPLY_JOB] No redirect button found, analyzing current page", flush=True)

            # Extract page content
            print(f"[APPLY_JOB] Extracting page content", flush=True)
            page_content = await _extract_page_content(page)

            # Analyze page and execute autonomously (up to 3 redirects)
            max_redirects = 3
            redirect_count = 0

            while redirect_count < max_redirects:
                print(f"[APPLY_JOB] Analyzing page (attempt {redirect_count + 1}/{max_redirects})", flush=True)
                analysis = await _analyze_application_method(job_url, page_content, cv_data, languages_str)

                if not analysis:
                    result["error"] = "Failed to analyze application method"
                    result["status"] = "requires_manual"
                    result["method"] = "manual"
                    break

                method = analysis.get('method')
                instructions = analysis.get('instructions', '')
                button_text = analysis.get('button_to_click', '')
                email = analysis.get('email', '')

                print(f"[APPLY_JOB] Method: {method} | Button: {button_text or 'N/A'}", flush=True)

                # Handle each method type
                if method == 'click_button':
                    if not button_text:
                        result["error"] = "LLM said click_button but no button_to_click provided"
                        result["status"] = "requires_manual"
                        result["method"] = "manual"
                        print(f"[APPLY_JOB] ERROR: {result['error']}", flush=True)
                        break

                    print(f"[APPLY_JOB] Clicking button: '{button_text}'", flush=True)
                    click_success = await _click_continuation_button(page, button_text)

                    if click_success:
                        redirect_count += 1
                        print(f"[APPLY_JOB] Button clicked, re-analyzing (redirect {redirect_count}/{max_redirects})", flush=True)
                        page_content = await _extract_page_content(page)
                        continue  # Loop back to analyze new page
                    else:
                        result["error"] = f"Failed to click button: '{button_text}'"
                        result["status"] = "requires_manual"
                        result["method"] = "manual"
                        messages = await _generate_user_friendly_message(
                            f"couldn't click the '{button_text}' button",
                            "click_button",
                            f"The button '{button_text}' was not accessible"
                        )
                        result["action"] = messages.get("why_i_need_help")
                        result["what_i_tried"] = messages.get("what_i_tried")
                        result["why_i_need_help"] = messages.get("why_i_need_help")
                        print(f"[APPLY_JOB] {result['error']}", flush=True)
                        break

                elif method == 'form':
                    print(f"[APPLY_JOB] Attempting form submission", flush=True)
                    form_result = await _fill_and_submit_form(page, cv_data, instructions)

                    if form_result.get('success'):
                        result["method"] = "form"
                        result["status"] = "applied"
                        result["action"] = form_result.get('message', 'Form submitted successfully')
                        print(f"[APPLY_JOB] Form submitted: {result['action']}", flush=True)
                    else:
                        result["method"] = "form"
                        result["status"] = "requires_manual"
                        result["error"] = form_result.get('error', 'Form submission failed')
                        messages = await _generate_user_friendly_message(
                            "form submission failed",
                            "form",
                            form_result.get('error', '')
                        )
                        result["action"] = messages.get("why_i_need_help")
                        result["what_i_tried"] = messages.get("what_i_tried")
                        result["why_i_need_help"] = messages.get("why_i_need_help")
                        print(f"[APPLY_JOB] Form submission failed: {result['error']}", flush=True)
                    break  # Form is final state

                elif method == 'email':
                    result["method"] = "email"
                    result["status"] = "requires_manual"  # Will be sent by email agent
                    messages = await _generate_user_friendly_message(
                        "email application detected",
                        "email",
                        f"Email: {email or instructions}"
                    )
                    result["action"] = messages.get("why_i_need_help")
                    result["what_i_tried"] = messages.get("what_i_tried")
                    result["why_i_need_help"] = messages.get("why_i_need_help")
                    print(f"[APPLY_JOB] Email application detected: {result['action']}", flush=True)
                    break  # Email is final state

                elif method == 'manual':
                    result["method"] = "manual"
                    result["status"] = "requires_manual"
                    messages = await _generate_user_friendly_message(
                        "application page requires manual interaction",
                        "manual",
                        instructions
                    )
                    result["action"] = messages.get("why_i_need_help")
                    result["what_i_tried"] = messages.get("what_i_tried")
                    result["why_i_need_help"] = messages.get("why_i_need_help")
                    print(f"[APPLY_JOB] Manual application required: {result['action']}", flush=True)
                    break  # Manual is final state

                else:
                    result["error"] = f"Unknown method: {method}"
                    result["status"] = "requires_manual"
                    result["method"] = "manual"
                    print(f"[APPLY_JOB] ERROR: {result['error']}", flush=True)
                    break

            # Check if we exceeded max redirects
            if redirect_count >= max_redirects:
                result["error"] = f"Exceeded maximum redirects ({max_redirects})"
                result["status"] = "requires_manual"
                result["method"] = "manual"
                messages = await _generate_user_friendly_message(
                    "too many application page redirects",
                    "manual",
                    "The application flow has too many steps"
                )
                result["action"] = messages.get("why_i_need_help")
                result["what_i_tried"] = messages.get("what_i_tried")
                result["why_i_need_help"] = messages.get("why_i_need_help")
                print(f"[APPLY_JOB] {result['error']}", flush=True)

            await context.close()
            await browser.close()

        # Update application status
        _update_application_status(application_id, result['status'])

        # Log action
        _log_application_action(user_id, application_id, result['method'], result['action'])

        print(f"[APPLY_JOB] Application complete: status={result['status']}, method={result['method']}", flush=True)
        print(f"[APPLY_JOB] Final result: what_i_tried='{result.get('what_i_tried')}', why_i_need_help='{result.get('why_i_need_help')}'", flush=True)

        return result

    except Exception as e:
        print(f"[APPLY_JOB] FATAL ERROR: {type(e).__name__}: {str(e)}", flush=True)
        result["error"] = str(e)
        result["status"] = "requires_manual"
        result["method"] = "manual"
        _log_application_action(user_id, application_id, "error", str(e))
        return result

    finally:
        if browser:
            await browser.close()


async def _extract_page_content(page) -> str:
    """
    Extract meaningful content from the job page.

    Gets text content, form elements, and buttons.
    """
    try:
        # Get page text
        text_content = await page.evaluate("""
            () => {
                const text = document.body.innerText;
                return text.substring(0, 2000);  // Limit to 2000 chars for LLM
            }
        """)

        # Get form info
        forms = await page.evaluate("""
            () => {
                const forms = document.querySelectorAll('form');
                return Array.from(forms).map((form, idx) => ({
                    id: form.id || `form_${idx}`,
                    inputs: Array.from(form.querySelectorAll('input, textarea, select')).map(el => ({
                        type: el.type || el.tagName,
                        name: el.name,
                        placeholder: el.placeholder
                    }))
                }));
            }
        """)

        # Get buttons
        buttons = await page.evaluate("""
            () => {
                const buttons = document.querySelectorAll('button, a[role="button"]');
                return Array.from(buttons).map(btn => ({
                    text: btn.innerText.substring(0, 50),
                    type: btn.type || 'link'
                })).slice(0, 10);
            }
        """)

        content = f"""
PAGE TEXT:
{text_content}

FORMS DETECTED: {len(forms)}
{str(forms[:2])}

BUTTONS DETECTED:
{str(buttons)}
"""
        return content

    except Exception as e:
        print(f"[APPLY_JOB] Error extracting page content: {str(e)}", flush=True)
        return "Unable to extract page content"


async def _follow_redirect_to_apply_page(page) -> bool:
    """
    Follow redirect to actual apply page by clicking apply button.

    Looks for apply buttons in multiple languages and clicks them.
    Returns True if button was found and clicked, False otherwise.
    """
    # Apply button text in multiple languages
    apply_button_texts = [
        "Apply", "Apply Now", "Apply for this job",  # English
        "Postularme", "Solicitar", "Candidatarse",  # Spanish
        "Bewerben", "Jetzt bewerben",  # German
        "Postuler", "Postulez maintenant",  # French
        "Candidatarsi", "Candidati ora",  # Italian
        "応募する", "今すぐ応募",  # Japanese
        "申请", "立即申请",  # Chinese
    ]

    try:
        # Look for apply button
        for button_text in apply_button_texts:
            # Try exact match first
            button = await page.query_selector(f'button:has-text("{button_text}"), a:has-text("{button_text}")')

            if button:
                print(f"[APPLY_JOB REDIRECT] Found apply button: '{button_text}'", flush=True)
                try:
                    await button.click()
                    print(f"[APPLY_JOB REDIRECT] Clicked apply button", flush=True)

                    # Wait for redirect/navigation
                    await page.wait_for_timeout(3000)
                    print(f"[APPLY_JOB REDIRECT] Redirect complete, new URL: {page.url}", flush=True)
                    return True
                except Exception as e:
                    print(f"[APPLY_JOB REDIRECT] Failed to click button: {str(e)}", flush=True)
                    continue

        print(f"[APPLY_JOB REDIRECT] No apply button found", flush=True)
        return False

    except Exception as e:
        print(f"[APPLY_JOB REDIRECT] Error: {type(e).__name__}: {str(e)}", flush=True)
        return False


async def _click_continuation_button(page, button_text: str) -> bool:
    """
    Click a button by exact text match using Playwright's get_by_text().

    Returns True if button was found and clicked, False otherwise.
    """
    try:
        print(f"[APPLY_JOB CONTINUE] Looking for button: '{button_text}'", flush=True)

        # Try to find button/link by exact text using Playwright's locator
        try:
            # First try to find a button with exact text
            button = page.get_by_role("button", name=button_text)
            button_count = await button.count()

            if button_count == 0:
                # Try link role
                button = page.get_by_role("link", name=button_text)
                button_count = await button.count()

            if button_count == 0:
                # Try getting by text as fallback (case-insensitive partial match)
                button = page.get_by_text(button_text)
                button_count = await button.count()

            if button_count > 0:
                print(f"[APPLY_JOB CONTINUE] Found {button_count} element(s) matching '{button_text}'", flush=True)
                try:
                    # Click the first matching element
                    await button.first.click()
                    print(f"[APPLY_JOB CONTINUE] Clicked button, waiting for redirect", flush=True)

                    # Wait for navigation/redirect
                    await page.wait_for_timeout(3000)
                    print(f"[APPLY_JOB CONTINUE] Navigation complete, new URL: {page.url}", flush=True)
                    return True
                except Exception as e:
                    print(f"[APPLY_JOB CONTINUE] Failed to click button: {str(e)}", flush=True)
                    return False
            else:
                print(f"[APPLY_JOB CONTINUE] Button '{button_text}' not found on page", flush=True)
                return False

        except Exception as e:
            print(f"[APPLY_JOB CONTINUE] Error finding button: {str(e)}", flush=True)
            return False

    except Exception as e:
        print(f"[APPLY_JOB CONTINUE] Error: {type(e).__name__}: {str(e)}", flush=True)
        return False


def _extract_json(text: str) -> Dict:
    """
    Extract JSON from text that may contain markdown code blocks or extra text.

    Tries multiple strategies:
    1. Extract from ```json...``` code blocks
    2. Extract raw JSON object
    3. Raise error if no JSON found
    """
    if not text:
        raise ValueError("Empty text provided")

    # Try to find JSON in code blocks first
    match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError as e:
            print(f"[APPLY_JOB JSON] Failed to parse JSON from code block: {str(e)}", flush=True)

    # Try to find raw JSON object
    match = re.search(r'\{.*?\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as e:
            print(f"[APPLY_JOB JSON] Failed to parse JSON from raw object: {str(e)}", flush=True)

    raise ValueError(f"No valid JSON found in text: {text[:200]}")


async def _analyze_application_method(job_url: str, page_content: str, cv_data: dict, user_languages: str = "English") -> Optional[Dict]:
    """
    Use LLM to analyze the job page and decide how to proceed.

    Args:
        job_url: URL of the job page
        page_content: HTML/text content of the page
        cv_data: User's CV data
        user_languages: User's languages (e.g. "Spanish (Native), English (B2)")

    Returns:
        {
            "method": "click_button" | "form" | "email" | "manual",
            "button_to_click": str (exact button text, only if method is "click_button"),
            "instructions": str (method-specific details),
            "email": str (email address, only if method is "email")
        }
    """
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        prompt = f"""Analyze this job application page and decide HOW to proceed.

USER CONTEXT:
- Languages: {user_languages}
- The applicant may interact with forms in any of these languages
- Prefer to fill forms in the language of the job posting, or in English if the applicant speaks it

JOB URL: {job_url}

PAGE CONTENT:
{page_content}

ANALYZE THE PAGE:
1. Is there a clickable button/link to proceed to the next step? (e.g., "Apply", "Continue", "Next", "Seguir", "Candidatarse", "Bewerben", etc.)
2. Is there a visible application form with standard fields (name, email, CV)?
3. Is there a company email visible for applications? (apply@, careers@, hr@, etc.)
4. Does it require complex interactions, account creation, or external sites?

DECIDE ONE METHOD:
- "click_button" → If there's a button/link to click to proceed to the next step. Provide the EXACT button text.
- "form" → If there's a visible application form ready to fill. Provide field IDs or instructions.
- "email" → If there's an email address to contact. Provide the email address.
- "manual" → If the page is too complex or requires account creation/external sites.

RESPOND AS JSON (all fields required):
{{
  "method": "click_button" | "form" | "email" | "manual",
  "button_to_click": "EXACT button text (only if method is 'click_button')",
  "instructions": "details for the method",
  "email": "email address (only if method is 'email')"
}}

IMPORTANT:
- Only set button_to_click if method is "click_button"
- Use EXACT button text as it appears on the page
- For other methods, leave button_to_click empty string"""

        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300
        )

        response_text = response.choices[0].message.content.strip()

        # Parse JSON from response (handles code blocks and raw JSON)
        try:
            result = _extract_json(response_text)
            method = result.get('method', '').strip() if result.get('method') else ''

            # Normalize method value (lowercase, trim whitespace)
            method_lower = method.lower().strip()
            valid_methods = ['click_button', 'form', 'email', 'manual']

            print(f"[APPLY_JOB ANALYZE] Parsed method: '{method}' (normalized: '{method_lower}')", flush=True)
            print(f"[APPLY_JOB ANALYZE] Full result: {result}", flush=True)

            if method_lower in valid_methods:
                print(f"[APPLY_JOB ANALYZE] Method validated: {method_lower}", flush=True)
                # Update result with normalized method
                result['method'] = method_lower
                return result
            else:
                print(f"[APPLY_JOB ANALYZE] Invalid method in response: '{method}' (normalized: '{method_lower}')", flush=True)
                print(f"[APPLY_JOB ANALYZE] Valid methods are: {valid_methods}", flush=True)
                return None
        except ValueError as e:
            print(f"[APPLY_JOB ANALYZE] Failed to extract JSON: {str(e)}", flush=True)
            return None

    except Exception as e:
        print(f"[APPLY_JOB ANALYZE] ERROR: {type(e).__name__}: {str(e)}", flush=True)
        return None


async def _generate_user_friendly_message(reason: str, method: str, details: str = "") -> Dict:
    """
    Generate human-readable messages explaining what the agent tried and why it needs manual help.

    Returns:
        {
            "what_i_tried": "one sentence describing what the agent attempted",
            "why_i_need_help": "friendly explanation of what went wrong"
        }
    """
    try:
        print(f"[APPLY_JOB MESSAGE] Called with reason='{reason}', method='{method}', details='{details}'", flush=True)

        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        prompt = f"""You are a helpful job application assistant. Explain to the user what happened when trying to apply for this job.

WHAT THE AGENT TRIED:
- Method attempted: {method}
- Details: {details}

WHAT WENT WRONG:
- Reason: {reason}

Generate a JSON response with two fields:
1. "what_i_tried" - ONE sentence describing what you attempted to do (e.g., "I tried to fill out the application form")
2. "why_i_need_help" - ONE sentence explaining what went wrong in plain language (no technical jargon like "403", "HTTP", "error code")

Be friendly and conversational. Explain it like talking to a friend.

Respond with ONLY the JSON, no markdown, no extra text:
{{
  "what_i_tried": "...",
  "why_i_need_help": "..."
}}"""

        print(f"[APPLY_JOB MESSAGE] Calling Groq API", flush=True)
        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200
        )

        response_text = response.choices[0].message.content.strip()
        print(f"[APPLY_JOB MESSAGE] Raw response: '{response_text}'", flush=True)

        # Parse JSON response
        try:
            result = _extract_json(response_text)
            what_i_tried = result.get("what_i_tried", "I attempted to apply for this job").strip()
            why_i_need_help = result.get("why_i_need_help", "The application requires manual completion").strip()

            print(f"[APPLY_JOB MESSAGE] Parsed what_i_tried: '{what_i_tried}'", flush=True)
            print(f"[APPLY_JOB MESSAGE] Parsed why_i_need_help: '{why_i_need_help}'", flush=True)

            return {
                "what_i_tried": what_i_tried,
                "why_i_need_help": why_i_need_help
            }
        except ValueError as e:
            print(f"[APPLY_JOB MESSAGE] Failed to parse JSON: {str(e)}", flush=True)
            # Return defaults if JSON parsing fails
            return {
                "what_i_tried": "I attempted to apply for this job",
                "why_i_need_help": "Please complete the application manually"
            }

    except Exception as e:
        print(f"[APPLY_JOB MESSAGE] ERROR generating message: {type(e).__name__}: {str(e)}", flush=True)
        import traceback
        print(f"[APPLY_JOB MESSAGE] Traceback: {traceback.format_exc()}", flush=True)
        # Fallback messages
        return {
            "what_i_tried": "I attempted to apply for this job",
            "why_i_need_help": "Please complete the application manually"
        }


async def _fill_and_submit_form(page, cv_data: dict, instructions: str) -> Dict:
    """
    Attempt to fill and submit the application form.

    Returns:
        {
            "success": bool,
            "message": str,
            "error": str (if failed)
        }
    """
    try:
        print(f"[APPLY_JOB FORM] Attempting to fill form with instructions: {instructions}", flush=True)

        # Find and fill standard fields
        # Email field
        email_input = await page.query_selector('input[type="email"], input[name*="email" i]')
        if email_input and cv_data.get('email'):
            await email_input.fill(cv_data['email'])
            print(f"[APPLY_JOB FORM] Filled email: {cv_data['email']}", flush=True)

        # Name field
        name_input = await page.query_selector('input[name*="name" i]:not([name*="company" i])')
        if name_input and cv_data.get('name'):
            await name_input.fill(cv_data['name'])
            print(f"[APPLY_JOB FORM] Filled name: {cv_data['name']}", flush=True)

        # Look for submit button
        submit_btn = await page.query_selector('button[type="submit"], button:has-text("Submit"), button:has-text("Apply")')
        if submit_btn:
            print(f"[APPLY_JOB FORM] Found submit button, clicking", flush=True)
            await submit_btn.click()

            # Wait for page to update
            await page.wait_for_timeout(2000)

            # Check if form was submitted (look for success message or URL change)
            if "thank" in page.url.lower() or "success" in page.url.lower():
                return {
                    "success": True,
                    "message": "Form submitted successfully"
                }

            # Try to detect success message on page
            success_text = await page.evaluate("""
                () => {
                    const text = document.body.innerText.toLowerCase();
                    return text.includes('success') || text.includes('thank') || text.includes('submitted');
                }
            """)

            if success_text:
                return {
                    "success": True,
                    "message": "Form submitted successfully"
                }

        return {
            "success": False,
            "message": "Could not find or submit form",
            "error": "Form submission incomplete"
        }

    except Exception as e:
        print(f"[APPLY_JOB FORM] Error: {type(e).__name__}: {str(e)}", flush=True)
        return {
            "success": False,
            "message": f"Form filling failed: {str(e)}",
            "error": str(e)
        }


def _update_application_status(application_id: str, status: str):
    """
    Update application status in database.
    """
    try:
        execute_update(
            """
            UPDATE applications
            SET status = %s, updated_at = NOW()
            WHERE id = %s
            """,
            (status, application_id)
        )
        print(f"[APPLY_JOB] Updated application {application_id} to status {status}", flush=True)
    except Exception as e:
        print(f"[APPLY_JOB] Error updating application: {str(e)}", flush=True)


def _log_application_action(user_id: str, application_id: str, method: str, action: str):
    """
    Log application action to agent_logs table.
    """
    try:
        # Wrap details in JSON object as required by agent_logs schema
        details = json.dumps({
            "method": method,
            "action": action
        })
        execute_update(
            """
            INSERT INTO agent_logs (user_id, application_id, agent, status, details)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (user_id, application_id, "application", "applied", details)
        )
        print(f"[APPLY_JOB] Logged action for application {application_id}", flush=True)
    except Exception as e:
        print(f"[APPLY_JOB] Error logging action: {str(e)}", flush=True)


def apply_for_job_sync(user_id: str, job_id: str, application_id: str, job_url: str, cv_url: str) -> Dict:
    """
    Synchronous wrapper that runs Playwright in a thread pool.

    This avoids asyncio.run() conflicts with FastAPI's event loop.
    Runs Playwright in its own thread with its own event loop.
    """
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_run_playwright_in_thread, user_id, job_id, application_id, job_url, cv_url)
            return future.result(timeout=120)
    except concurrent.futures.TimeoutError:
        return {
            "application_id": application_id,
            "status": "requires_manual",
            "method": "manual",
            "action": "Application attempt timed out",
            "error": "Browser automation took too long (>2 minutes)"
        }
    except Exception as e:
        return {
            "application_id": application_id,
            "status": "requires_manual",
            "method": "manual",
            "action": None,
            "error": f"Thread pool error: {str(e)}"
        }


def _run_playwright_in_thread(user_id: str, job_id: str, application_id: str, job_url: str, cv_url: str) -> Dict:
    """
    Runs Playwright in its own thread with its own event loop.

    This allows Playwright to run independently from FastAPI's async event loop.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(apply_for_job(user_id, job_id, application_id, job_url, cv_url))
        return result
    finally:
        loop.close()
