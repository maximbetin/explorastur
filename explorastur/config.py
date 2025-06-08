"""Configuration settings for the Explorastur application."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# LLM API settings
LLM_API_BASE_URL = os.getenv("LLM_API_BASE_URL", "http://localhost:1234/v1")

# Default prompt template for event extraction
DEFAULT_PROMPT_TEMPLATE = """
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

# Output settings
DEFAULT_OUTPUT_FORMAT = "json"  # Options: json, console
DEFAULT_OUTPUT_FILE = "events.json"
