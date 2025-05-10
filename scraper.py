#!/usr/bin/env python3
"""
ExplorAstur - Simple Telecable event scraper for Asturias
---------------------------------------------------------
Simple script that scrapes events from Telecable blog
and outputs them to a markdown file.
"""

import os
import datetime
import logging
import requests
from bs4 import BeautifulSoup
import re
import sys

# Create directories
os.makedirs('logs', exist_ok=True)
os.makedirs('output', exist_ok=True)

# Configure logging
logger = logging.getLogger('explorastur')
logger.setLevel(logging.INFO)
if not logger.handlers:
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)

    # Add file handler
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    log_file = f'logs/explorastur_{today}.log'
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    logger.info(f"Logging to file: {log_file}")

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
    def extract_days_from_range(date_pattern):
        """
        Extract all day numbers from a date range pattern.
        Handles formats like:
        - "10 de mayo" (single day)
        - "10-15 de mayo" (range with hyphen)
        - "10 y 12 de mayo" (multiple days)
        - "10-11 y 15-17 de mayo" (multiple ranges)
        """
        day_numbers = []

        # Match single days: "10 de mayo"
        single_days = re.findall(r'(\d+)(?=\s+de\s+[a-zA-Z]+)', date_pattern)
        if single_days:
            day_numbers.extend([int(day) for day in single_days])

        # Match day ranges: "10-15 de mayo"
        day_ranges = re.findall(r'(\d+)-(\d+)(?=\s+de\s+[a-zA-Z]+)', date_pattern)
        for start, end in day_ranges:
            day_numbers.extend(range(int(start), int(end) + 1))

        # Match separated ranges: "10 y 15 de mayo"
        if ' y ' in date_pattern and not day_numbers:
            separated_days = re.findall(r'(\d+)(?=\s+y\s+|\s+de\s+)', date_pattern)
            if separated_days:
                day_numbers.extend([int(day) for day in separated_days])

        # Look for additional formats: "del 10 al 15"
        del_al_match = re.search(r'del\s+(\d+)\s+al\s+(\d+)', date_pattern)
        if del_al_match:
            start, end = int(del_al_match.group(1)), int(del_al_match.group(2))
            day_numbers.extend(range(start, end + 1))

        return sorted(list(set(day_numbers)))  # Remove duplicates and sort

    @staticmethod
    def is_future_event(date_pattern, current_date):
        """
        Determine if an event is in the future based on its date pattern.
        Returns True if it's a month-long event or any day in the range is >= current_date.
        """
        # Always keep month-long events
        if date_pattern.startswith(("Mayo", "Junio", "Julio")) or "todo el mes" in date_pattern.lower():
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
        Month-long events go first, then by earliest day in range.
        """
        # Month-long events first
        if date_str.startswith(("Mayo", "Junio", "Julio")) or "todo el mes" in date_str.lower():
            return 0

        # Get all days in the range
        days = DateProcessor.extract_days_from_range(date_str)

        # Return first/earliest day in the range, or high number if none found
        return min(days) if days else 100

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
        """Clean up event title, removing date patterns and redundant information."""
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

        # Clean up by removing trailing punctuation
        title = title.rstrip('- ,:')

        # Fix specific titles
        if title.startswith("1 a 4 de mayo L.E.V. Festival"):
            title = "L.E.V. Festival"

        return title

    @staticmethod
    def extract_location_from_title(title):
        """Extract location information from event title."""
        # Common venue words in Spanish
        venue_words = ["Teatro", "Auditorio", "Sala", "Centro", "Pabellón",
                      "Plaza", "Factoría", "Recinto", "Museo"]

        # Try to extract location that has venue words
        for word in venue_words:
            pattern = f"{word}\\s+[\\w\\s\\.]+"
            match = re.search(pattern, title, re.IGNORECASE)
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

class EventScraper:
    """Base class for event scrapers."""

    def __init__(self):
        self.date_processor = DateProcessor()
        self.text_processor = TextProcessor()

    def scrape(self):
        """To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement scrape method")

    def _create_event(self, title, date, location, description, url):
        """Create a standardized event dictionary."""
        # Ensure title isn't empty
        if not title or title == ":":
            title = ""  # Let the processor handle empty titles

        return {
            'title': title,
            'date': date,
            'location': location,
            'description': description,
            'url': url
        }

class TelecableScraper(EventScraper):
    """Scraper for Telecable blog."""

    def __init__(self):
        super().__init__()
        self.url = "https://blog.telecable.es/agenda-planes-asturias/"
        self.current_month_year = self.date_processor.get_current_month_year()

    def scrape(self):
        """Scrape events from Blog Telecable Asturias."""
        events = []
        logger.info(f"Fetching URL: {self.url}")

        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(self.url, headers=headers, timeout=30)
            response.raise_for_status()
            html = response.text
        except Exception as e:
            logger.error(f"Error fetching {self.url}: {e}")
            return []

        # Parse HTML
        try:
            soup = BeautifulSoup(html, 'html.parser')
            article_body = soup.select_one('div.article-body')
            if not article_body:
                logger.error("Could not find article body")
                return []
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            return []

        logger.info("Using Telecable parser")

        # Variables to track current section
        current_section = ""
        current_image = ""

        # Store event descriptions separately for better context
        event_descriptions = {}

        # First pass - collect all paragraphs with event information
        self._collect_event_descriptions(article_body, event_descriptions)

        # Process the article body to find events
        events = self._process_article_body(article_body, current_section, event_descriptions)

        logger.info(f"Successfully extracted {len(events)} events")
        return events

    def _collect_event_descriptions(self, article_body, event_descriptions):
        """Collect event descriptions from all paragraphs for better context."""
        for element in article_body.find_all(['p']):
            if element.get('class') and 'western' in element.get('class'):
                text = element.get_text(strip=True)
                if bold := element.find('b'):
                    event_title = bold.get_text(strip=True)
                    # Extract key identifiers that might be in the title (like date + title)
                    date_match = re.search(r'(\d+(?:\s+y\s+\d+)?\s+de\s+[a-zA-Z]+)', event_title)
                    if date_match:
                        key = f"{date_match.group(1)}_{event_title.replace(date_match.group(1), '').strip()}"
                        # Store the paragraph text
                        event_descriptions[key] = text

    def _process_article_body(self, article_body, current_section, event_descriptions):
        """Process the article body to extract events."""
        events = []
        current_image = ""

        for element in article_body.find_all(['h2', 'p', 'figure']):
            # Process h2 tags as section markers
            if element.name == 'h2':
                current_section = element.get_text(strip=True)
                current_image = ""
                continue

            # Process figures with images
            if element.name == 'figure' and not current_image:
                img = element.find('img')
                if img and img.get('src'):
                    current_image = img.get('src')
                continue

            # Process paragraphs for events
            if element.name == 'p' and element.get('class') and 'western' in element.get('class'):
                # Case 1: Bold titles (most concerts and events)
                bold = element.find('b')
                if bold:
                    event = self._extract_event_from_bold(element, bold, event_descriptions)
                    if event:
                        events.append(event)

                # Case 2: Festival listings (in fiestas sections)
                elif "fiestas" in current_section.lower():
                    event = self._extract_event_from_festival(element)
                    if event:
                        events.append(event)

        return events

    def _extract_event_from_bold(self, element, bold, event_descriptions):
        """Extract event information from paragraphs with bold titles."""
        # Extract event title and check if it looks like an event
        event_title = bold.get_text(strip=True)
        if not re.search(r'\d+\s+de\s+[a-zA-Z]+', event_title) and not 'mayo' in event_title.lower():
            return None

        # Extract data from the text
        full_text = element.get_text(strip=True)

        # Find the next paragraph to possibly extract more description
        next_p = element.find_next('p')
        if next_p and next_p.get('class') and 'western' in next_p.get('class') and not next_p.find('b'):
            # If the next paragraph doesn't have a bold element, consider it part of this event's description
            next_text = next_p.get_text(strip=True)
            if next_text and len(next_text) > 5:
                full_text += " " + next_text

        # Extract date
        date_match = re.search(r'(\d+(?:\s+y\s+\d+)?\s+de\s+[a-zA-Z]+)', event_title) or re.search(r'(\d+(?:\s+y\s+\d+)?\s+de\s+[a-zA-Z]+)', full_text)
        event_date = date_match.group(1) if date_match else ""

        # Check for month-long events
        if not event_date and ("Durante todo el mes" in event_title or "todo el mes" in full_text):
            event_date = self.current_month_year

        # Extract location
        event_location = self._extract_location(full_text, event_title)

        # Extract URL
        event_url = self._extract_url(element, next_p)

        # Clean up the title - fix empty titles
        clean_title = self.text_processor.clean_title(event_title, event_date)

        # Handle cleanup for empty titles
        if not clean_title or clean_title == ":" or clean_title.startswith(":"):
            # Try to use the first part of the description as title
            if ":" in event_title:
                parts = event_title.split(":", 1)
                if len(parts) > 1 and parts[1].strip():
                    clean_title = parts[1].strip()
                    # Remove quotes if present
                    clean_title = re.sub(r'^["\']\s*|\s*["\']$', '', clean_title)

        # Extract description
        description = self._extract_description(full_text, event_title, event_date, clean_title, event_descriptions)

        # Create event
        return self._create_event(
            clean_title,
            event_date,
            event_location.strip(),
            description,
            event_url
        )

    def _extract_event_from_festival(self, element):
        """Extract event information from festival listings."""
        text = element.get_text(strip=True)

        # Skip short paragraphs
        if len(text) < 5:
            return None

        # Find date pattern
        date_match = re.search(r'(\d+(?:\s+[a-zA-Z]+)?\s+de\s+[a-zA-Z]+)', text) or re.search(r'(\d+(?:\s+a|\s+al|\s+y)\s+\d+(?:\s+de)?\s+[a-zA-Z]+)', text)
        if not date_match:
            return None

        event_date = date_match.group(1)

        # Extract title and description
        if ":" in text:
            parts = text.split(":", 1)
            event_title = parts[1].strip()
            description = parts[0].strip()
            if date_match.group(0) in description:
                description = description.replace(date_match.group(0), "").strip()
            description = self.text_processor.clean_description(description)
        else:
            event_title = text
            description = ""

        # Clean up title - remove date patterns
        for pattern in [r'\d+\s+de\s+[a-zA-Z]+:', r'\d+\s+a\s+\d+\s+de\s+[a-zA-Z]+:', r'\d+-\d+\s+de\s+[a-zA-Z]+:']:
            event_title = re.sub(pattern, '', event_title).strip()

        # Extract URL
        event_url = ""
        link = element.find('a')
        if link and link.get('href') and link.get('href') != self.url:
            event_url = link.get('href')

        # Create event
        return self._create_event(
            event_title,
            event_date,
            'Asturias',
            description,
            event_url
        )

    def _extract_location(self, full_text, event_title):
        """Extract location information from the text."""
        location_patterns = [
            r'en\s+(?:el|la|los|las)\s+(.*?)(?:\.|el día|\s+los días)',
            r'en\s+(.*?)(?:\.|el día|\s+los días)',
            r'(?:Teatro|Auditorio|Centro|Sala|Pabellón|Plaza|Factoría)\s+[^\.]+',
        ]

        # Try standard patterns first
        for pattern in location_patterns:
            location_match = re.search(pattern, full_text)
            if location_match:
                return location_match.group(0).replace("en ", "")

        # If no location found, try extracting from title
        title_location = self.text_processor.extract_location_from_title(event_title)
        if title_location:
            return title_location

        return ""

    def _extract_url(self, element, next_p=None):
        """Extract URL from element and optionally from the next paragraph."""
        event_url = ""

        # First check current element
        links = element.find_all('a')
        if links:
            for link in links:
                if link.get('href') and link.get('href') != self.url:
                    event_url = link.get('href')
                    break

        # If no URL found, check next paragraph
        if not event_url and next_p:
            links = next_p.find_all('a')
            if links:
                for link in links:
                    if link.get('href') and link.get('href') != self.url:
                        event_url = link.get('href')
                        break

        return event_url if event_url.startswith(('http://', 'https://')) else ""

    def _extract_description(self, full_text, event_title, event_date, clean_title, event_descriptions):
        """Extract and clean the event description."""
        # Remove the event title from the full text
        description = full_text.replace(event_title, '').strip()

        # Look for event description in the collected descriptions
        if event_date:
            key = f"{event_date}_{clean_title}"
            if key in event_descriptions and event_descriptions[key] != full_text:
                # If there's more text in the stored description, use that
                if len(event_descriptions[key]) > len(full_text):
                    description = event_descriptions[key].replace(event_title, '').strip()

        # Clean and fix the description
        description = self.text_processor.clean_description(description)
        description = self.text_processor.fix_incomplete_description(clean_title, description)

        return description

class EventProcessor:
    """Class to process, filter, and format events."""

    def __init__(self):
        self.date_processor = DateProcessor()
        self.text_processor = TextProcessor()
        self.current_date = datetime.datetime.now().day

    def process_events(self, events):
        """Process, clean, and filter events."""
        filtered_events = []

        for event in events:
            # Clean title and extract data
            title = self.text_processor.clean_title(event.get('title', '').strip(), event.get('date', '').strip())
            date_pattern = event.get('date', '').strip()

            # Extract and clean location
            location = event.get('location', '').strip() or "N/A"
            title_location = self.text_processor.extract_location_from_title(title)
            if title_location and location == "N/A":
                location = title_location
                # Remove the location from the title
                title = title.replace(title_location, "").strip()
                title = re.sub(r'-\s*$', '', title).strip()
                title = title.rstrip('- ,:')

            # Get and fix description
            description = event.get('description', '').strip()
            description = self.text_processor.fix_incomplete_description(title, description)

            # Filter out non-events and empty titles
            if not title or self.text_processor.is_non_event(title):
                continue

            # Filter by date - keep only current and future events
            if not self.date_processor.is_future_event(date_pattern, self.current_date):
                continue

            # Add to filtered events
            filtered_events.append({
                'title': title,
                'date': date_pattern or self.date_processor.get_current_month_year(),
                'location': location,
                'description': description,
                'url': event.get('url', '')
            })

        return filtered_events

    def format_to_markdown(self, events):
        """Format events to markdown with date headers."""
        # Group events by date
        events_by_date = {}
        for event in events:
            date_info = event.get('date', '')
            if date_info not in events_by_date:
                events_by_date[date_info] = []
            events_by_date[date_info].append(event)

        # Sort date keys
        date_keys = list(events_by_date.keys())
        date_keys.sort(key=self.date_processor.date_sort_key)

        # Build markdown
        md = ["# Eventos en Asturias\n\n"]

        # Add events by date
        for date in date_keys:
            md.append(f"## {date}\n")

            for event in events_by_date[date]:
                title = event.get('title', '').strip()
                url = event.get('url', '')
                description = event.get('description', '')
                location = event.get('location', '')

                # Determine what details to show
                event_details = description
                if not event_details or len(event_details) < 5:
                    event_details = location if location and location != "N/A" else ""

                # Check for truncated descriptions
                if event_details and (event_details.endswith('a') or event_details.endswith('-')):
                    event_details = self.text_processor.fix_incomplete_description(title, event_details)

                # Create the markdown line - ensure title isn't blank
                if not title:
                    # If no title but we have details, use first few words of details as title
                    if event_details:
                        title_words = event_details.split()[:3]
                        title = " ".join(title_words) + "..."
                    else:
                        title = "Evento"

                # Create markdown line with title and URL
                if url:
                    md.append(f"* [{title}]({url})")
                else:
                    md.append(f"* {title}")

                # Add details if available
                if event_details:
                    md[-1] += f": {event_details}"

                md[-1] += "\n"

            # Add extra newline between date sections
            md.append("\n")

        return ''.join(md)

def main():
    """Main execution function."""
    logger.info("Starting ExplorAstur - Telecable events scraper")

    try:
        # Create scraper
        scraper = TelecableScraper()

        # Scrape events
        events = scraper.scrape()

        if not events:
            logger.warning("No events found")
            return

        logger.info(f"Found {len(events)} events")

        # Process events
        processor = EventProcessor()
        filtered_events = processor.process_events(events)

        # Format to markdown
        markdown = processor.format_to_markdown(filtered_events)

        # Write to file
        date_str = datetime.datetime.now().strftime('%Y-%m-%d')
        output_file = f'output/events_{date_str}.md'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown)

        logger.info(f"Exported {len(filtered_events)} events to {output_file}")
        logger.info("ExplorAstur completed successfully")

    except Exception as e:
        logger.error(f"Error running scraper: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()