"""
Utility classes for date and text processing.
"""

import datetime
import re
from typing import List, Tuple, Optional

# Constants
SPANISH_MONTHS_LOWER = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
]

SPANISH_MONTHS_CAPITAL = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

# Regex patterns
MONTH_PATTERN = r'\b(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b'
MONTH_LONG_PATTERNS = ["todo el mes", "durante todo el mes"]


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


class TextProcessor:
    """Class to handle text cleaning and processing."""

    # Common Spanish venue words
    VENUE_WORDS = [
        "Teatro", "Auditorio", "Sala", "Centro", "Pabellón",
        "Plaza", "Factoría", "Recinto", "Museo"
    ]

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

    @staticmethod
    def clean_title(title: str, date_pattern: Optional[str] = None) -> str:
        """
        Clean up event title, removing date patterns and fixing formatting issues.

        Args:
            title: The title to clean
            date_pattern: Optional date pattern to remove from the title

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

        # Fix dangling quotes in the middle of titles
        if '"' in title and title.count('"') == 1:
            title = title.replace('"', '')

        # Apply text formatting fixes
        title = TextProcessor._apply_formatting_fixes(title)

        # Fix specific titles - consider moving to a configuration file if this grows
        if title.startswith("1 a 4 de mayo L.E.V. Festival"):
            title = "L.E.V. Festival"

        return title

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
    def is_non_event(title: str) -> bool:
        """
        Check if the title is likely not an actual event.

        Args:
            title: The title to check

        Returns:
            True if this appears to be a non-event, False otherwise
        """
        return any(re.search(pattern, title.lower()) for pattern in TextProcessor.NON_EVENT_PATTERNS)