"""
LLM API wrapper for aINeedJob.

Unified interface for both Anthropic Claude and OpenAI APIs.
Automatically routes requests based on model name.

Required environment variables:
  - ANTHROPIC_API_KEY: API key for Anthropic Claude
  - OPENAI_API_KEY: API key for OpenAI GPT
  - ANTHROPIC_MODEL: Default Claude model (e.g., claude-sonnet-4-6)
  - OPENAI_MODEL: Default OpenAI model (e.g., gpt-4o)

Example usage:
  from tools.llm import call_llm

  # Using Claude
  response = call_llm(
    prompt="Extract job title from this description: ...",
    model="claude-sonnet-4-6"
  )

  # Using GPT
  response = call_llm(
    prompt="Analyze this job offer...",
    model="gpt-4o"
  )
"""

import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


def call_llm(prompt, model=None):
    """
    Call an LLM (Claude or GPT) with a prompt.

    Args:
        prompt (str): The prompt to send to the LLM
        model (str): Model name (e.g., 'claude-sonnet-4-6' or 'gpt-4o').
                     If None, uses ANTHROPIC_MODEL or OPENAI_MODEL from .env

    Returns:
        str: LLM response text

    Raises:
        Exception: If API call fails, no API key found, or model is unknown
    """
    if not model:
        model = os.getenv('ANTHROPIC_MODEL') or os.getenv('OPENAI_MODEL')

    if not model:
        raise Exception("No model specified and no default in .env")

    # Route to Anthropic Claude
    if 'claude' in model.lower():
        if not ANTHROPIC_API_KEY:
            raise Exception("ANTHROPIC_API_KEY not set in .env")
        return _call_anthropic(prompt, model)

    # Route to OpenAI GPT
    elif 'gpt' in model.lower():
        if not OPENAI_API_KEY:
            raise Exception("OPENAI_API_KEY not set in .env")
        return _call_openai(prompt, model)

    else:
        raise Exception(f"Unknown model: {model}. Use 'claude-*' or 'gpt-*'")


def _call_anthropic(prompt, model):
    """Call Anthropic Claude API."""
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception as e:
        raise Exception(f"Anthropic API call failed: {str(e)}")


def _call_openai(prompt, model):
    """Call OpenAI GPT API."""
    try:
        import openai

        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"OpenAI API call failed: {str(e)}")
