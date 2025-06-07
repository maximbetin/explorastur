"""Explorastur - A modular Python project for extracting event information from webpages using LLMs."""

__version__ = "0.1.0"

from explorastur.main import extract_events_from_source, save_events
from explorastur.event_parser import Event, parse_events, format_events
from explorastur.html_fetcher import get_html_content
from explorastur.llm_client import LLMClient

__all__ = [
    "extract_events_from_source",
    "save_events",
    "Event",
    "parse_events",
    "format_events",
    "get_html_content",
    "LLMClient",
]
