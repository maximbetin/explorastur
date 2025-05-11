"""
Utility functions for web scraping operations.
"""

import logging
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
from typing import Dict, List, Optional, Union, Any, Tuple

logger = logging.getLogger('explorastur')

def parse_html(html: str) -> Optional[BeautifulSoup]:
    """
    Parse HTML content into a BeautifulSoup object.

    Args:
        html: HTML content as string

    Returns:
        BeautifulSoup object or None if parsing failed
    """
    try:
        return BeautifulSoup(html, 'html.parser')
    except Exception as e:
        logger.error(f"Error parsing HTML: {e}")
        return None

def extract_text(element: Any, selector: str) -> str:
    """
    Extract text from an element using a CSS selector.

    Args:
        element: BeautifulSoup element to search within
        selector: CSS selector to find the target element

    Returns:
        Extracted text or empty string if element not found
    """
    found = element.select_one(selector)
    return found.get_text().strip() if found else ""

def extract_attribute(element: Any, selector: str, attribute: str) -> str:
    """
    Extract an attribute from an element using a CSS selector.

    Args:
        element: BeautifulSoup element to search within
        selector: CSS selector to find the target element
        attribute: The attribute to extract

    Returns:
        Extracted attribute value or empty string if element not found
    """
    found = element.select_one(selector)
    return found.get(attribute, "") if found else ""

def make_absolute_url(base_url: str, relative_url: str) -> str:
    """
    Convert a relative URL to an absolute URL.

    Args:
        base_url: The base URL of the website
        relative_url: The relative URL to convert

    Returns:
        Absolute URL
    """
    if not relative_url:
        return base_url

    # Remove fragment identifier from base_url
    if '#' in base_url:
        base_url = base_url.split('#')[0]

    # If it already starts with http, it's already absolute
    if relative_url.startswith(('http://', 'https://')):
        return relative_url

    # If it starts with a slash, append to the domain
    if relative_url.startswith('/'):
        # Extract domain from base_url
        parsed_base = urlparse(base_url)
        domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
        return domain + relative_url

    # Otherwise, it's relative to the current path
    # Remove the filename from the base_url if present
    if base_url.endswith('/'):
        return base_url + relative_url
    else:
        # Remove last path component
        base_url = base_url.rsplit('/', 1)[0] + '/'
        return base_url + relative_url

def extract_date_from_text(text: str) -> str:
    """
    Extract date information from text using common Spanish date patterns.

    Args:
        text: Text to extract date from

    Returns:
        Extracted date as string or empty string if no date found
    """
    # Pattern for dates like "12 de mayo"
    month_pattern = re.search(
        r'(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)',
        text,
        re.IGNORECASE
    )
    if month_pattern:
        return month_pattern.group(0)

    # Pattern for date ranges like "12-15 de mayo"
    range_pattern = re.search(
        r'(\d{1,2})\s*[-\/]\s*(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)',
        text,
        re.IGNORECASE
    )
    if range_pattern:
        return range_pattern.group(0)

    # Pattern for "todo el mes" or "durante todo el mes"
    month_long_pattern = re.search(
        r'(todo\s+el\s+mes|durante\s+todo\s+el\s+mes)(\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre))?',
        text,
        re.IGNORECASE
    )
    if month_long_pattern:
        return month_long_pattern.group(0)

    return ""

def extract_location_from_text(text: str) -> str:
    """
    Extract location information from text.

    Args:
        text: Text to extract location from

    Returns:
        Extracted location as string or empty string if no location found
    """
    # Common venue keywords
    venue_keywords = [
        "Teatro", "Auditorio", "Sala", "Centro", "Museo",
        "Plaza", "Pabellón", "Recinto", "Factoría"
    ]

    # Look for venue keywords in the text
    for venue in venue_keywords:
        venue_match = re.search(f"{venue}\\s+[\\w\\s\\.,]+", text, re.IGNORECASE)
        if venue_match:
            return venue_match.group(0).strip()

    # Try to match common location patterns
    location_patterns = [
        r'en\s+(?:el|la)?\s+([\w\s\.\-]+)(?:de|en)\s+([\w\s]+)',
        r'(?:el|la|los|las)\s+([\w\s\.]+)(?:de|en)\s+([\w\s\.\-]+)',
        r'en\s+([\w\s\.\-]+)'
    ]

    for pattern in location_patterns:
        location_match = re.search(pattern, text)
        if location_match:
            location = location_match.group(0).strip()
            # Remove "en el" or "en la" prefixes
            location = re.sub(r'^en\s+(?:el|la|los|las)\s+', '', location)
            location = re.sub(r'^en\s+', '', location)
            return location

    return ""