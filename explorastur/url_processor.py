"""Module for processing URLs and extracting event information using LLM."""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import json
import httpx
from urllib.parse import urlparse

from explorastur.event_parser import Event, parse_events
from explorastur.config import LLM_API_BASE_URL, DEFAULT_PROMPT_TEMPLATE


@dataclass
class ProcessingResult:
  """Result of processing a URL for events."""
  url: str
  events: List[Event]
  error: Optional[str] = None
  processed_at: datetime = datetime.now()

  def to_dict(self) -> Dict[str, Any]:
    """Convert result to dictionary format."""
    return {
        "url": self.url,
        "events": [event.dict() for event in self.events],
        "error": self.error,
        "processed_at": self.processed_at.isoformat()
    }


class URLEventProcessor:
  """Process URLs to extract event information using LLM."""

  def __init__(self, api_base_url: str = LLM_API_BASE_URL):
    """Initialize the URL processor with LLM API settings."""
    self.api_base_url = api_base_url
    self.client = httpx.Client(timeout=60.0)
    self._validate_url = urlparse

  def _is_valid_url(self, url: str) -> bool:
    """Validate if a string is a proper URL."""
    try:
      result = self._validate_url(url)
      return all([result.scheme, result.netloc])
    except Exception:
      return False

  def _get_llm_response(self, url: str) -> List[Dict[str, Any]]:
    """Get event information from LLM for a given URL."""
    prompt = f"""
        Analyze the content at this URL and extract all upcoming events:
        {url}

        Return a JSON array of events, where each event has these fields:
        - "title": Short name of the event
        - "date": In "YYYY-MM-DD" format (or best effort if not available)
        - "time": In "HH:MM" 24-hour format (or "All day" / "Unknown" if unclear)
        - "location": Venue or address
        - "description": 1–2 sentence summary

        Only include actual events — skip ads, generic text, or navigation elements.
        Return only the JSON array, no extra text.
        """

    url = f"{self.api_base_url}/chat/completions"
    payload = {
        "model": "default",
        "messages": [
            {"role": "system", "content": "You extract structured event information from web content."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }

    response = self.client.post(url, json=payload)
    response.raise_for_status()

    result = response.json()
    content = result["choices"][0]["message"]["content"]
    events = json.loads(content)

    if not isinstance(events, list):
      events = [events] if isinstance(events, dict) else []

    return events

  def process_url(self, url: str) -> ProcessingResult:
    """
    Process a single URL to extract events.

    Args:
        url: The URL to process

    Returns:
        ProcessingResult containing extracted events or error information
    """
    if not self._is_valid_url(url):
      return ProcessingResult(url=url, events=[], error="Invalid URL format")

    try:
      events_data = self._get_llm_response(url)
      events = parse_events(events_data)
      return ProcessingResult(url=url, events=events)
    except Exception as e:
      return ProcessingResult(url=url, events=[], error=str(e))

  def process_urls(self, urls: List[str]) -> List[ProcessingResult]:
    """
    Process multiple URLs to extract events.

    Args:
        urls: List of URLs to process

    Returns:
        List of ProcessingResult objects, one for each URL
    """
    return [self.process_url(url) for url in urls]

  def close(self):
    """Close the HTTP client."""
    self.client.close()
