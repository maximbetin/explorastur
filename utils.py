"""
Utility classes for date and text processing.
"""

import datetime
import re

class DateProcessor:
    """Class to handle date processing and formatting."""

    @staticmethod
    def get_current_month_year():
        """Get the current month name in Spanish and year."""
        months = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        now = datetime.datetime.now()
        return f"{months[now.month]} {now.year}"

    @staticmethod
    def get_current_month_name():
        """Get just the current month name in Spanish."""
        months = {
            1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
            5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
            9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
        }
        now = datetime.datetime.now()
        return months[now.month]

    @staticmethod
    def extract_days_from_range(date_pattern):
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

        # Generic pattern for any month
        month_pattern = r'\b(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b'
        day_numbers = []

        # Match single days: "10 de mayo"
        single_days = re.findall(r'(\d+)(?=\s+de\s+[a-zA-Z]+)', date_pattern)
        if single_days:
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
        if y_days:
            day_numbers.extend([int(day) for day in y_days])

        # Look for additional formats: "del 10 al 15"
        del_al_match = re.search(r'del\s+(\d+)\s+al\s+(\d+)', date_pattern)
        if del_al_match:
            start, end = del_al_match.groups()
            day_numbers.extend(range(int(start), int(end) + 1))

        # Special case for "todo el mes" or month-long events
        if re.search(r'todo\s+el\s+mes|durante\s+todo\s+el\s+mes', date_pattern.lower()):
            # Add all days of the month (assuming 30 days to be safe)
            day_numbers.extend(range(1, 31))

        # Ensure we return unique days in ascending order
        return sorted(set(day_numbers))

    @staticmethod
    def is_future_event(date_pattern, current_date):
        """
        Determine if an event is in the future based on its date pattern.
        Returns True if it's a month-long event or any day in the range is >= current_date.
        Works with any month name, not just specific to May.
        """
        # List of all month names in Spanish (lowercase)
        months = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                 "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

        current_month = datetime.datetime.now().month - 1  # 0-indexed for list

        # Check if date refers to a future month
        for i, month in enumerate(months):
            if month in date_pattern.lower():
                # If month is in the future, keep the event
                if i > current_month:
                    return True
                # If month is in the past, filter out the event
                elif i < current_month:
                    return False
                # If it's the current month, continue with day-based filtering
                break

        # Always keep month-long events for the current month
        if "todo el mes" in date_pattern.lower() or "durante todo" in date_pattern.lower():
            return True

        # Extract all day numbers from the date pattern
        day_numbers = DateProcessor.extract_days_from_range(date_pattern)

        # If no days could be extracted, keep the event to be safe
        if not day_numbers:
            return True

        # Keep if any day in the range is in the future
        return any(day >= current_date for day in day_numbers)

    @staticmethod
    def date_sort_key(date_str):
        """
        Create a sort key for dates to ensure correct chronological ordering.
        Month-long events go first, then events are sorted by month and earliest day.
        Works with any month, not just May.
        """
        # List of months for ordering
        months = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                 "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

        # Default to current month if none found
        month_index = datetime.datetime.now().month - 1  # 0-indexed

        # Try to find month in the date string
        for i, month in enumerate(months):
            if month in date_str.lower():
                month_index = i
                break

        # Month-long events first in the current month
        if "todo el mes" in date_str.lower() or "durante todo" in date_str.lower():
            return (month_index, 0)

        # Get all days in the range
        days = DateProcessor.extract_days_from_range(date_str)

        # Return month index and first/earliest day, or high number if none found
        return (month_index, min(days) if days else 100)


class TextProcessor:
    """Class to handle text cleaning and processing."""

    @staticmethod
    def clean_description(text):
        """Clean up description text by removing common prefixes, dates, and urls."""
        if not text:
            return ""

        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)

        # Remove dates at the beginning
        text = re.sub(r'^(\d+(?:\s+[ay]\s+\d+)?\s+de\s+[a-zA-Z]+:?)', '', text)
        text = re.sub(r'^(\d+-\d+(?:\s+[ay]\s+\d+-\d+)?\s+de\s+[a-zA-Z]+:?)', '', text)

        # Remove common prefixes
        prefixes = ["el día", "los días", "el viernes", "el sábado", "el domingo",
                   "el lunes", "el martes", "el miércoles", "el jueves"]
        for prefix in prefixes:
            if text.lower().startswith(prefix):
                text = text[len(prefix):].strip()

        # Clean up any leftover punctuation at the beginning
        text = text.lstrip('.:,;- ')

        # Fix missing spaces after punctuation
        text = re.sub(r'([a-zA-Z])\.([A-Z])', r'\1. \2', text)
        text = re.sub(r'([a-zA-Z]),([A-Z])', r'\1, \2', text)

        # Fix missing spaces around names
        text = re.sub(r'([a-záéíóúñ])([A-ZÁÉÍÓÚÑ])', r'\1 \2', text)

        # Capitalize first letter if needed
        if text and len(text) > 1:
            text = text[0].upper() + text[1:]

        return text

    @staticmethod
    def clean_title(title, date_pattern=None):
        """Clean up event title, removing date patterns and fixing formatting issues."""
        if not title:
            return ""

        # Handle titles that are just colons
        if title == ":":
            return ""

        # Remove title prefixes that start with colon (commonly found in the data)
        if title.startswith(":"):
            title = title[1:].strip()

        # Remove date from title if it starts with it
        if date_pattern and title.startswith(date_pattern):
            title = title[len(date_pattern):].strip()

        # Clean up titles with date prefixes
        title = re.sub(r'^(\d+\s+de\s+[a-zA-Z]+\s+)', '', title)

        # Remove common date prefixes from title
        date_prefixes = [
            r'^Hasta el \d+ de [a-zA-Z]+',
            r'^Durante todo el mes de [a-zA-Z]+',
            r'^\d+ a \d+ de [a-zA-Z]+',
            r'^\d+-\d+ de [a-zA-Z]+'
        ]
        for prefix in date_prefixes:
            title = re.sub(prefix, '', title)

        # Fix malformed quotes in titles
        # Replace starting quote without closing quote
        if title.startswith('"') and '"' not in title[1:]:
            title = title[1:].strip()

        # Fix dangling quotes in the middle of titles
        if '"' in title and title.count('"') == 1:
            # Fix Nido-ritual" case and similar
            title = title.replace('"', '')

        # Fix quotes in the middle
        title = re.sub(r'([a-zA-Z])"([a-zA-Z])', r'\1 \2', title)

        # Clean up quotes and spaces
        title = re.sub(r'^["\']\s*', '', title)  # Remove starting quotes
        title = re.sub(r'\s*["\']$', '', title)  # Remove ending quotes
        title = re.sub(r'\s{2,}', ' ', title).strip()

        # Fix concatenated words (like "Primeraexposición")
        title = re.sub(r'([a-z])([A-Z])', r'\1 \2', title)

        # Fix missing spaces after punctuation
        title = re.sub(r'([a-zA-Z])\.([A-Z])', r'\1. \2', title)
        title = re.sub(r'([a-zA-Z]),([a-zA-Z])', r'\1, \2', title)

        # Clean up by removing trailing punctuation
        title = title.rstrip('- ,:')

        # Fix specific titles
        if title.startswith("1 a 4 de mayo L.E.V. Festival"):
            title = "L.E.V. Festival"

        return title

    @staticmethod
    def extract_location_from_title(title):
        """Extract location information from event title."""
        # Clean up the title first to fix any formatting issues
        clean_title = re.sub(r'([a-z])([A-Z])', r'\1 \2', title)
        clean_title = re.sub(r'([a-zA-Z]),([A-Z])', r'\1, \2', clean_title)

        # Common venue words in Spanish
        venue_words = ["Teatro", "Auditorio", "Sala", "Centro", "Pabellón",
                      "Plaza", "Factoría", "Recinto", "Museo"]

        # Try to extract location that has venue words
        for word in venue_words:
            pattern = f"{word}\\s+[\\w\\s\\.]+"
            match = re.search(pattern, clean_title, re.IGNORECASE)
            if match:
                return match.group(0)

        return ""

    @staticmethod
    def is_non_event(title):
        """Check if the title is likely not an actual event."""
        non_event_patterns = [
            r'agenda', r'asturias en [a-z]+', r'¿quieres saber',
            r'planes', r'vamos allá'
        ]

        return any(re.search(pattern, title.lower()) for pattern in non_event_patterns)

    @staticmethod
    def fix_incomplete_description(title, description):
        """Fix known incomplete descriptions or truncated text."""
        known_fixes = {
            "Jornadas Gastronómicas de la Llámpara,Villaviciosa":
                "9 a 18 de mayo: Jornadas Gastronómicas de la Llámpara en Villaviciosa",
            "San Isidro en Llanera":
                "10-11 y 16-18 de mayo: San Isidro en Llanera",
            "Semana de la Floración del Manzano en la Comarca de la Sidra":
                "1 a 4 de mayo: Semana de la Floración del Manzano en la Comarca de la Sidra",
            "Preba de la sidra de Gascona":
                "Celebración de la sidra asturiana en la calle Gascona de Oviedo"
        }

        # Apply known fixes
        if title in known_fixes and (not description or description.endswith(('a', '-'))):
            return known_fixes[title]

        # Fix truncated descriptions
        if description and (description.endswith('a') or description.endswith('-')):
            # Try to intelligently expand common truncations
            if description.endswith('a') and title.find("Llámpara") >= 0:
                return "9 a 18 de mayo: Jornadas Gastronómicas de la Llámpara en Villaviciosa"
            elif description.endswith('-') and title.find("San Isidro") >= 0:
                return "10-11 y 16-18 de mayo: San Isidro en Llanera"

        return description