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

            # Extract page content
            print(f"[APPLY_JOB] Extracting page content", flush=True)
            page_content = await _extract_page_content(page)

            # Analyze with LLM
            print(f"[APPLY_JOB] Analyzing page with LLM", flush=True)
            analysis = await _analyze_application_method(job_url, page_content, cv_data)

            if not analysis:
                result["error"] = "Failed to analyze application method"
                result["status"] = "requires_manual"
                result["method"] = "manual"
                return result

            method = analysis.get('method')  # 'email', 'form', or 'manual'
            instructions = analysis.get('instructions')

            print(f"[APPLY_JOB] Detected method: {method}", flush=True)
            print(f"[APPLY_JOB] Instructions: {instructions}", flush=True)

            # Execute application method
            if method == 'email':
                result["method"] = "email"
                result["action"] = f"Found email: {instructions}"
                result["status"] = "requires_manual"  # Will be sent by email agent
                print(f"[APPLY_JOB] Email application detected: {instructions}", flush=True)

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
                    result["action"] = form_result.get('message', 'Could not auto-fill form')
                    print(f"[APPLY_JOB] Form submission failed: {result['error']}", flush=True)

            else:  # manual
                result["method"] = "manual"
                result["status"] = "requires_manual"
                result["action"] = instructions or "This application requires manual interaction"
                print(f"[APPLY_JOB] Manual application required: {result['action']}", flush=True)

            await context.close()
            await browser.close()

        # Update application status
        _update_application_status(application_id, result['status'])

        # Log action
        _log_application_action(user_id, application_id, result['method'], result['action'])

        print(f"[APPLY_JOB] Application complete: status={result['status']}, method={result['method']}", flush=True)

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


async def _analyze_application_method(job_url: str, page_content: str, cv_data: dict) -> Optional[Dict]:
    """
    Use LLM to analyze the job page and decide application method.

    Returns:
        {
            "method": "email" | "form" | "manual",
            "instructions": str (specific instructions for the method)
        }
    """
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        prompt = f"""Analyze this job application page and decide HOW to apply.

JOB URL: {job_url}

PAGE CONTENT:
{page_content}

DETERMINE:
1. Can this be auto-filled with a form? Look for input fields, textareas, etc.
2. Is there an "Apply" or "Submit" button visible?
3. Is there a company email for applications? Look for "apply@", "careers@", "hr@"
4. Does it require uploading files/attachments?
5. Are there required custom fields that can't be auto-filled?

DECIDE ONE:
- "form" → If there's a visible application form with standard fields (name, email, CV) that can be auto-filled. Provide specific field IDs or names to fill.
- "email" → If there's no form but a recruiter email is visible. Provide the email address.
- "manual" → If the page requires complex interactions, external sites, custom questions, or account creation.

RESPOND AS JSON:
{{
  "method": "form" | "email" | "manual",
  "instructions": "specific details for this method (field IDs for form, email address for email, explanation for manual)"
}}"""

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
            if result.get('method') in ['email', 'form', 'manual']:
                print(f"[APPLY_JOB ANALYZE] Method: {result['method']}", flush=True)
                return result
            else:
                print(f"[APPLY_JOB ANALYZE] Invalid method in response: {result.get('method')}", flush=True)
                return None
        except ValueError as e:
            print(f"[APPLY_JOB ANALYZE] Failed to extract JSON: {str(e)}", flush=True)
            return None

    except Exception as e:
        print(f"[APPLY_JOB ANALYZE] ERROR: {type(e).__name__}: {str(e)}", flush=True)
        return None


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
