"""
Utility functions for web scraping operations.
"""

import logging
import requests
from bs4 import BeautifulSoup
import re
from typing import Dict, List, Optional, Union, Any, Tuple

logger = logging.getLogger('explorastur')

def fetch_page(url: str, timeout: int = 30) -> Optional[str]:
    """
    Fetch a webpage and return its HTML content.

    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds

    Returns:
        HTML content as string or None if request failed
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return None

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

    if relative_url.startswith('http'):
        return relative_url

    if relative_url.startswith('/'):
        return f"{base_url}{relative_url}"
    else:
        return f"{base_url}/{relative_url}"

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