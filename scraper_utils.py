"""
Utility functions for web scraping operations.
"""

import logging
import requests
from bs4 import BeautifulSoup, Tag
import re
from urllib.parse import urlparse
from typing import Dict, List, Optional, Union, Any, Tuple, Callable, cast

logger = logging.getLogger('explorastur')

# Spanish months for use in multiple functions
SPANISH_MONTHS = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
}

SPANISH_MONTHS_LIST = list(SPANISH_MONTHS.values())

# Common regex patterns
TIME_PATTERNS = {
    'standard': r'(\d{1,2}):(\d{2})',
    'with_h': r'(\d{1,2})h(\d{2})?',
    'with_a_las': r'a\s+las\s+(\d{1,2})[\.:]?(\d{2})?'
}

DATE_PATTERNS = {
    'single_day': r'(\d{1,2})\s+de\s+(' + r'|'.join(SPANISH_MONTHS_LIST) + r')',
    'range': r'(\d{1,2})\s*[-/]\s*(\d{1,2})\s+de\s+(' + r'|'.join(SPANISH_MONTHS_LIST) + r')',
    'month_long': r'(todo\s+el\s+mes|durante\s+todo\s+el\s+mes)(\s+de\s+(' + r'|'.join(SPANISH_MONTHS_LIST) + r'))?',
    'del_al': r'[Dd]el\s+(\d{1,2})\s+al\s+(\d{1,2})\s+de\s+(' + r'|'.join(SPANISH_MONTHS_LIST) + r')',
    'with_time': r'(\d{1,2})\s+de\s+(' + r'|'.join(SPANISH_MONTHS_LIST) + r')\s+a\s+las\s+(\d{1,2}):(\d{2})'
}

LOCATION_PATTERNS = {
    'lugar': r'lugar:?\s*([^.,\n]+)',
    'en_el': r'en\s+(?:el|la|los|las)?\s+([\w\s.-]+)(?:de|en)\s+([\w\s]+)',
    'en': r'en\s+([\w\s.-]+)'
}

# HTML Parsing Utilities
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

# URL Handling Utilities
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

def extract_url_from_element(element: Any, base_url: str) -> str:
    """
    Extract a URL from an element, handling common patterns and converting to absolute URL.

    Args:
        element: BeautifulSoup element to extract URL from
        base_url: Base URL to use for relative URLs

    Returns:
        Extracted absolute URL or base_url if not found
    """
    # First check for <a> tags
    link = element.select_one('a')
    if not link:
        return base_url

    # Extract href attribute
    href = link.get('href', '')

    # Handle case where href is a list (some BS4 versions)
    if isinstance(href, list):
        href = href[0] if href else ""

    # Skip if href is empty
    if not href:
        return base_url

    # Make URL absolute if needed
    href_str = str(href)  # Ensure href is a string
    if href_str.startswith(('http://', 'https://')):
        return href_str
    else:
        return make_absolute_url(base_url, href_str)

def extract_url_from_onclick(element: Tag, base_url: str, pattern: str = r"'([^']+)'") -> str:
    """
    Extract URL from an onclick attribute, commonly found in buttons.

    Args:
        element: BeautifulSoup element that might have onclick
        base_url: Base URL to use for relative URLs
        pattern: Regex pattern to extract the URL from onclick

    Returns:
        Extracted URL or base_url if not found
    """
    if not hasattr(element, 'attrs') or 'onclick' not in element.attrs:
        return base_url

    onclick = element['onclick']

    # Ensure onclick is a string
    onclick_str = str(onclick)

    match = re.search(pattern, onclick_str)

    if not match:
        return base_url

    href = match.group(1)

    # Make URL absolute if needed
    if href.startswith(('http://', 'https://')):
        return href
    else:
        return make_absolute_url(base_url, href)

# Date Extraction Utilities
def extract_date_from_text(text: str) -> str:
    """
    Extract date information from text using common Spanish date patterns.

    Args:
        text: Text to extract date from

    Returns:
        Extracted date as string or empty string if no date found
    """
    if not text:
        return ""

    # Check each pattern in order of most specific to least specific
    for pattern_name, pattern in DATE_PATTERNS.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)

    return ""

def extract_time_from_text(text: str) -> str:
    """
    Extract time information from text.

    Args:
        text: Text to extract time from

    Returns:
        Extracted time as string or empty string if no time found
    """
    if not text:
        return ""

    # Pattern for times like "19:00" or "7:30"
    time_match = re.search(TIME_PATTERNS['standard'], text)
    if time_match:
        return time_match.group(0)

    # Pattern for times with 'h' like "19h30" or "19h"
    hour_match = re.search(TIME_PATTERNS['with_h'], text, re.IGNORECASE)
    if hour_match:
        hour = hour_match.group(1)
        minute = hour_match.group(2) or "00"
        return f"{hour}:{minute}"

    # Look for times mentioned with 'a las'
    a_las_match = re.search(TIME_PATTERNS['with_a_las'], text, re.IGNORECASE)
    if a_las_match:
        hour = a_las_match.group(1)
        minute = a_las_match.group(2) or "00"
        return f"{hour}:{minute}"

    return ""

def format_date_range(start_day: str, end_day: str, month: str) -> str:
    """
    Format a date range within the same month.

    Args:
        start_day: Starting day number as string
        end_day: Ending day number as string
        month: Month name

    Returns:
        Formatted date range string
    """
    # Remove leading zeros from days
    start_day = start_day.lstrip('0')
    end_day = end_day.lstrip('0')

    # Format as "X - Y de mes"
    return f"{start_day} - {end_day} de {month.lower()}"

def get_spanish_month_name(month_num: int) -> str:
    """
    Get Spanish month name from month number.

    Args:
        month_num: Month number (1-12)

    Returns:
        Spanish month name or empty string if invalid month number
    """
    return SPANISH_MONTHS.get(month_num, "")

# Location Extraction Utilities
def extract_location_from_text(text: str) -> str:
    """
    Extract location information from text.

    Args:
        text: Text to extract location from

    Returns:
        Extracted location as string or empty string if no location found
    """
    if not text:
        return ""

    # Common venue keywords
    venue_keywords = [
        "Teatro", "Auditorio", "Sala", "Centro", "Museo",
        "Plaza", "Pabellón", "Recinto", "Factoría"
    ]

    # Look for venue keywords in the text
    for venue in venue_keywords:
        venue_match = re.search(fr'{venue}\s+[\w\s.,]+', text, re.IGNORECASE)
        if venue_match:
            return venue_match.group(0).strip()

    # Try to match common location patterns
    for pattern_name, pattern in LOCATION_PATTERNS.items():
        location_match = re.search(pattern, text, re.IGNORECASE)
        if location_match:
            location = location_match.group(0).strip()
            # Remove common prefixes
            location = re.sub(r'^en\s+(?:el|la|los|las)\s+', '', location, re.IGNORECASE)
            location = re.sub(r'^en\s+', '', location, re.IGNORECASE)
            location = re.sub(r'^lugar:?\s*', '', location, re.IGNORECASE)
            return location

    # Try to match city names
    city_names = ["Oviedo", "Gijón", "Avilés", "Langreo", "Mieres", "Siero", "Lugones"]
    for city in city_names:
        if re.search(fr'\b{city}\b', text, re.IGNORECASE):
            return city

    return ""

# Event Extraction Utilities
def extract_common_event_data(container: Tag, selectors: Dict[str, str], base_url: str) -> Dict[str, str]:
    """
    Extract common event data from a container element using selectors.

    Args:
        container: BeautifulSoup Tag containing event data
        selectors: Dictionary mapping data types to CSS selectors
        base_url: Base URL for resolving relative URLs

    Returns:
        Dictionary with extracted event data
    """
    data = {
        'title': '',
        'date': '',
        'location': '',
        'url': base_url,
        'description': ''
    }

    # Process each field if selector exists
    for field in data.keys():
        if field not in selectors:
            continue

        selector = selectors[field]
        element = container.select_one(selector)

        if not element:
            continue

        # Handle URL field specially
        if field == 'url' and element.name == 'a' and element.has_attr('href'):
            href = element['href']
            if href:
                href_str = str(href)
                data['url'] = make_absolute_url(base_url, href_str)
        else:
            # For text fields
            data[field] = element.get_text().strip()

    return data

def process_pagination(soup: BeautifulSoup, selector: str, extract_func: Callable,
                       base_url: str, max_pages: int = 3) -> List[Dict[str, str]]:
    """
    Process pagination and extract events from multiple pages.

    Args:
        soup: BeautifulSoup object of the first page
        selector: CSS selector for the next page link
        extract_func: Function to extract events from a page
        base_url: Base URL for resolving relative links
        max_pages: Maximum number of pages to process

    Returns:
        List of events from all pages
    """
    all_events = []
    current_page = soup
    page_count = 1

    while current_page and page_count <= max_pages:
        # Extract events from current page
        page_events = extract_func(current_page)
        all_events.extend(page_events)

        # Find next page link
        next_link = current_page.select_one(selector)
        if not next_link or 'href' not in next_link.attrs:
            break

        # Get next page URL and ensure it's a string
        href = str(next_link['href'])
        next_url = make_absolute_url(base_url, href)

        # Fetch next page
        logger.info(f"Fetching next page: {next_url}")
        try:
            response = requests.get(next_url)
            if response.status_code != 200:
                break

            current_page = BeautifulSoup(response.text, 'html.parser')
            page_count += 1
        except Exception as e:
            logger.error(f"Error fetching next page: {e}")
            break

    return all_events

def clean_event_title(title: str) -> str:
    """
    Clean up an event title by removing common patterns and formatting issues.

    Args:
        title: Raw event title

    Returns:
        Cleaned event title
    """
    if not title:
        return ""

    # Remove leading/trailing whitespace
    title = title.strip()

    # Remove leading colons
    title = re.sub(r'^[:\-–—]+\s*', '', title)

    # Remove date patterns from beginning of title
    title = re.sub(r'^\d{1,2}\s+de\s+[a-zA-Z]+:\s*', '', title)

    # Remove "Ver evento" prefix
    title = re.sub(r'^Ver evento\s+', '', title)

    # Fix encoding issues with HTML entities
    title = title.replace("&amp;", "&").replace("&quot;", "\"")

    # Remove any other special characters that shouldn't be part of the title
    title = re.sub(r'["\']$', '', title)  # Remove trailing quotes

    return title