"""Configuration settings for the Explorastur application."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# LLM API settings
LLM_API_BASE_URL = os.getenv("LLM_API_BASE_URL", "http://localhost:1234/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "default")  # Model identifier if needed

# Default prompt template for event extraction
DEFAULT_PROMPT_TEMPLATE = """
Extract event information from the following HTML content. Return a JSON array with objects containing these fields:
- title: The name or title of the event
- date: The date of the event (YYYY-MM-DD format if possible)
- time: The time of the event
- location: Where the event takes place
- description: A brief description of the event

HTML Content:
{html_content}

Return ONLY a valid JSON array with the extracted events, nothing else.
"""

# Output settings
DEFAULT_OUTPUT_FORMAT = "json"  # Options: json, console
DEFAULT_OUTPUT_FILE = "events.json"
