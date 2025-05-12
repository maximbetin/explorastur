"""
Utility classes for date and text processing.
"""

import datetime
import logging
import requests
import re
from typing import List, Tuple, Optional, Dict, Any, Callable
from urllib.parse import urlparse
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger('explorastur')

# Constants
SPANISH_MONTHS_LOWER = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
]

SPANISH_MONTHS_CAPITAL = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

# Map of month numbers to names
SPANISH_MONTHS_MAP = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
}

# Regex patterns for date extraction
DATE_PATTERNS = {
    'single_day': r'(\d{1,2})\s+de\s+(' + r'|'.join(SPANISH_MONTHS_LOWER) + r')',
    'range': r'(\d{1,2})\s*[-/]\s*(\d{1,2})\s+de\s+(' + r'|'.join(SPANISH_MONTHS_LOWER) + r')',
    'month_long': r'(todo\s+el\s+mes|durante\s+todo\s+el\s+mes)(\s+de\s+(' + r'|'.join(SPANISH_MONTHS_LOWER) + r'))?',
    'del_al': r'[Dd]el\s+(\d{1,2})\s+al\s+(\d{1,2})\s+de\s+(' + r'|'.join(SPANISH_MONTHS_LOWER) + r')',
    'with_time': r'(\d{1,2})\s+de\s+(' + r'|'.join(SPANISH_MONTHS_LOWER) + r')\s+a\s+las\s+(\d{1,2}):(\d{2})'
}

# Time patterns
TIME_PATTERNS = {
    'standard': r'(\d{1,2}):(\d{2})',
    'with_h': r'(\d{1,2})h(\d{2})?',
    'with_a_las': r'a\s+las\s+(\d{1,2})[\.:]?(\d{2})?'
}

MONTH_LONG_PATTERNS = ["todo el mes", "durante todo el mes"]

# Location patterns
LOCATION_PATTERNS = {
    'lugar': r'lugar:?\s*([^.,\n]+)',
    'en_el': r'en\s+(?:el|la|los|las)?\s+([\w\s.-]+)(?:de|en)\s+([\w\s]+)',
    'en': r'en\s+([\w\s.-]+)'
}


class DateProcessor:
    """Class to handle date processing and formatting."""

    @staticmethod
    def get_current_month_year() -> str:
        """Get the current month name in Spanish with first letter capitalized."""
        now = datetime.datetime.now()
        return SPANISH_MONTHS_CAPITAL[now.month - 1]

    @staticmethod
    def get_current_month_name() -> str:
        """Get just the current month name in Spanish (lowercase)."""
        now = datetime.datetime.now()
        return SPANISH_MONTHS_LOWER[now.month - 1]

    @staticmethod
    def extract_days_from_range(date_pattern: str) -> List[int]:
        """
        Extract all day numbers from a date range pattern.
        Handles formats like:
        - "10 de mayo" (single day)
        - "10-15 de mayo" (range with hyphen)
        - "10 y 12 de mayo" (multiple days)
        - "10-11 y 15-17 de mayo" (multiple ranges)
        - "9 a 18 de mayo" (range with 'a')
        Works with any month name, not just "mayo"
        """
        if not date_pattern:
            return []

        day_numbers = []

        # Match single days: "10 de mayo"
        single_days = re.findall(r'(\d+)(?=\s+de\s+[a-zA-Z]+)', date_pattern)
        day_numbers.extend([int(day) for day in single_days])

        # Match day ranges: "10-15 de mayo"
        day_ranges = re.findall(r'(\d+)-(\d+)(?=\s+de\s+[a-zA-Z]+)', date_pattern)
        for start, end in day_ranges:
            day_numbers.extend(range(int(start), int(end) + 1))

        # Match 'a' ranges: "9 a 18 de mayo"
        a_ranges = re.findall(r'(\d+)\s+a\s+(\d+)(?=\s+de\s+[a-zA-Z]+)', date_pattern)
        for start, end in a_ranges:
            day_numbers.extend(range(int(start), int(end) + 1))

        # Match separated ranges: "10 y 15 de mayo"
        y_days = re.findall(r'(\d+)(?=\s+y\s+\d+)', date_pattern)
        day_numbers.extend([int(day) for day in y_days])

        # Look for additional formats: "del 10 al 15"
        del_al_match = re.search(r'del\s+(\d+)\s+al\s+(\d+)', date_pattern)
        if del_al_match:
            start, end = del_al_match.groups()
            day_numbers.extend(range(int(start), int(end) + 1))

        # Special case for "todo el mes" or month-long events
        if any(pattern in date_pattern.lower() for pattern in MONTH_LONG_PATTERNS):
            # Add all days of the month (assuming 31 days to be safe)
            day_numbers.extend(range(1, 32))

        # Ensure we return unique days in ascending order
        return sorted(set(day_numbers))

    @staticmethod
    def is_future_event(date_pattern: str, current_date: int) -> bool:
        """
        Determine if an event is in the future based on its date pattern.
        Returns True if it's a month-long event or any day in the range is >= current_date.
        Works with any month name, not just specific to a specific month.

        Args:
            date_pattern: The date string to analyze
            current_date: The current day of month

        Returns:
            True if the event is in the future, False otherwise
        """
        current_month = datetime.datetime.now().month - 1  # 0-indexed for list

        # Check if date refers to a future month
        for i, month in enumerate(SPANISH_MONTHS_LOWER):
            if month in date_pattern.lower():
                if i > current_month:
                    return True
                elif i < current_month:
                    return False
                break  # It's the current month, continue with day-based filtering

        # Always keep month-long events for the current month
        if any(pattern in date_pattern.lower() for pattern in MONTH_LONG_PATTERNS):
            return True

        # Extract all day numbers from the date pattern
        day_numbers = DateProcessor.extract_days_from_range(date_pattern)

        # If no days could be extracted, keep the event to be safe
        if not day_numbers:
            return True

        # Keep if any day in the range is in the future
        return any(day >= current_date for day in day_numbers)

    @staticmethod
    def date_sort_key(date_str: str) -> Tuple[int, int]:
        """
        Create a sort key for dates to ensure correct chronological ordering.
        Month-long events go first, then events are sorted by month and earliest day.

        Returns:
            Tuple of (month_index, earliest_day) for sorting
        """
        # Default to current month if none found
        month_index = datetime.datetime.now().month - 1  # 0-indexed

        # Try to find month in the date string
        for i, month in enumerate(SPANISH_MONTHS_LOWER):
            if month in date_str.lower():
                month_index = i
                break

        # Month-long events first in the current month
        if any(pattern in date_str.lower() for pattern in MONTH_LONG_PATTERNS):
            return (month_index, 0)

        # Get all days in the range
        days = DateProcessor.extract_days_from_range(date_str)

        # Return month index and first/earliest day, or high number if none found
        return (month_index, min(days) if days else 100)

    @staticmethod
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

    @staticmethod
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

    @staticmethod
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

    @staticmethod
    def get_spanish_month_name(month_num: int) -> str:
        """
        Get Spanish month name from month number.

        Args:
            month_num: Month number (1-12)

        Returns:
            Spanish month name or empty string if invalid month number
        """
        return SPANISH_MONTHS_MAP.get(month_num, "")


class TextProcessor:
    """Class to handle text cleaning and processing."""

    # Common Spanish venue words
    VENUE_WORDS = [
        "Teatro", "Auditorio", "Sala", "Centro", "Pabellón",
        "Plaza", "Factoría", "Recinto", "Museo"
    ]

    # Common Spanish city names
    CITY_NAMES = ["Oviedo", "Gijón", "Avilés", "Langreo", "Mieres", "Siero", "Lugones"]

    # Patterns for non-event titles
    NON_EVENT_PATTERNS = [
        r'agenda', r'asturias en [a-z]+', r'¿quieres saber',
        r'planes', r'vamos allá'
    ]

    # Date prefix patterns to remove from titles
    DATE_PREFIX_PATTERNS = [
        r'^Hasta el \d+ de [a-zA-Z]+',
        r'^Durante todo el mes de [a-zA-Z]+',
        r'^\d+ a \d+ de [a-zA-Z]+',
        r'^\d+-\d+ de [a-zA-Z]+'
    ]

    # Small words that should be lowercase in titles unless they're the first word
    SMALL_WORDS = [
        'a', 'e', 'o', 'y', 'u', 'de', 'la', 'el', 'del', 'los', 'las',
        'en', 'con', 'por', 'para', 'al', 'su', 'sus', 'tu', 'tus',
        'mi', 'mis', 'un', 'una', 'unos', 'unas', 'lo', 'que'
    ]

    @staticmethod
    def clean_title(title: str, date_pattern: Optional[str] = None, fix_capitalization: bool = False) -> str:
        """
        Clean up event title, removing date patterns and fixing formatting issues.

        Args:
            title: The title to clean
            date_pattern: Optional date pattern to remove from the title
            fix_capitalization: Whether to fix the capitalization of title words

        Returns:
            Cleaned title string
        """
        if not title or title == ":":
            return ""

        # Remove title prefixes that start with colon
        if title.startswith(":"):
            title = title[1:].strip()

        # Remove date from title if it starts with it
        if date_pattern and title.startswith(date_pattern):
            title = title[len(date_pattern):].strip()

        # Clean up titles with date prefixes
        title = re.sub(r'^(\d+\s+de\s+[a-zA-Z]+\s+)', '', title)

        # Remove common date prefixes from title
        for prefix in TextProcessor.DATE_PREFIX_PATTERNS:
            title = re.sub(prefix, '', title)

        # Fix malformed quotes in titles
        if title.startswith('"') and '"' not in title[1:]:
            title = title[1:].strip()
        if title.startswith('"') and title.endswith('"'):
            title = title[1:-1].strip()
        elif title.startswith('"'):
            title = title[1:].strip()
        elif title.endswith('"'):
            title = title[:-1].strip()

        # Fix dangling quotes in the middle of titles
        if '"' in title and title.count('"') == 1:
            title = title.replace('"', '')

        # Remove any remaining quotes anywhere in the title
        title = title.replace('"', '')

        # Remove "Ver evento" prefix
        title = re.sub(r'^Ver evento\s+', '', title)

        # Fix encoding issues with HTML entities
        title = title.replace("&amp;", "&").replace("&quot;", "\"")

        # Remove leading colons, dashes, etc.
        title = re.sub(r'^[:\-–—]+\s*', '', title)

        # Apply text formatting fixes
        title = TextProcessor._apply_formatting_fixes(title)

        # Fix specific titles - consider moving to a configuration file if this grows
        if title.startswith("1 a 4 de mayo L.E.V. Festival"):
            title = "L.E.V. Festival"

        # Fix capitalization if requested
        if fix_capitalization:
            title = TextProcessor._fix_title_capitalization(title)

        return title

    @staticmethod
    def _fix_title_capitalization(title: str) -> str:
        """
        Fix capitalization in titles, making appropriate words lowercase.

        Args:
            title: The title to fix

        Returns:
            Title with fixed capitalization
        """
        words = title.split()
        fixed_words = []

        for i, word in enumerate(words):
            # Skip small common words and acronyms (2 chars or less)
            if word.isupper() and len(word) > 2:
                word = word.capitalize()
            # Check if it's a lowercase common preposition/article and not the first word
            elif word.lower() in TextProcessor.SMALL_WORDS and i > 0:
                word = word.lower()
            # Capitalize first word
            elif i == 0 and not word.isupper():
                word = word.capitalize()
            fixed_words.append(word)

        return ' '.join(fixed_words)

    @staticmethod
    def _apply_formatting_fixes(text: str) -> str:
        """Apply common formatting fixes to text."""
        # Fix quotes in the middle
        text = re.sub(r'([a-zA-Z])"([a-zA-Z])', r'\1 \2', text)

        # Clean up quotes and spaces
        text = re.sub(r'^["\']\s*', '', text)  # Remove starting quotes
        text = re.sub(r'\s*["\']$', '', text)  # Remove ending quotes
        text = re.sub(r'\s{2,}', ' ', text).strip()

        # Fix concatenated words (like "Primeraexposición")
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)

        # Fix missing spaces after punctuation
        text = re.sub(r'([a-zA-Z])\.([A-Z])', r'\1. \2', text)
        text = re.sub(r'([a-zA-Z]),([a-zA-Z])', r'\1, \2', text)
        text = re.sub(r'([a-zA-Z])"([a-zA-Z])', r'\1" \2', text)

        # Fix specific concatenation issues
        prefixes = ['la', 'el', 'de', 'del', 'un']
        for prefix in prefixes:
            text = re.sub(fr'{prefix}([A-Z])', fr'{prefix} \1', text)

        # Remove common Spanish prefixes
        text = re.sub(r'^en\s+(?:el|la|los|las)\s+', '', text)
        text = re.sub(r'^en\s+', '', text)

        # Fix special case patterns
        text = re.sub(r'el día$', '', text)
        text = re.sub(r'con la banda.*$', '', text)
        text = re.sub(r'para presentar.*$', '', text)

        # Fix "Dr," which should be "Dr." in addresses
        text = re.sub(r'Dr,', 'Dr.', text)

        # Clean up by removing trailing punctuation
        return text.rstrip('- ,:')

    @staticmethod
    def extract_location_from_title(title: str) -> str:
        """
        Extract location information from event title.

        Args:
            title: The event title to analyze

        Returns:
            Extracted location string or empty string if none found
        """
        # Clean up the title first to fix any formatting issues
        clean_title = TextProcessor._apply_formatting_fixes(title)

        # Try to extract location that has venue words
        for word in TextProcessor.VENUE_WORDS:
            pattern = f"{word}\\s+[\\w\\s\\.]+"
            match = re.search(pattern, clean_title, re.IGNORECASE)
            if match:
                return match.group(0)

        return ""

    @staticmethod
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

        # Look for venue keywords in the text
        for venue in TextProcessor.VENUE_WORDS:
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
        for city in TextProcessor.CITY_NAMES:
            if re.search(fr'\b{city}\b', text, re.IGNORECASE):
                return city

        return ""

    @staticmethod
    def extract_venue_and_city(location: str) -> str:
        """
        Extract venue and city from location or truncate if too long.

        Args:
            location: Location text

        Returns:
            Extracted venue and city or truncated location
        """
        # If location is too long, try to extract just the venue name
        if len(location) > 80:
            # Try to extract just the venue name by looking for common patterns
            venue_pattern = r'^([^,.]+(?:' + '|'.join(TextProcessor.VENUE_WORDS) + r')[^,.]{0,30})'
            venue_match = re.match(venue_pattern, location)

            if venue_match:
                location = venue_match.group(1).strip()

            # If still too long, truncate and add ellipsis
            if len(location) > 80:
                location = location[:77] + '...'

        # Extract venue and city when possible using more flexible patterns
        venue_keywords_str = '|'.join(TextProcessor.VENUE_WORDS)
        venue_city_pattern = fr'([^,.]+(?:{venue_keywords_str})[^,.]+)(?:de|en)\s+([^,.]+)'

        match = re.search(venue_city_pattern, location)
        if match:
            venue = match.group(1).strip()
            city = match.group(2).strip()
            # Remove any trailing dates or times
            city = re.sub(r'\d+\s+de\s+\w+$', '', city).strip()
            city = re.sub(r'el\s+\w+\s+\d+$', '', city).strip()
            return f"{venue} ({city})"

        # If the pattern didn't match but there's a venue keyword, clean it up
        for keyword in TextProcessor.VENUE_WORDS:
            if keyword in location:
                # Just clean up the location without trying to separate venue/city
                location = re.sub(r'\d+\s+de\s+\w+', '', location).strip()
                location = re.sub(r'el\s+\w+\s+\d+', '', location).strip()
                return location

        return location

    @staticmethod
    def clean_location(location: str) -> str:
        """
        Clean up location text to extract just the venue and city.

        Args:
            location (str): Raw location text

        Returns:
            str: Cleaned location text
        """
        if not location:
            return ""

        # Replace line breaks with spaces
        location = re.sub(r'[\r\n]+', ' ', location)

        # Fix formatting issues
        location = TextProcessor._apply_formatting_fixes(location)

        # Handle specific location patterns
        specific_locations = {
            "El Atrio": "Centro Comercial 'El Atrio' (C/ Cámara, Cuba, Dr.), Avilés" if "Cuba" in location else location,
            "La Florida con": "Centro Social La Florida, Oviedo",
            "Factoría Cultural": "Factoría Cultural, Avilés",
            "NIEMEYER": "Centro Niemeyer, Avilés"
        }

        # Check for specific location patterns
        for pattern, replacement in specific_locations.items():
            if pattern in location:
                return replacement

        # Handle truncated locations
        if location.strip() == 'Plaza':
            return 'Plaza de Asturias, Oviedo'
        if location.strip() == 'Centro Social':
            return 'Centro Social de Oviedo'
        if 'Centro Social' in location and len(location.strip()) < 20:
            return f"{location}, Oviedo"

        # Clean up excessive commas and spacing in addresses
        location = re.sub(r',\s*,', ',', location)
        location = re.sub(r'\s+', ' ', location)

        # Extract venue and city or truncate if too long
        location = TextProcessor.extract_venue_and_city(location)

        return location.strip()

    @staticmethod
    def is_non_event(title: str) -> bool:
        """
        Check if the title is likely not an actual event.

        Args:
            title: The title to check

        Returns:
            True if this appears to be a non-event, False otherwise
        """
        return any(re.search(pattern, title.lower()) for pattern in TextProcessor.NON_EVENT_PATTERNS)


class UrlUtils:
    """Class for handling URL operations."""

    @staticmethod
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

    @staticmethod
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
            return UrlUtils.make_absolute_url(base_url, href_str)

    @staticmethod
    def extract_url_from_onclick(element: Any, base_url: str, pattern: str = r"'([^']+)'") -> str:
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
            return UrlUtils.make_absolute_url(base_url, href)

    @staticmethod
    def get_hostname(url: str) -> str:
        """
        Extract the hostname from a URL.

        Args:
            url: The URL to parse

        Returns:
            Hostname as string or empty string if URL is invalid
        """
        try:
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return ""


class HtmlUtils:
    """Class for handling HTML parsing operations."""

    @staticmethod
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

    @staticmethod
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

    @staticmethod
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


class EventUtils:
    """Class for handling event extraction and processing."""

    @staticmethod
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
                    data['url'] = UrlUtils.make_absolute_url(base_url, href_str)
            else:
                # For text fields
                data[field] = element.get_text().strip()

        return data

    @staticmethod
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
            next_url = UrlUtils.make_absolute_url(base_url, href)

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