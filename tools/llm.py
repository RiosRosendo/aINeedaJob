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
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')


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
    """Call Groq API."""
    try:
        from groq import Groq

        client = Groq(api_key=GROQ_API_KEY)
        message = client.chat.completions.create(
            model=model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.choices[0].message.content
    except ImportError:
        raise Exception("groq package not installed. Run: pip install groq")
    except Exception as e:
        raise Exception(f"Groq API call failed: {str(e)}")
