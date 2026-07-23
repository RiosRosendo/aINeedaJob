"""
LLM API wrapper for aINeedJob.

Unified interface for Groq API (free, fast inference).

Required environment variables:
  - GROQ_API_KEY: API key for Groq (get from https://console.groq.com)
  - GROQ_MODEL: Model name (default: llama-3.1-8b-instant)

Example usage:
  from tools.llm import call_llm

  # Using Groq (Llama)
  response = call_llm(
    prompt="Extract job title from this description: ...",
    model="llama-3.1-8b-instant"
  )
"""

import os
import time
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')
MAX_RETRIES = 3
RETRY_DELAYS = [2, 4, 8, 16]  # Exponential backoff: 2, 4, 8, 16 seconds


def call_llm(prompt, model=None):
    """
    Call Groq LLM with a prompt.

    Args:
        prompt (str): The prompt to send to the LLM
        model (str): Model name (e.g., 'llama-3.1-8b-instant').
                     If None, uses GROQ_MODEL from .env

    Returns:
        str: LLM response text

    Raises:
        Exception: If API call fails or API key not set
    """
    if not model:
        model = GROQ_MODEL

    if not GROQ_API_KEY:
        raise Exception("GROQ_API_KEY not set in .env. Get one from https://console.groq.com")

    return _call_groq(prompt, model)


def _call_groq(prompt, model):
    """Call Groq API with exponential backoff retry on rate limits."""
    try:
        from groq import Groq
    except ImportError:
        raise Exception("groq package not installed. Run: pip install groq")

    client = Groq(api_key=GROQ_API_KEY)

    for attempt in range(MAX_RETRIES + 1):
        try:
            message = client.chat.completions.create(
                model=model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.choices[0].message.content

        except Exception as e:
            error_str = str(e)

            if "429" in error_str or "rate" in error_str.lower():
                if attempt < MAX_RETRIES:
                    wait_time = RETRY_DELAYS[attempt] if attempt < len(RETRY_DELAYS) else RETRY_DELAYS[-1]
                    print(f"[LLM_RETRY] Rate limited, waiting {wait_time}s before retry {attempt + 1}/{MAX_RETRIES}")
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"Groq rate limit exceeded after {MAX_RETRIES} retries: {error_str}")
            else:
                raise Exception(f"Groq API call failed: {error_str}")
