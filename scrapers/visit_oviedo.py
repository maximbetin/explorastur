"""
Scraper for Visit Oviedo website.
"""

import logging
import re
import json
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Any

from scrapers.base import EventScraper
from scraper_utils import make_absolute_url

logger = logging.getLogger('explorastur')

class VisitOviedoScraper(EventScraper):
    """Scraper for Visit Oviedo website."""

    def __init__(self, config=None):
        super().__init__(config)
        # No need for custom URL or source_name as they're handled by the base class

    def scrape(self):
        """Scrape events from Visit Oviedo website with pagination support."""
        logger.info(f"Fetching URL: {self.url}")

        try:
            # Use the base class pagination method
            return self.process_pagination(
                base_url=self.base_url,
                start_url=self.url,
                extract_page_events=self._extract_week_events,
                next_page_selector='.paginator .pager li:last-child a:contains("Siguiente")'
            )
        except Exception as e:
            return self.handle_error(e, "scraping Visit Oviedo events", [])

    def _extract_week_events(self, soup):
        """Extract events from a week view page."""
        events = []

        # Find the week-view container
        week_view = soup.select_one('.week-view')
        if not week_view:
            logger.warning("No week view found on Visit Oviedo page")
            return []

        # Find all day entries
        day_entries = week_view.select('.day-entry')
        if not day_entries:
            logger.warning("No day entries found on Visit Oviedo page")
            return []

        # Process each day
        for day_entry in day_entries:
            day_events = self._process_day(day_entry)
            events.extend(day_events)

        return events

    def _process_day(self, day_entry):
        """Process a single day entry and extract all events."""
        events = []

        try:
            # Extract the day information
            day_element = day_entry.select_one('.day')
            if not day_element:
                return []

            day_num = day_element.select_one('.day-of-month')
            month_element = day_element.select_one('.month')

            day = day_num.get_text().strip() if day_num else ""
            month = month_element.get_text().strip() if month_element else ""

            # Create the day date string
            day_date = ""
            if day and month:
                day_date = f"{day.lstrip('0')} de {month.strip()}"

            # Find all event entries for this day
            event_entries = day_entry.select('.entry')
            if not event_entries:
                return []

            # Process each event
            for entry in event_entries:
                event = self._extract_event_from_entry(entry, day_date)
                if event:
                    events.append(event)

            return events

        except Exception as e:
            logger.error(f"Error processing day entry: {e}")
            return []

    def _extract_event_from_entry(self, entry, day_date):
        """Extract event details from an entry element."""
        try:
            # Extract link
            link = entry.select_one('a')
            if not link:
                return None

            # Extract URL
            event_url = link.get('href', '')
            # Ensure event_url is a string
            event_url = str(event_url)
            if not event_url.startswith('http'):
                event_url = make_absolute_url(self.base_url, event_url)

            # First try to get title from link title attribute as this may be cleaner
            link_title = link.get('title', '')
            if link_title:
                # Remove "Ver evento " prefix from title
                title = re.sub(r'^Ver evento\s+', '', link_title)
                # Fix broken title attribute in links like "Segunda semifinal Concurso... ciudad="" de="" oviedo"
                title = re.sub(r'\s+ciudad=""', ' Ciudad', title)
                title = re.sub(r'\s+de=""', ' de', title)
                title = re.sub(r'\s+oviedo""="">', ' Oviedo', title)
            else:
                title = ""

            # If no title from link attribute or it's malformed, try from the .title element
            if not title or '""=""' in title:
                title_element = entry.select_one('.title')
                if title_element:
                    # Extract title and decode HTML entities
                    title = title_element.get_text(strip=True)
                    # Fix common HTML entity issues
                    title = title.replace("&amp;", "&").replace("&quot;", "\"")

            # Sometimes there are special pattern issues like 'ciudad="" de="" oviedo""="">'
            malformed_patterns = ['"="">', 'ciudad=""', 'de=""', 'oviedo""', '=""']
            for pattern in malformed_patterns:
                if pattern in title:
                    if pattern == '"="">' or pattern == '="">':
                        title = title.split(pattern)[0]
                    elif pattern == 'ciudad=""':
                        title = title.replace('ciudad=""', 'Ciudad')
                    elif pattern == 'de=""':
                        title = title.replace('de=""', 'de')
                    elif pattern == 'oviedo""':
                        title = title.replace('oviedo""', 'Oviedo')

            if not title:
                return None

            # Extract time
            hour_element = entry.select_one('.hour')
            time = ""
            if hour_element:
                # Extract the time, removing the icon text
                time_text = hour_element.get_text().strip()
                time_match = re.search(r'\d{1,2}:\d{2}', time_text)
                if time_match:
                    time = time_match.group(0)

            # Extract location
            location_element = entry.select_one('.location')
            location = ""
            if location_element:
                # Extract the location, removing the icon text
                location_text = location_element.get_text().strip()
                location = re.sub(r'^marker', '', location_text).strip()

            # Combine date and time
            event_date = day_date
            if time:
                event_date = f"{day_date} a las {time}"

            # Clean up the title - remove any remaining quotes or whitespace
            title = self.text_processor.clean_title(title)

            # Create the event
            return self.create_event(
                title=title,
                date=event_date,
                location=location,
                url=event_url
            )

        except Exception as e:
            logger.error(f"Error extracting event from entry: {e}")
            return None

    def _clean_date_text(self, date_text):
        """Clean and format date text."""
        if not date_text:
            return ""

        # Remove any HTML tags that might be present
        date_text = re.sub(r'<[^>]+>', '', date_text)

        # Remove common prefixes
        prefixes = ['fecha:', 'fecha', 'desde el', 'desde', 'a partir del']
        for prefix in prefixes:
            if date_text.lower().startswith(prefix):
                date_text = date_text[len(prefix):].strip()

        # Handle different date formats

        # Format: "Del 23 al 27 de mayo"
        del_al_match = re.search(r'del\s+(\d{1,2})\s+al\s+(\d{1,2})\s+de\s+([a-zA-Z]+)', date_text, re.IGNORECASE)
        if del_al_match:
            start_day = del_al_match.group(1)
            end_day = del_al_match.group(2)
            month = del_al_match.group(3)
            return f"{start_day} - {end_day} de {month.lower()}"

        # Format: "23 - 27 mayo" or "23-27 mayo"
        range_match = re.search(r'(\d{1,2})\s*[-\/]\s*(\d{1,2})\s+(?:de\s+)?([a-zA-Z]+)', date_text, re.IGNORECASE)
        if range_match:
            start_day = range_match.group(1)
            end_day = range_match.group(2)
            month = range_match.group(3)
            return f"{start_day} - {end_day} de {month.lower()}"

        # Format: "23 de mayo"
        single_day_match = re.search(r'(\d{1,2})\s+(?:de\s+)?([a-zA-Z]+)', date_text, re.IGNORECASE)
        if single_day_match:
            day = single_day_match.group(1)
            month = single_day_match.group(2)
            return f"{day} de {month.lower()}"

        # Format: "Mayo 2023" (whole month)
        month_year_match = re.search(r'([a-zA-Z]+)\s+\d{4}', date_text, re.IGNORECASE)
        if month_year_match:
            month = month_year_match.group(1)
            return f"Todo el mes de {month.lower()}"

        # If no patterns match, just clean up the text
        clean_text = date_text.strip()
        if clean_text:
            return clean_text

        # If nothing works, return empty string
        return ""