"""Module for interacting with the local LLM via OpenAI-compatible API."""
import json
from typing import Any, Dict, List, Optional

import httpx

from explorastur.config import LLM_API_BASE_URL, DEFAULT_PROMPT_TEMPLATE


class LLMClient:
  """Client for interacting with a local LLM via OpenAI-compatible API."""

  def __init__(self, api_base_url: str = LLM_API_BASE_URL):
    """
    Initialize the LLM client.

    Args:
        api_base_url: Base URL for the LLM API
    """
    self.api_base_url = api_base_url
    self.client = httpx.Client(timeout=60.0)  # Longer timeout for LLM processing

  def extract_events(self, html_content: str, prompt_template: str = DEFAULT_PROMPT_TEMPLATE) -> List[Dict[str, Any]]:
    """
    Extract event information from HTML content using the LLM.

    Args:
        html_content: The HTML content to process
        prompt_template: Template for the prompt to send to the LLM

    Returns:
        List of extracted events as dictionaries

    Raises:
        Exception: If the LLM request fails or returns invalid JSON
    """
    # Format the prompt with the HTML content
    prompt = prompt_template.format(html_content=html_content)

    # Prepare the API request
    url = f"{self.api_base_url}/chat/completions"
    payload = {
        "model": "default",  # Local LLM models typically ignore this
        "messages": [
            {"role": "system", "content": "You extract structured event information from HTML."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1  # Low temperature for more deterministic results
    }

    # Make the API request
    response = self.client.post(url, json=payload)
    response.raise_for_status()

    # Parse the response
    result = response.json()

    try:
      # Extract the content from the response
      content = result["choices"][0]["message"]["content"]

      # Try to parse the JSON response
      events = json.loads(content)

      # Ensure we have a list of events
      if not isinstance(events, list):
        if isinstance(events, dict):
          # Single event returned as a dict
          events = [events]
        else:
          raise ValueError("LLM did not return a list or dictionary")

      return events

    except (KeyError, json.JSONDecodeError) as e:
      # Handle parsing errors
      raise ValueError(f"Failed to parse LLM response: {str(e)}")

  def close(self):
    """Close the HTTP client."""
    self.client.close()
