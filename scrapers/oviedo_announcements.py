"""
Scraper for Oviedo's social centers announcements and events.
"""

import logging
import re
from bs4 import BeautifulSoup
from bs4.element import Tag
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from scrapers.base import EventScraper

logger = logging.getLogger('explorastur')

class OviedoAnnouncementsScraper(EventScraper):
    """Scraper for Oviedo's social centers announcements and events."""

    def __init__(self, config=None):
        super().__init__(config)

        if not config:
            self.url = "https://www.oviedo.es/centrossociales/avisos"
            self.source_name = "Centros Sociales Oviedo"
            self.base_url = "https://www.oviedo.es"

    def scrape(self):
        """Scrape events from Oviedo's social centers announcements page."""
        events = []
        logger.info(f"Fetching URL: {self.url}")

        try:
            soup = self.fetch_and_parse(self.url)
            if not soup:
                return []

            # Find all the announcement sections
            announcement_sections = soup.select('.asset-full-content')
            if not announcement_sections:
                logger.warning("No announcement sections found on Oviedo announcements page")
                return []

            # Process each announcement section
            for section in announcement_sections:
                # Extract header title (section title)
                header = section.find_previous('h3', class_='header-title')
                if header:
                    header_span = header.select_one('span')
                    header_text = header_span.get_text().strip() if header_span else ""
                else:
                    header_text = ""

                # Find the article content
                article = section.select_one('.journal-content-article')
                if not article:
                    continue

                # Process the content
                if self._is_agenda(header_text):
                    # This is a weekly agenda, process all events in it
                    agenda_events = self._extract_agenda_events(article, header_text)
                    events.extend(agenda_events)
                else:
                    # This might be a single event/announcement
                    event = self._extract_single_announcement(article, header_text)
                    if event:
                        events.append(event)

            logger.info(f"Found {len(events)} events on Oviedo announcements page")
            return events

        except Exception as e:
            logger.error(f"Error scraping Oviedo announcements: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def _is_agenda(self, header_text):
        """Check if this is a weekly agenda section."""
        return 'agenda' in header_text.lower() and re.search(r'\d+\s+de\s+[a-zA-Z]+\s+a\s+\d+\s+de\s+[a-zA-Z]+', header_text.lower())

    def _extract_agenda_events(self, article, header_text):
        """Extract events from a weekly agenda."""
        events = []

        # Extract the date range from the header
        date_range = self._extract_date_range(header_text)

        # Find the text containing all the events
        text_div = article.select_one('.text')
        if not text_div:
            return []

        # Find all the event sections (usually marked with <strong> tags)
        event_sections = []
        current_section = {"title": "", "content": []}

        # Process all paragraphs and list items
        for element in text_div.select('p, ul, li'):
            # Check if this element contains a strong tag that might be an event title
            strong_tags = element.select('strong')

            if strong_tags and not element.name == 'li':
                # This might be a new event section title
                for strong in strong_tags:
                    title = strong.get_text().strip()

                    # Skip empty or formatting-only titles
                    if not title or len(title) < 3 or title.lower() in ['fecha:', 'lugar:', 'horario:', 'información:', 'inscripciones:']:
                        continue

                    # If we already had a section, save it
                    if current_section["title"]:
                        event_sections.append(current_section)

                    # Start a new section
                    current_section = {"title": title, "content": []}

                    # Add the rest of this paragraph to the content
                    paragraph_text = element.get_text().replace(title, "", 1).strip()
                    if paragraph_text:
                        current_section["content"].append(paragraph_text)

            elif current_section["title"]:
                # Add this element's text to the current section's content
                current_section["content"].append(element.get_text().strip())

        # Don't forget the last section
        if current_section["title"]:
            event_sections.append(current_section)

        # Process each event section
        for section in event_sections:
            # Skip non-event sections
            skip_titles = ['inscripciones', 'información', 'más información']
            if any(skip_word in section["title"].lower() for skip_word in skip_titles):
                continue

            # Get the full section content as text
            details = "\n".join(section["content"])

            # Extract the event from the section
            event = self._parse_event_section(section["title"], details, date_range)
            if event:
                events.append(event)

        return events

    def _extract_single_announcement(self, article, header_text):
        """Extract a single announcement or event."""
        # Check if this is a non-event announcement
        skip_headers = ['apertura de plazo', 'servicio de asesoramiento', 'concurso']
        if any(skip_word in header_text.lower() for skip_word in skip_headers):
            # Process this as a general announcement, not a specific event
            return self._create_announcement(header_text, article)

        # Find the text content
        text_div = article.select_one('.text')
        if not text_div:
            return None

        # Get the full text
        details = text_div.get_text().strip()

        # Parse the event
        return self._parse_event_section(header_text, details, "")

    def _create_announcement(self, title, article):
        """Create a general announcement entry."""
        # Find the text content
        text_div = article.select_one('.text')
        if not text_div:
            return None

        # Get the important details
        details = text_div.get_text().strip()

        # Look for dates in the text
        date = self._extract_date_from_text(details)
        if not date:
            # If no specific date, use the current month
            date = f"Todo el mes de {self.date_processor.get_current_month_name()}"

        # Location is usually "Centros Sociales Oviedo" for announcements
        location = "Centros Sociales Oviedo"

        # Try to find a more specific location
        location_match = re.search(r'(?:lugar|centro):?\s*([^.,\n]+)', details, re.IGNORECASE)
        if location_match:
            location = location_match.group(1).strip()

        # For some specific types of announcements, extract better location info
        if 'villa magdalena' in details.lower() or 'la corredoria' in details.lower():
            locations = []
            if 'villa magdalena' in details.lower():
                locations.append('Villa Magdalena')
            if 'la corredoria' in details.lower():
                locations.append('Centro Juvenil y Telecentro de La Corredoria')
            location = ", ".join(locations)

        # Create the event
        return self.create_event(
            title=title,
            date=date,
            location=location,
            url=self.url
        )

    def _parse_event_section(self, section_title, details, date_range):
        """Parse an event from a section title and details."""
        # Clean up the title
        title = section_title.strip()
        title = re.sub(r'^[:\-–—]+\s*', '', title)  # Remove leading colons or dashes
        title = self.text_processor.clean_title(title)

        # Skip if title is too short or empty
        if not title or len(title) < 3:
            return None

        # Skip non-events
        if self.text_processor.is_non_event(title):
            return None

        # Extract dates, times, and locations
        dates = []
        times = []
        locations = []

        # Process each line in the details
        for line in details.split('\n'):
            # Skip empty lines
            if not line.strip():
                continue

            # Check for dates
            date_matches = re.findall(r'(\d{1,2})\s+de\s+([a-zA-Z]+)', line, re.IGNORECASE)
            for day, month in date_matches:
                dates.append(f"{day} de {month.lower()}")

            # Check for days of week followed by dates
            day_date_matches = re.findall(r'(lunes|martes|miércoles|jueves|viernes|sábado|domingo)\s+(\d{1,2})\s+de\s+([a-zA-Z]+)', line, re.IGNORECASE)
            for day_of_week, day, month in day_date_matches:
                dates.append(f"{day} de {month.lower()}")

            # Check for times
            time_matches = re.findall(r'(\d{1,2})[\.:](\d{2})h?', line)
            for hour, minute in time_matches:
                times.append(f"{hour}:{minute}")

            # Check for locations
            # Common Centro Social abbreviations
            cs_match = re.search(r'CS\s+([A-Z][a-zA-Z]+)', line)
            if cs_match:
                locations.append(f"Centro Social {cs_match.group(1)}")

            # Full Centro Social names
            cs_full_match = re.search(r'Centro\s+Social\s+([A-Z][a-zA-Z\s]+)', line, re.IGNORECASE)
            if cs_full_match:
                locations.append(f"Centro Social {cs_full_match.group(1).strip()}")

            # Other specific locations
            location_keywords = ['Plaza', 'Teatro', 'Auditorio', 'Telecentro', 'Villa Magdalena']
            for keyword in location_keywords:
                if keyword.lower() in line.lower():
                    # Extract the location with the keyword and some words after it
                    location_match = re.search(f'{keyword}\\s+([^.,\\n]+)', line, re.IGNORECASE)
                    if location_match:
                        locations.append(f"{keyword} {location_match.group(1).strip()}")
                    else:
                        # Just add the keyword if we can't find more context
                        locations.append(keyword)

        # Format the date and time information
        event_date = ""
        if dates:
            # Use the first extracted date
            event_date = dates[0]
        elif date_range:
            # Fall back to the date range from the header
            event_date = date_range
        else:
            # If still no date, assume it's happening all month
            event_date = f"Todo el mes de {self.date_processor.get_current_month_name()}"

        # Add time if available
        if times:
            event_date = f"{event_date} a las {times[0]}"

        # Format the location
        event_location = ""
        if locations:
            # Use the first extracted location
            event_location = locations[0]
        else:
            # Try to extract from title as a last resort
            title_location = self.text_processor.extract_location_from_title(title)
            if title_location:
                event_location = title_location
            else:
                # Default location
                event_location = "Centros Sociales Oviedo"

        # Create the event
        return self.create_event(
            title=title,
            date=event_date,
            location=event_location,
            url=self.url
        )

    def _extract_date_range(self, header_text):
        """Extract a date range from header text."""
        if not header_text:
            return ""

        # Look for date range patterns like "12 de mayo a 18 de mayo"
        date_range_match = re.search(
            r'(\d{1,2})\s+de\s+([a-zA-Z]+)\s+a\s+(\d{1,2})\s+de\s+([a-zA-Z]+)',
            header_text
        )
        if date_range_match:
            start_day = date_range_match.group(1)
            start_month = date_range_match.group(2).lower()
            end_day = date_range_match.group(3)
            end_month = date_range_match.group(4).lower()

            if start_month == end_month:
                return f"{start_day} - {end_day} de {start_month}"
            else:
                return f"{start_day} de {start_month} - {end_day} de {end_month}"

        return ""

    def _extract_date_from_text(self, text):
        """Extract date information from text."""
        # Look for specific date patterns
        date_patterns = [
            # "12 de mayo" (exact date)
            (r'(\d{1,2})\s+de\s+([a-zA-Z]+)', lambda m: f"{m.group(1)} de {m.group(2).lower()}"),
            # "del 12 al 20 de mayo" (date range in same month)
            (r'del\s+(\d{1,2})\s+al\s+(\d{1,2})\s+de\s+([a-zA-Z]+)',
             lambda m: f"{m.group(1)} - {m.group(2)} de {m.group(3).lower()}"),
            # "del 28 de abril al 12 de mayo" (date range across months)
            (r'del\s+(\d{1,2})\s+de\s+([a-zA-Z]+)\s+al\s+(\d{1,2})\s+de\s+([a-zA-Z]+)',
             lambda m: f"{m.group(1)} de {m.group(2).lower()} - {m.group(3)} de {m.group(4).lower()}"),
            # "hasta el 20 de mayo" (deadline)
            (r'hasta\s+el\s+(\d{1,2})\s+de\s+([a-zA-Z]+)',
             lambda m: f"Hasta el {m.group(1)} de {m.group(2).lower()}"),
        ]

        for pattern, formatter in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return formatter(match)

        # If no explicit date pattern found, look for month names
        month_match = re.search(
            r'\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b',
            text,
            re.IGNORECASE
        )
        if month_match:
            month = month_match.group(1).lower()
            # Check for a specific day near the month
            day_match = re.search(r'(\d{1,2})\s+(?:de\s+)?' + month, text, re.IGNORECASE)
            if day_match:
                return f"{day_match.group(1)} de {month}"
            else:
                return f"Todo el mes de {month}"

        return ""